import asyncio
import copy
import importlib.util
import os
import sys
import types
from contextlib import nullcontext
from types import SimpleNamespace

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

import httpx
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _install_upload_jobs_stub(monkeypatch):
    module = types.ModuleType("backend.ingest.upload_jobs")
    module._normalize_draft = lambda draft: copy.deepcopy(draft)
    module.normalize_doi = lambda value: str(value).strip() if value else None
    monkeypatch.setitem(sys.modules, "backend.ingest.upload_jobs", module)


def _app_with_user(rag):
    app = FastAPI()
    app.include_router(rag.router)
    app.dependency_overrides[rag.get_current_user] = lambda: SimpleNamespace(
        id=7, role="user", is_approved=True,
    )
    return app


async def _request(app, method, path, **kwargs):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, **kwargs)


def test_old_draft_get_converts_once_without_returning_legacy_fields(tmp_path, monkeypatch):
    from backend.api import rag
    from backend.database import Base
    from backend.ingest import upload_tasks
    from backend.models import MaterialFamily
    from backend.rag import database as rag_database

    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'legacy.sqlite'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        async with session_factory.begin() as session:
            session.add(MaterialFamily(
                code="hydrogen_based", name_zh="氢基超导体",
                name_en="Hydrogen-based superconductor",
                normalized_name="氢基超导体",
            ))
        monkeypatch.setattr(rag_database, "async_session_factory", session_factory)
        _install_upload_jobs_stub(monkeypatch)
        monkeypatch.setattr(rag, "_task_for_user", lambda *_args: {"user_id": 7})
        monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: {
            "paper": {"title": "Old draft", "paper_type": "experimental"},
            "material_states": [{"material": "LaH10"}],
            "sc_type": "hydride",
            "sc_type_review_status": "confirmed",
        })

        response = await _request(
            _app_with_user(rag), "GET", f"/api/rag/upload-tasks/{'7' * 32}/draft",
        )
        await engine.dispose()
        return response

    response = asyncio.run(scenario())

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["paper"]["material_families"] == [{
        "id": 1, "name": "氢基超导体", "status": "confirmed",
    }]
    assert "material_family" not in data["material_states"][0]
    assert "classification_migration_warnings" in data
    for field in ("sc_type", "sc_type_review_status", "type_code", "type_proposal_raw"):
        assert field not in data


def test_new_put_and_submit_reject_each_legacy_classification_field(monkeypatch):
    from backend.api import rag
    from backend.ingest import upload_tasks

    task_id = "8" * 32
    ready_state = {
        "task_id": task_id,
        "user_id": 7,
        "stage": "ready",
        "processing_status": "succeeded",
        "updated_at": 1,
        "state_schema_version": 1,
    }
    monkeypatch.setattr(rag, "_task_for_user", lambda *_args: ready_state)
    _install_upload_jobs_stub(monkeypatch)
    monkeypatch.setattr(rag, "_submitted_paper_for_task", lambda _task_id: _async_value(None))
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(upload_tasks, "update_state", lambda *_args, **_kwargs: ready_state)
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: submit_draft["value"])
    app = _app_with_user(rag)

    for field in ("sc_type", "sc_type_review_status", "type_code", "type_proposal_raw"):
        legacy_draft = {
            "paper": {"title": "Legacy", "paper_type": "review"},
            "material_states": [],
            field: "legacy-value",
        }
        put_response = asyncio.run(_request(
            app, "PUT", f"/api/rag/upload-tasks/{task_id}/draft", json=legacy_draft,
        ))
        assert put_response.status_code == 400
        assert put_response.json()["detail"] == {
            "code": "legacy_classification_contract",
            "message": "草稿仍包含旧材料分类字段，请重新打开草稿完成一次性转换",
            "fields": [field],
        }

        submit_draft["value"] = legacy_draft
        submit_response = asyncio.run(_request(
            app, "POST", f"/api/rag/upload-tasks/{task_id}/submit",
        ))
        assert submit_response.status_code == 400
        assert submit_response.json()["detail"]["code"] == "legacy_classification_contract"
        assert submit_response.json()["detail"]["fields"] == [field]


submit_draft = {"value": {}}


async def _async_value(value):
    return value
