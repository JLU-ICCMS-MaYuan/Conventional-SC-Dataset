from inspect import signature
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import sessionmaker

from backend.api import upload_tasks as upload_api
from backend.ingest import upload_contracts, upload_tasks


class MigrationRedis:
    def __init__(self, values):
        self.values = dict(values)
        self.expiries = {}

    def scan_iter(self, match):
        assert match == "upload:*:state"
        return list(self.values)

    def get(self, key):
        return self.values.get(key)

    def pipeline(self, transaction=True):
        assert transaction is True
        return MigrationPipeline(self)


class MigrationPipeline:
    def __init__(self, client):
        self.client = client
        self.watched = None
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def watch(self, key):
        self.watched = key

    def get(self, key):
        return self.client.get(key)

    def unwatch(self):
        self.watched = None

    def multi(self):
        return None

    def setex(self, key, ttl, value):
        self.commands.append((key, ttl, value))

    def execute(self):
        for key, ttl, value in self.commands:
            self.client.values[key] = value
            self.client.expiries[key] = ttl
        return [True] * len(self.commands)


def _duplicate_state() -> dict:
    return {
        "task_id": "a" * 32,
        "user_id": 7,
        "status": "duplicate",
        "stage": "ready",
        "processing_status": "succeeded",
        "duplicate": True,
        "existing_paper_id": 42,
        "existing_paper_status": "approved",
        "allowed_actions": ["view"],
        "duplicate_reason": "数据库中已有该论文",
        "cleanup_at": 200,
        "updated_at": 100,
        "state_schema_version": upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    }


def test_new_upload_task_exposes_current_state_schema(monkeypatch):
    class Client:
        def pipeline(self, transaction=True):
            return Pipeline()

    class Pipeline:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def watch(self, _key):
            return None

        def zrange(self, _key, _start, _end):
            return []

        def multi(self):
            return None

        def set(self, _key, _value):
            return None

        def zadd(self, _key, _value):
            return None

        def execute(self):
            return None

    monkeypatch.setattr(upload_tasks, "redis_client", Client)

    state = upload_tasks.create_task(
        7,
        files=[{"client_id": "main", "role": "main", "filename": "paper.pdf", "size": 3}],
    )

    assert state["state_schema_version"] == upload_contracts.UPLOAD_STATE_SCHEMA_VERSION
    assert upload_contracts.public_task_state(state)["state_schema_version"] == (
        upload_contracts.UPLOAD_STATE_SCHEMA_VERSION
    )


def test_upload_task_reads_duplicate_contract_without_database_session(monkeypatch):
    state = _duplicate_state()
    current_user = SimpleNamespace(id=7, role="user", is_approved=True)
    monkeypatch.setattr(upload_tasks, "list_user_tasks", lambda _user_id: [state])
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: state)

    assert "db" not in signature(upload_api.get_upload_tasks).parameters
    assert "db" not in signature(upload_api.get_upload_task).parameters
    listed = upload_api.get_upload_tasks(current_user=current_user)
    detailed = upload_api.get_upload_task(
        task_id=state["task_id"], touch=False, current_user=current_user,
    )

    assert listed["data"] == [upload_contracts.public_task_state(state)]
    assert detailed["data"] == upload_contracts.public_task_state(state)


def test_upload_task_rejects_unsupported_redis_contract(monkeypatch):
    state = {**_duplicate_state(), "state_schema_version": 0}
    current_user = SimpleNamespace(id=7, role="user", is_approved=True)
    monkeypatch.setattr(upload_tasks, "list_user_tasks", lambda _user_id: [state])

    with pytest.raises(HTTPException) as unsupported:
        upload_api.get_upload_tasks(current_user=current_user)

    assert unsupported.value.status_code == 409
    assert unsupported.value.detail["code"] == "UPLOAD_STATE_VERSION_UNSUPPORTED"


def test_worker_writes_complete_versioned_duplicate_contract(monkeypatch, tmp_path):
    from backend.ingest import upload_jobs

    source = tmp_path / "new.pdf"
    existing_source = tmp_path / "existing.pdf"
    source.write_bytes(b"same paper")
    existing_source.write_bytes(b"same paper")
    existing = SimpleNamespace(
        id=42,
        doi="10.1000/example",
        review_status="approved",
        uploaded_by_user_id=99,
        main_stored_path=str(existing_source),
        main_sha256=upload_jobs.sha256_file(existing_source),
    )
    captured = {}
    monkeypatch.setattr(upload_jobs, "_original_path", lambda _state: source)
    monkeypatch.setattr(upload_jobs, "artifact_directory", lambda _task_id: tmp_path / "artifacts")
    monkeypatch.setattr(upload_jobs, "markdown_path", lambda _task_id: tmp_path / "paper.md")
    monkeypatch.setattr(
        upload_jobs,
        "update_state",
        lambda _task_id, **changes: captured.update(changes) or dict(changes),
    )
    monkeypatch.setattr(upload_jobs, "_schedule_terminal_cleanup", lambda _task_id: None)

    result = upload_jobs._handle_duplicate(
        "b" * 32,
        {"user_id": 7, "filename": "new.pdf", "created_at": 1},
        existing,
    )

    assert result["status"] == "duplicate"
    assert result["existing_paper_status"] == "approved"
    assert result["allowed_actions"] == ["view"]
    assert result["duplicate_reason"] == "数据库中已有该论文"
    assert result["state_schema_version"] == upload_contracts.UPLOAD_STATE_SCHEMA_VERSION


def test_duplicate_lookup_uses_current_paper_file_schema(sqlite_engine, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.models import Paper, PaperFile

    session_factory = sessionmaker(bind=sqlite_engine, future=True)
    with session_factory() as session:
        paper = Paper(
            doi="10.1000/current-schema",
            title="Current schema paper",
            review_status="approved",
            content_revision=1,
            approved_revision=1,
            uploaded_by_user_id=99,
        )
        session.add(paper)
        session.flush()
        session.add(PaperFile(
            paper_id=paper.id,
            paper_revision=1,
            role="main",
            original_filename="paper.pdf",
            stored_path="upload_PDFs/formal/paper.pdf",
            sha256="a" * 64,
            size=3,
            sort_order=0,
        ))
        session.commit()
        paper_id = paper.id

    monkeypatch.setattr(upload_jobs, "SessionLocal", session_factory)

    by_hash = upload_jobs._find_existing_by_hash({"file_sha256": "a" * 64})
    by_doi = upload_jobs._find_existing_paper("https://doi.org/10.1000/current-schema")

    assert by_hash.id == paper_id
    assert by_hash.main_sha256 == "a" * 64
    assert by_doi.id == paper_id
    assert by_doi.main_stored_path == "upload_PDFs/formal/paper.pdf"


def test_legacy_duplicate_migration_is_dry_run_then_idempotent_apply():
    from backend.scripts.migrate_upload_task_states import migrate_upload_task_states

    task_id = "c" * 32
    key = upload_tasks.task_key(task_id)
    legacy = {
        "task_id": task_id,
        "user_id": 7,
        "status": "queued",
        "stage": "ready",
        "duplicate": True,
        "existing_paper_id": 42,
        "updated_at": 100,
    }
    client = MigrationRedis({key: json.dumps(legacy)})
    lookups = []

    def lookup(paper_id):
        lookups.append(paper_id)
        return SimpleNamespace(
            id=42,
            review_status="approved",
            uploaded_by_user_id=99,
        )

    dry_run = migrate_upload_task_states(client, lookup, apply=False, now=150)
    assert dry_run == {"legacy": 1, "migrated": 0, "unresolved": 0, "changed": 0}
    assert json.loads(client.values[key]) == legacy
    assert lookups == []

    applied = migrate_upload_task_states(client, lookup, apply=True, now=150)
    migrated = json.loads(client.values[key])
    assert applied == {"legacy": 1, "migrated": 1, "unresolved": 0, "changed": 1}
    assert migrated["status"] == "duplicate"
    assert migrated["existing_paper_status"] == "approved"
    assert migrated["allowed_actions"] == ["view"]
    assert migrated["terminal_at"] == 100
    assert migrated["cleanup_at"] == 100 + upload_contracts.TASK_TTL
    assert migrated["state_schema_version"] == upload_contracts.UPLOAD_STATE_SCHEMA_VERSION
    assert client.expiries[key] == upload_contracts.TASK_TTL - 50

    repeated = migrate_upload_task_states(client, lookup, apply=True, now=160)
    assert repeated == {"legacy": 0, "migrated": 0, "unresolved": 0, "changed": 0}
    assert lookups == [42]
