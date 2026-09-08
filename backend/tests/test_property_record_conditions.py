"""实验条件从真实提取调用到记录持久化、导出的往返验证。"""

import asyncio
from copy import deepcopy
import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend import models
from backend.api.material_state_export import build_material_state_export
from backend.database import Base
from backend.ingest import upload_jobs
from backend.ingest.form_definitions import definition_checksum
from backend.ingest.property_modules import PropertyValidationError, persist_property_modules, validate_record


DESCRIPTIONS = [
    "Annealed Hg was measured using a four-probe setup.\nNo external field was applied.",
    "A separate Hg sample was measured with an applied field; pressure uncertainty was not reported.",
]


def raw_draft():
    return {
        "paper": {"title": "Hg measurements", "year": 2026, "paper_type": "experimental"},
        "material_states": [{
            "material": "Hg", "state_kind": "experimental", "scope": "current_paper",
            "tc_results": [
                {"result_kind": "experimental", "tc_method": "experimental", "tc_value_k": value,
                 "value_raw": f"{value} K", "experimental_conditions": {"description": description},
                 "evidence": {"page": 1, "quote": f"Tc was {value} K."}}
                for value, description in zip([4.2, 3.8], DESCRIPTIONS)
            ],
        }],
    }


def test_worker_prompts_and_storage_keep_each_measurement_conditions(tmp_path, monkeypatch):
    source = tmp_path / "paper.md"
    source.write_text("# Results\n\nHg was measured by four-probe resistivity. Tc was 4.2 K and 3.8 K.")
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    state = {"task_id": "e" * 32, "file_path": str(source), "file_kind": "md", "status": "queued"}
    saved = {}
    prompts = []
    monkeypatch.setattr(upload_jobs, "get_state", lambda _: state)
    monkeypatch.setattr(upload_jobs, "markdown_path", lambda _: source)
    monkeypatch.setattr(upload_jobs, "artifact_directory", lambda _: artifact_dir)
    monkeypatch.setattr(upload_jobs, "artifact_path", lambda _: artifact_dir / "result.json")
    monkeypatch.setattr(upload_jobs, "data_path", lambda name: tmp_path / name)
    monkeypatch.setattr(upload_jobs, "_find_existing_by_hash", lambda _: None)
    monkeypatch.setattr(upload_jobs, "_find_existing_paper", lambda _: None)
    monkeypatch.setattr(upload_jobs, "_schedule_terminal_cleanup", lambda _: None)
    monkeypatch.setattr(upload_jobs, "save_draft", lambda _, draft: saved.update(deepcopy(draft)))

    def update_state(_, **changes):
        state.update(changes)
        return dict(state)

    def complete_json(system, prompt, **kwargs):
        prompts.append(system)
        for direction in ("样品", "制备方式", "测量方法", "测量装置", "外场", "压力不确定度"):
            assert direction in system
        assert "experimental_conditions.description" in system
        assert "不是六个必填项" in system
        assert "不要猜测或编造" in system
        if system == upload_jobs.CHUNK_SYSTEM_PROMPT:
            return {"material_states": deepcopy(raw_draft()["material_states"])}
        candidates = json.loads(prompt)
        assert candidates[0]["material_states"][0]["tc_results"][1]["experimental_conditions"]["description"] == DESCRIPTIONS[1]
        return raw_draft()

    monkeypatch.setattr(upload_jobs, "update_state", update_state)
    monkeypatch.setattr(upload_jobs, "complete_json", complete_json)
    result = upload_jobs._process_upload_task(state["task_id"])
    assert result["status"] == "ready"
    assert prompts == [upload_jobs.CHUNK_SYSTEM_PROMPT, upload_jobs.SUMMARY_SYSTEM_PROMPT]
    modules = saved["material_states"][0]["property_modules"]
    assert [record["payload"]["experimental_conditions"]["description"] for record in modules[0]["records"]] == DESCRIPTIONS
    assert "tc_results" not in saved["material_states"][0]

    async def roundtrip():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with sessions() as session:
                seeds = json.loads((Path(__file__).parents[1] / "data/form_definitions.v1.json").read_text())
                session.add_all([models.FormDefinition(**seed, checksum=definition_checksum(seed)) for seed in seeds])
                session.add_all([
                    models.Paper(id=1, title="Hg", year=2026, review_status="pending", content_revision=1),
                    models.ChemicalSystem(id=1, paper_id=1, paper_revision=1, system_key="Hg", elements_list=["Hg"], element_count=1),
                    models.Superconductor(id=1, paper_id=1, paper_revision=1, chemical_system_id=1, chemical_formula="Hg", formula_normalized="Hg", composition_key="Hg:1", display_name="Hg", elements_list=["Hg"], composition={"Hg": 1}, element_ratio={"Hg": 1}),
                    models.MaterialState(id=1, state_key="state-hg", paper_id=1, paper_revision=1, superconductor_id=1, state_kind="experimental", crystal_system="unknown", material_dimensionality="unknown"),
                ])
                await session.flush()
                await persist_property_modules(session, paper_id=1, paper_revision=1, material_state_id=1, modules=modules)
                await session.commit()
            async with sessions() as session:
                records = (await session.execute(select(models.PropertyRecord).order_by(models.PropertyRecord.id))).scalars().all()
                assert [record.payload_json["experimental_conditions"]["description"] for record in records] == DESCRIPTIONS
                output = await session.run_sync(lambda db: build_material_state_export(db, paper_id=1, state_key="state-hg", user=models.User(role="admin")))
                exported = output["property_modules"][0]["records"]
                assert [record["payload"]["experimental_conditions"]["description"] for record in exported] == DESCRIPTIONS
                assert all(record["definition_version"] == 1 for record in exported)
        finally:
            await engine.dispose()

    asyncio.run(roundtrip())


@pytest.mark.parametrize("description", [7, None, [], {}])
def test_nontext_description_is_rejected_at_its_field(description):
    record = upload_jobs._normalize_draft(raw_draft())["material_states"][0]["property_modules"][0]["records"][0]
    record["payload"]["experimental_conditions"]["description"] = description
    with pytest.raises(PropertyValidationError) as error:
        validate_record(record)
    assert any(issue.field.endswith("payload.experimental_conditions.description") for issue in error.value.issues)


def test_empty_description_and_legacy_object_remain_valid():
    record = upload_jobs._normalize_draft(raw_draft())["material_states"][0]["property_modules"][0]["records"][0]
    for conditions in ({"description": ""}, {}, {"sample": "Hg", "external_field_t": 0}):
        record["payload"]["experimental_conditions"] = conditions
        assert validate_record(record)["payload"]["experimental_conditions"] == conditions
