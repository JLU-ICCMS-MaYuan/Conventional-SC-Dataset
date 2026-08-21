import json
import asyncio
from contextlib import nullcontext
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import OperationalError

from backend.ingest import upload_contracts, upload_tasks


class CleanupRedis:
    def __init__(self):
        self.deleted: list[str] = []
        self.removed: list[tuple[str, str]] = []

    def delete(self, *keys):
        self.deleted.extend(keys)
        return len(keys)

    def zrem(self, key, member):
        self.removed.append((key, member))
        return 1


def _write(path, content="data"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_transient_cleanup_preserves_review_snapshot_and_formal_files(tmp_path, monkeypatch):
    task_id = "a" * 32
    client = CleanupRedis()
    deleted_jobs: list[str] = []
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: client)
    monkeypatch.setattr(upload_tasks, "_delete_processing_job", deleted_jobs.append)

    upload_file = tmp_path / "upload_PDFs" / task_id / "paper.pdf"
    combined_markdown = tmp_path / "parsed_markdown" / f"{task_id}.md"
    split_markdown = tmp_path / "parsed_markdown" / task_id / "main.md"
    result = tmp_path / "review_artifacts" / task_id / "result.json"
    chunk = tmp_path / "review_artifacts" / task_id / "chunks" / "main" / "00000.json"
    intermediate = tmp_path / "review_artifacts" / task_id / "identities.json"
    for path in (upload_file, combined_markdown, split_markdown, chunk, intermediate):
        _write(path)
    _write(result, json.dumps({"task_id": task_id, "paper_id": 42}))

    context = upload_contracts.CleanupContext(
        task_id=task_id,
        user_id=7,
        processing_job_id="rq-job",
        existing_paper_id=None,
        expected_updated_at=100,
        state_schema_version=upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    )
    upload_tasks.cleanup_transient_data(
        task_id,
        context=context,
        preserve_review_snapshot=True,
    )

    assert result.is_file()
    assert not chunk.exists()
    assert not intermediate.exists()
    assert upload_file.is_file()
    assert combined_markdown.is_file()
    assert split_markdown.is_file()
    assert deleted_jobs == ["rq-job"]
    assert set(client.deleted) == {
        upload_tasks.task_key(task_id),
        upload_tasks.draft_key(task_id),
    }
    assert client.removed == [(upload_tasks.user_tasks_key(7), task_id)]


def test_unsubmitted_file_cleanup_deletes_both_markdown_layouts(tmp_path, monkeypatch):
    task_id = "b" * 32
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    upload_file = tmp_path / "upload_PDFs" / task_id / "paper.pdf"
    combined_markdown = tmp_path / "parsed_markdown" / f"{task_id}.md"
    split_markdown = tmp_path / "parsed_markdown" / task_id / "main.md"
    for path in (upload_file, combined_markdown, split_markdown):
        _write(path)

    upload_tasks.cleanup_unsubmitted_files(task_id)

    assert not upload_file.exists()
    assert not combined_markdown.exists()
    assert not split_markdown.exists()


def test_duplicate_candidate_cleanup_is_scoped_to_one_task(tmp_path, monkeypatch):
    task_id = "c" * 32
    other_task_id = "d" * 32
    paper_id = 42
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    root = tmp_path / "upload_PDFs" / "candidates" / str(paper_id)
    candidate = root / f"{task_id}.pdf"
    metadata = root / f"{task_id}.json"
    other_candidate = root / f"{other_task_id}.pdf"
    for path in (candidate, metadata, other_candidate):
        _write(path)

    upload_tasks.cleanup_duplicate_candidate(task_id, paper_id)

    assert not candidate.exists()
    assert not metadata.exists()
    assert other_candidate.is_file()


def test_processing_job_cleanup_uses_rq_delete(monkeypatch):
    deleted = []

    class Job:
        def delete(self):
            deleted.append(True)

    monkeypatch.setattr(
        upload_tasks.Job,
        "fetch",
        lambda job_id, connection: Job() if job_id == "rq-job" else None,
    )
    monkeypatch.setattr(upload_tasks.Redis, "from_url", lambda _url: object())

    upload_tasks._delete_processing_job("rq-job")

    assert deleted == [True]


def test_scheduled_cleanup_keeps_context_after_redis_state_expires(monkeypatch):
    task_id = "e" * 32
    state = {
        "task_id": task_id,
        "user_id": 7,
        "status": "duplicate",
        "job_id": "rq-job",
        "existing_paper_id": 42,
        "updated_at": 100,
        "cleanup_at": 200,
        "state_schema_version": upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    }
    scheduled = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_tasks.time, "time", lambda: 150)
    monkeypatch.setattr(
        upload_tasks,
        "_enqueue_cleanup",
        lambda context, delay=upload_tasks.TASK_TTL: scheduled.append((context, delay)),
    )

    upload_tasks.schedule_cleanup(task_id)

    context, delay = scheduled[0]
    assert context == upload_contracts.CleanupContext.from_state(task_id, state)
    assert delay == 50

    events = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda cleaned_task_id, **kwargs: events.append(("transient", cleaned_task_id, kwargs)),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda cleaned_task_id: events.append(("files", cleaned_task_id)),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_duplicate_candidate",
        lambda cleaned_task_id, paper_id: events.append(("candidate", cleaned_task_id, paper_id)),
    )

    upload_tasks.cleanup_upload_task(context)

    assert events == [
        ("transient", task_id, {"context": context, "preserve_review_snapshot": False}),
        ("files", task_id),
        ("candidate", task_id, 42),
    ]


def test_cleanup_fails_closed_when_mysql_is_unavailable(monkeypatch):
    task_id = "f" * 32
    context = upload_contracts.CleanupContext(
        task_id=task_id,
        user_id=7,
        processing_job_id="rq-job",
        existing_paper_id=None,
        expected_updated_at=100,
        state_schema_version=upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    )
    rescheduled = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(
        upload_tasks,
        "submitted_paper_id",
        lambda _task_id: (_ for _ in ()).throw(OperationalError("SELECT", {}, Exception("down"))),
    )
    monkeypatch.setattr(
        upload_tasks,
        "_enqueue_cleanup",
        lambda scheduled_context, delay=upload_tasks.TASK_TTL: rescheduled.append(
            (scheduled_context, delay)
        ),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("不得清理临时数据")),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda *_args: (_ for _ in ()).throw(AssertionError("不得删除文件")),
    )

    upload_tasks.cleanup_upload_task(context)

    assert rescheduled == [(context, 60)]


def test_submit_retry_recovers_from_mysql_without_redis(monkeypatch):
    from backend.api import rag

    task_id = "1" * 32
    monkeypatch.setattr(
        rag,
        "_submitted_paper_for_task",
        lambda _task_id: _async_value({
            "paper_id": 77,
            "uploaded_by_user_id": 7,
            "review_status": "pending",
            "paper_revision": 1,
        }),
    )
    monkeypatch.setattr(
        rag,
        "_task_for_user",
        lambda *_args: (_ for _ in ()).throw(AssertionError("不得依赖 Redis")),
    )
    monkeypatch.setattr(rag, "_recover_submitted_upload", lambda *_args: None)

    result = asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=7)))

    assert result == {"ok": True, "paper_id": 77, "review_status": "pending"}

    with pytest.raises(HTTPException) as forbidden:
        asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=8)))
    assert forbidden.value.status_code == 403


def test_successful_submit_cleans_transient_only_after_snapshot(monkeypatch):
    from backend.api import rag

    task_id = "2" * 32
    state = {
        "task_id": task_id,
        "user_id": 7,
        "status": "ready",
        "stage": "ready",
        "processing_status": "succeeded",
        "updated_at": 100,
        "job_id": "rq-job",
        "state_schema_version": upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    }
    draft = {"paper": {"title": "Paper"}, "key_properties": []}
    events = []
    monkeypatch.setattr(rag, "_submitted_paper_for_task", lambda _task_id: _async_value(None))
    monkeypatch.setattr(rag, "_task_for_user", lambda *_args: state)
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: draft)
    monkeypatch.setattr(upload_tasks, "update_state", lambda _task_id, **_changes: state)
    monkeypatch.setattr(rag, "_create_pending_paper", lambda *_args: _async_value(88))
    monkeypatch.setattr(
        rag,
        "_record_submitted_upload",
        lambda *_args, **_kwargs: events.append("snapshot"),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda cleaned_task_id, **kwargs: events.append((cleaned_task_id, kwargs)),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda *_args: (_ for _ in ()).throw(AssertionError("正式文件不得删除")),
    )

    result = asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=7)))

    expected_context = upload_contracts.CleanupContext.from_state(task_id, state)
    assert result["paper_id"] == 88
    assert events == [
        "snapshot",
        (task_id, {"context": expected_context, "preserve_review_snapshot": True}),
    ]


def test_snapshot_failure_keeps_transient_recovery_data(monkeypatch):
    from backend.api import rag

    task_id = "3" * 32
    state = {
        "task_id": task_id,
        "user_id": 7,
        "status": "ready",
        "stage": "ready",
        "processing_status": "succeeded",
        "updated_at": 100,
        "state_schema_version": upload_contracts.UPLOAD_STATE_SCHEMA_VERSION,
    }
    monkeypatch.setattr(rag, "_submitted_paper_for_task", lambda _task_id: _async_value(None))
    monkeypatch.setattr(rag, "_task_for_user", lambda *_args: state)
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: {"paper": {"title": "Paper"}})
    monkeypatch.setattr(upload_tasks, "update_state", lambda _task_id, **_changes: state)
    monkeypatch.setattr(rag, "_create_pending_paper", lambda *_args: _async_value(89))
    monkeypatch.setattr(
        rag,
        "_record_submitted_upload",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("快照失败后不得清理")),
    )

    result = asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=7)))

    assert result["paper_id"] == 89


def test_submitted_review_snapshot_keeps_only_review_fields(tmp_path, monkeypatch):
    from backend.api import rag

    task_id = "7" * 32
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    result_path = tmp_path / "review_artifacts" / task_id / "result.json"
    _write(result_path, json.dumps({
        "task_id": task_id,
        "paper_id": None,
        "ai_values": {"paper": {"title": "AI title"}},
        "evidence": {"classification": [{"quote": "source"}]},
        "raw_response": "must disappear",
        "prompt": "must disappear",
    }))
    monkeypatch.setattr(upload_tasks, "update_state", lambda *_args, **_kwargs: None)

    rag._record_submitted_upload(
        task_id,
        92,
        {
            "paper": {"title": "User title"},
            "key_properties": [],
            "ai_original": {"paper": {"title": "fallback"}},
        },
        paper_revision=4,
    )

    snapshot = json.loads(result_path.read_text(encoding="utf-8"))
    assert set(snapshot) == {
        "task_id", "paper_id", "paper_revision", "ai_values", "user_values", "evidence",
    }
    assert snapshot["paper_revision"] == 4
    assert snapshot["ai_values"]["paper"]["title"] == "AI title"
    assert snapshot["user_values"]["paper"]["title"] == "User title"


def test_pending_paper_transaction_matches_current_revision_schema(tmp_path, monkeypatch):
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from backend.database import Base
    from backend.api import rag
    from backend.models import Paper, PaperChunk, PaperEvidence, PaperFile
    from backend.rag import database as rag_database

    async def scenario():
        engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'submit.sqlite'}")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        monkeypatch.setattr(rag_database, "async_session_factory", session_factory)
        monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
        task_id = "6" * 32
        _write(
            tmp_path / "parsed_markdown" / task_id / "main.md",
            "<!-- page: 1 -->\n# Abstract\nThis review summarizes superconductors.",
        )
        state = {
            "task_id": task_id,
            "user_id": 7,
            "files": [{
                "file_id": "main",
                "role": "main",
                "original_filename": "paper.pdf",
                "source_file_path": f"upload_PDFs/{task_id}/paper.pdf",
                "sha256": "a" * 64,
                "size": 3,
                "sort_order": 0,
            }],
        }
        draft = {
            "paper": {
                "title": "Review paper",
                "paper_type": "review",
                "authors": ["A. Author"],
            },
            "key_properties": [],
            "classification_evidence": [{
                "file_id": "main",
                "chunk_index": 0,
                "section": "Abstract",
                "page": 1,
                "quote": "This review summarizes superconductors.",
            }],
        }

        paper_id = await rag._create_pending_paper(task_id, state, draft)

        async with session_factory() as session:
            paper = await session.get(Paper, paper_id)
            paper_file = await session.scalar(
                select(PaperFile).where(PaperFile.paper_id == paper_id)
            )
            paper_chunk = await session.scalar(
                select(PaperChunk).where(PaperChunk.paper_id == paper_id)
            )
            paper_evidence = await session.scalar(
                select(PaperEvidence).where(PaperEvidence.paper_id == paper_id)
            )
        await engine.dispose()
        return paper, paper_file, paper_chunk, paper_evidence

    paper, paper_file, paper_chunk, paper_evidence = asyncio.run(scenario())

    assert paper.upload_task_id == "6" * 32
    assert paper.content_revision == 1
    assert paper_file.paper_revision == 1
    assert paper_file.stored_path.endswith("/paper.pdf")
    assert paper_chunk.paper_revision == 1
    assert paper_chunk.paper_file_id == paper_file.id
    assert paper_evidence.paper_revision == 1
    assert paper_evidence.paper_chunk_id == paper_chunk.id


def test_pending_review_snapshot_requires_current_paper_revision(tmp_path, monkeypatch):
    from backend.api import rag

    task_id = "4" * 32
    result_path = tmp_path / "review_artifacts" / task_id / "result.json"
    _write(result_path, json.dumps({
        "task_id": task_id,
        "paper_id": 90,
        "paper_revision": 3,
        "ai_values": {"paper": {"title": "AI title"}},
        "user_values": {"paper": {"title": "User title"}},
        "evidence": {"classification": []},
    }))
    context = {
        "task_id": task_id,
        "paper_id": 90,
        "paper_revision": 3,
        "review_status": "pending",
    }
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    monkeypatch.setattr(rag, "_paper_review_context", lambda _paper_id: dict(context))

    response = asyncio.run(rag.get_paper_review_artifact(90, _current_user=SimpleNamespace()))

    assert response["data"]["paper_revision"] == 3
    assert response["data"]["ai_values"]["paper"]["title"] == "AI title"

    context["paper_revision"] = 4
    with pytest.raises(HTTPException) as mismatch:
        asyncio.run(rag.get_paper_review_artifact(90, _current_user=SimpleNamespace()))
    assert mismatch.value.status_code == 409
    assert mismatch.value.detail["code"] == "review_artifact_revision_mismatch"


def test_review_snapshot_delete_is_terminal_only_and_idempotent(tmp_path, monkeypatch):
    from backend.api import rag

    task_id = "5" * 32
    result_path = tmp_path / "review_artifacts" / task_id / "result.json"
    _write(result_path, json.dumps({
        "task_id": task_id,
        "paper_id": 91,
        "paper_revision": 2,
        "ai_values": {},
        "user_values": {},
        "evidence": {},
    }))
    context = {
        "task_id": task_id,
        "paper_id": 91,
        "paper_revision": 2,
        "review_status": "pending",
    }
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    monkeypatch.setattr(rag, "_paper_review_context", lambda _paper_id: dict(context))

    with pytest.raises(HTTPException) as pending:
        asyncio.run(rag.delete_paper_review_artifact(91, _current_user=SimpleNamespace()))
    assert pending.value.status_code == 409
    assert pending.value.detail["code"] == "review_artifact_still_pending"
    assert result_path.is_file()

    context["review_status"] = "approved"
    first = asyncio.run(rag.delete_paper_review_artifact(91, _current_user=SimpleNamespace()))
    second = asyncio.run(rag.delete_paper_review_artifact(91, _current_user=SimpleNamespace()))

    assert first == {"ok": True, "paper_id": 91, "cleaned": True}
    assert second == {"ok": True, "paper_id": 91, "cleaned": False}
    assert not result_path.exists()


async def _async_value(value):
    return value
