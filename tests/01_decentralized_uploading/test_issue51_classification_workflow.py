import asyncio
import copy
import importlib.util
import json
import os
import sys
import types

os.environ.setdefault("JWT_SECRET_KEY", "issue51-test-secret")


def _install_upload_dependency_stubs():
    if "redis" not in sys.modules and importlib.util.find_spec("redis") is None:
        redis_module = types.ModuleType("redis")
        redis_module.Redis = type("Redis", (), {})
        sys.modules["redis"] = redis_module
    if "rq" not in sys.modules and importlib.util.find_spec("rq") is None:
        rq_module = types.ModuleType("rq")
        rq_module.Queue = type("Queue", (), {})
        rq_exceptions = types.ModuleType("rq.exceptions")
        rq_exceptions.NoSuchJobError = type("NoSuchJobError", (Exception,), {})
        rq_job = types.ModuleType("rq.job")
        rq_job.Job = type("Job", (), {})
        sys.modules.update({"rq": rq_module, "rq.exceptions": rq_exceptions, "rq.job": rq_job})


_install_upload_dependency_stubs()

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _install_upload_jobs_stub(monkeypatch):
    module = types.ModuleType("backend.ingest.upload_jobs")
    module._normalize_draft = lambda draft: copy.deepcopy(draft)
    module.normalize_doi = lambda value: str(value).strip() if value else None
    monkeypatch.setitem(sys.modules, "backend.ingest.upload_jobs", module)


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_submission_persists_material_state_classifications_transactionally(tmp_path, monkeypatch):
    from backend.api import rag
    from backend.database import Base
    from backend.ingest import upload_tasks
    from backend.models import (
        ClassificationEvidence,
        ClassificationProposal,
        MaterialFamily,
        MaterialState,
        MaterialStateStructureFamily,
        StructureFamily,
    )
    from backend.rag import database as rag_database

    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'issue51.sqlite'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(rag_database, "async_session_factory", session_factory)
        monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
        _install_upload_jobs_stub(monkeypatch)

        async with session_factory.begin() as session:
            hydride = MaterialFamily(
                code="hydrogen_based", name_zh="氢基超导体",
                name_en="Hydrogen-based superconductor",
                normalized_name="氢基超导体", is_active=True,
            )
            clathrate = StructureFamily(
                code="clathrate", name_zh="笼状结构", name_en="Clathrate",
                normalized_name="笼状结构", is_active=True,
            )
            layered = StructureFamily(
                code="layered", name_zh="层状结构", name_en="Layered",
                normalized_name="层状结构", is_active=True,
            )
            session.add_all([hydride, clathrate, layered])
            await session.flush()
            ids = hydride.id, clathrate.id, layered.id

        task_id = "5" * 32
        state = {"task_id": task_id, "user_id": 7, "files": []}
        draft = {
            "paper": {
                "title": "Material-state classification",
                "paper_type": "experimental",
                "authors": ["A. Author"],
                "research_materials": ["LaH10", "CeCu2Si2"],
            },
            "material_states": [
                {
                    "material": "LaH10",
                    "material_family": {
                        "id": ids[0], "name": "氢基超导体", "status": "confirmed",
                        "evidence": {"section": "Results", "page": 3, "quote": "hydride"},
                    },
                    "structure_families": [
                        {"id": ids[1], "name": "笼状结构", "status": "confirmed", "is_primary": True},
                        {"id": ids[2], "name": "层状结构", "status": "confirmed", "is_primary": False},
                    ],
                    "element_count": 99,
                    "material_dimensionality": "three_dimensional",
                    "state_kind": "experimental",
                },
                {
                    "material": "CeCu2Si2",
                    "material_family": {
                        "id": None, "name": "重费米子超导体", "status": "pending",
                    },
                    "structure_families": [
                        {"id": None, "name": "四方结构", "status": "pending", "is_primary": False},
                    ],
                    "material_dimensionality": "three_dimensional",
                    "state_kind": "experimental",
                },
            ],
            "classification_evidence": [],
        }

        paper_id = await rag._create_pending_paper(task_id, state, draft)

        async with session_factory() as session:
            states = list((await session.scalars(
                select(MaterialState).where(MaterialState.paper_id == paper_id).order_by(MaterialState.id)
            )).all())
            links = list((await session.scalars(
                select(MaterialStateStructureFamily).where(
                    MaterialStateStructureFamily.material_state_id == states[0].id
                ).order_by(MaterialStateStructureFamily.structure_family_id)
            )).all())
            proposals = list((await session.scalars(
                select(ClassificationProposal).order_by(ClassificationProposal.dimension)
            )).all())
            evidences = list((await session.scalars(
                select(ClassificationEvidence).order_by(
                    ClassificationEvidence.material_state_id,
                    ClassificationEvidence.dimension,
                )
            )).all())
        await engine.dispose()
        return states, links, proposals, evidences, ids

    states, links, proposals, evidences, ids = asyncio.run(scenario())

    assert states[0].material_family_id == ids[0]
    assert states[0].element_count == 2
    assert states[0].material_dimensionality == "three_dimensional"
    assert [(link.structure_family_id, link.is_primary) for link in links] == [
        (ids[1], True), (ids[2], False),
    ]
    assert states[1].material_family_id is None
    assert states[1].element_count == 3
    assert [(item.dimension, item.raw_name, item.status) for item in proposals] == [
        ("material_family", "重费米子超导体", "proposed"),
        ("structure_family", "四方结构", "proposed"),
    ]
    assert {item.dimension for item in evidences} == {
        "material_family", "structure_family", "element_count", "material_dimensionality",
    }
    assert all(item.scope == "current_paper" for item in evidences)
    assert all(item.source_kind in {"reported", "derived"} for item in evidences)


def test_admin_snapshot_preserves_reference_scope_without_formal_material_state(tmp_path, monkeypatch):
    from backend.api import rag
    from backend.ingest import upload_tasks

    task_id = "6" * 32
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    monkeypatch.setattr(upload_tasks, "update_state", lambda *_args, **_kwargs: None)
    artifact = {
        "evidence": {
            "classification_scope": [
                {"material": "LaH10", "scope": "current_paper", "quote": "we report LaH10"},
                {"material": "H3S", "scope": "referenced_work", "quote": "previous H3S work"},
            ],
        },
    }
    result_path = tmp_path / "review_artifacts" / task_id / "result.json"
    _write(result_path, json.dumps(artifact, ensure_ascii=False))

    rag._record_submitted_upload(
        task_id,
        42,
        {
            "paper": {"title": "LaH10"},
            "material_states": [{"material": "LaH10"}],
        },
    )

    snapshot = json.loads(result_path.read_text(encoding="utf-8"))
    assert snapshot["user_values"]["material_states"] == [{"material": "LaH10"}]
    assert snapshot["evidence"]["classification_scope"] == artifact["evidence"]["classification_scope"]
    assert "referenced_materials" not in snapshot["user_values"]["paper"]
