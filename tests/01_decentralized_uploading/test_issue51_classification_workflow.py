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

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _install_upload_jobs_stub(monkeypatch):
    module = types.ModuleType("backend.ingest.upload_jobs")
    module._normalize_draft = lambda draft: copy.deepcopy(draft)
    module.normalize_doi = lambda value: str(value).strip() if value else None
    monkeypatch.setitem(sys.modules, "backend.ingest.upload_jobs", module)


def _write(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_submission_keeps_classification_in_review_artifact_until_approval(tmp_path, monkeypatch):
    from backend.api import rag
    from backend.database import Base
    from backend.ingest import upload_tasks
    from backend.models import (
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
        monkeypatch.setattr(upload_tasks, "update_state", lambda *_args, **_kwargs: None)
        _install_upload_jobs_stub(monkeypatch)

        async with session_factory.begin() as session:
            hydride = MaterialFamily(
                code="hydrogen_based",
                name_zh="氢基超导体",
                name_en="Hydrogen-based superconductor",
                normalized_name="氢基超导体",
            )
            clathrate = StructureFamily(
                code="clathrate",
                name_zh="笼状结构",
                name_en="Clathrate",
                normalized_name="笼状结构",
            )
            session.add_all([hydride, clathrate])
            await session.flush()
            catalog_ids = hydride.id, clathrate.id

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
                        "id": catalog_ids[0],
                        "name": "氢基超导体",
                        "status": "confirmed",
                    },
                    "structure_families": [
                        {
                            "id": catalog_ids[1],
                            "name": "笼状结构",
                            "status": "confirmed",
                            "is_primary": True,
                        }
                    ],
                    "material_dimensionality": "three_dimensional",
                    "state_kind": "experimental",
                },
                {
                    "material": "CeCu2Si2",
                    "material_family": {
                        "id": None,
                        "name": "重费米子超导体",
                        "status": "pending",
                    },
                    "structure_families": [
                        {"id": None, "name": "四方结构", "status": "pending", "is_primary": False}
                    ],
                    "material_dimensionality": "three_dimensional",
                    "state_kind": "experimental",
                },
            ],
            "classification_evidence": [],
        }

        paper_id = await rag._create_pending_paper(task_id, state, draft)
        rag._record_submitted_upload(task_id, paper_id, draft)

        async with session_factory() as session:
            states = list(
                (
                    await session.scalars(
                        select(MaterialState)
                        .where(MaterialState.paper_id == paper_id)
                        .order_by(MaterialState.id)
                    )
                ).all()
            )
            link_count = await session.scalar(
                select(func.count()).select_from(MaterialStateStructureFamily)
            )
        await engine.dispose()
        return states, link_count, task_id

    states, link_count, task_id = asyncio.run(scenario())

    assert [item.material_family_id for item in states] == [None, None]
    assert [item.element_count for item in states] == [2, 3]
    assert [item.material_dimensionality for item in states] == [
        "three_dimensional",
        "three_dimensional",
    ]
    assert link_count == 0

    snapshot_path = tmp_path / "review_artifacts" / task_id / "result.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    assert snapshot["user_values"]["material_states"][0]["material_family"]["name"] == "氢基超导体"
    assert snapshot["user_values"]["material_states"][1]["material_family"]["name"] == "重费米子超导体"


def test_models_exclude_the_superseded_classification_governance_schema():
    from backend.database import Base
    from backend import models  # noqa: F401

    assert "classification_proposals" not in Base.metadata.tables
    assert "classification_evidences" not in Base.metadata.tables
    assert "classification_audit_events" not in Base.metadata.tables
    assert "classification_snapshot" in Base.metadata.tables["paper_review_events"].c


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
