import asyncio
import json
from contextlib import nullcontext

from backend.ingest import upload_tasks


def test_expired_redis_state_preserves_files_for_submitted_paper(monkeypatch):
    deleted = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: 42)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(upload_tasks, "cleanup_task_files", deleted.append)

    upload_tasks.cleanup_upload_task("a" * 32, expected_updated_at=1)

    assert deleted == []


def test_missing_paper_id_in_redis_still_preserves_persisted_paper(monkeypatch):
    deleted = []
    state = {"task_id": "b" * 32, "updated_at": 1, "paper_id": None}
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: 43)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(upload_tasks, "cleanup_task_files", deleted.append)

    upload_tasks.cleanup_upload_task("b" * 32, expected_updated_at=1)

    assert deleted == []


def test_expired_unsubmitted_task_is_deleted(monkeypatch):
    deleted = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(upload_tasks, "cleanup_task_files", deleted.append)

    upload_tasks.cleanup_upload_task("c" * 32, expected_updated_at=1)

    assert deleted == ["c" * 32]


def test_submitted_paper_is_found_from_durable_source_path(sqlite_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from backend import database
    from backend.models import Paper

    task_id = "1" * 32
    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session.begin() as session:
        paper = Paper(
            title="Persisted",
            review_status="pending",
            source_file_path=f"upload_PDFs/{task_id}/paper.pdf",
        )
        session.add(paper)
        session.flush()
        paper_id = paper.id
    monkeypatch.setattr(database, "SessionLocal", Session)

    assert upload_tasks.submitted_paper_id(task_id) == paper_id
    assert upload_tasks.submitted_paper_id("2" * 32) is None


def test_submitting_task_is_rescheduled_instead_of_deleted(monkeypatch):
    task_id = "3" * 32
    state = {"task_id": task_id, "updated_at": 9, "submission_status": "submitting"}
    deleted = []
    rescheduled = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(upload_tasks, "cleanup_task_files", deleted.append)
    monkeypatch.setattr(
        upload_tasks,
        "_enqueue_cleanup",
        lambda task, updated, delay=upload_tasks.TASK_TTL: rescheduled.append((task, updated, delay)),
    )

    upload_tasks.cleanup_upload_task(task_id, expected_updated_at=9)

    assert deleted == []
    assert rescheduled == [(task_id, 9, upload_tasks.TASK_TTL)]


def test_review_artifact_recovers_task_from_database_path(tmp_path, sqlite_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from backend import database
    from backend.api import rag
    from backend.models import Paper

    task_id = "4" * 32
    artifact = tmp_path / "review_artifacts" / task_id / "result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(json.dumps({"task_id": task_id, "paper_id": None}), encoding="utf-8")
    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session.begin() as session:
        paper = Paper(
            title="Recoverable",
            review_status="pending",
            source_file_path=f"upload_PDFs/{task_id}/paper.pdf",
        )
        session.add(paper)
        session.flush()
        paper_id = paper.id
    monkeypatch.setattr(database, "SessionLocal", Session)
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)

    found = rag._artifact_by_paper_id(paper_id)

    assert found is not None
    assert found[0] == task_id
    assert found[2]["paper_id"] == paper_id


def test_submit_retry_recovers_committed_paper_without_creating_duplicate(monkeypatch):
    from types import SimpleNamespace

    from backend.api import rag

    task_id = "5" * 32
    state = {
        "task_id": task_id,
        "user_id": 7,
        "stage": "ready",
        "processing_status": "succeeded",
        "source_file_path": f"upload_PDFs/{task_id}/paper.pdf",
    }
    draft = {"paper": {"title": "Recovered"}, "key_properties": []}
    recorded = []
    monkeypatch.setattr(rag, "_task_for_user", lambda *_args: state)
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: draft)
    monkeypatch.setattr(rag, "_paper_id_for_source_path", lambda _path: _async_value(77))
    monkeypatch.setattr(rag, "_record_submitted_upload", lambda *args: recorded.append(args))

    async def must_not_create(*_args):
        raise AssertionError("已提交论文不得重复创建")

    monkeypatch.setattr(rag, "_create_pending_paper", must_not_create)

    result = asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=7)))

    assert result["paper_id"] == 77
    assert recorded[0][:2] == (task_id, 77)


def test_submit_endpoint_uses_same_lifecycle_lock_as_cleanup(monkeypatch):
    from contextlib import contextmanager
    from types import SimpleNamespace

    from backend.api import rag

    task_id = "7" * 32
    events = []

    @contextmanager
    def lock(locked_task_id):
        events.append(("enter", locked_task_id))
        yield
        events.append(("exit", locked_task_id))

    async def submit_locked(locked_task_id, _user):
        events.append(("submit", locked_task_id))
        return {"paper_id": 88}

    monkeypatch.setattr(upload_tasks, "upload_task_lock", lock)
    monkeypatch.setattr(rag, "_submit_upload_draft_locked", submit_locked)

    result = asyncio.run(rag.submit_upload_draft(task_id, SimpleNamespace(id=7)))

    assert result["paper_id"] == 88
    assert events == [("enter", task_id), ("submit", task_id), ("exit", task_id)]


async def _async_value(value):
    return value


def test_full_paper_summary_receives_every_chunk(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    task_id = "d" * 32
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    markdown = tmp_path / "paper.md"
    markdown.write_text("full paper", encoding="utf-8")
    artifact = tmp_path / "result.json"
    state = {
        "task_id": task_id,
        "file_path": str(source),
        "stage": "saving_file",
        "updated_at": 1,
    }
    chunks = [
        Chunk(0, index, f"Section {index}", None, f"content {index}", 2)
        for index in range(3)
    ]
    progress = []
    summary_inputs = []

    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_jobs, "markdown_path", lambda _task_id: markdown)
    monkeypatch.setattr(upload_jobs, "artifact_path", lambda _task_id: artifact)
    monkeypatch.setattr(upload_jobs, "_chunks_with_preamble", lambda _markdown: chunks)
    monkeypatch.setattr(upload_jobs, "_read_chunk", lambda _task_id, chunk: {"chunk": chunk.chunk_index})
    monkeypatch.setattr(upload_jobs, "_find_existing_by_hash", lambda _state: None)
    monkeypatch.setattr(upload_jobs, "_find_existing_paper", lambda _doi: None)
    monkeypatch.setattr(upload_jobs, "save_draft", lambda _task_id, _draft: None)

    def update_state(_task_id, **changes):
        state.update(changes)
        if "completed_chunks" in changes:
            progress.append((changes["completed_chunks"], changes["total_chunks"]))
        return dict(state)

    def complete_json(_system_prompt, prompt):
        summary_inputs.append(json.loads(prompt))
        return {
            "paper": {"title": "Full paper", "paper_type": "experimental"},
            "key_properties": [],
        }

    monkeypatch.setattr(upload_jobs, "update_state", update_state)
    monkeypatch.setattr(upload_jobs, "complete_json", complete_json)

    result = upload_jobs.process_upload_task(task_id)

    assert summary_inputs == [[{"chunk": 0}, {"chunk": 1}, {"chunk": 2}]]
    assert (1, 3) in progress and (2, 3) in progress and (3, 3) in progress
    assert result["processing_status"] == "succeeded"


def test_cached_chunk_is_reused_while_missing_chunk_calls_llm(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    monkeypatch.setattr(upload_jobs, "artifact_directory", lambda _task_id: tmp_path)
    chunk = Chunk(0, 0, "Results", None, "content", 2)
    cache = tmp_path / "chunks/00000.json"
    cache.parent.mkdir()
    cache.write_text(json.dumps({"cached": True}), encoding="utf-8")
    calls = []
    monkeypatch.setattr(upload_jobs, "complete_json", lambda *_args: calls.append(True) or {"fresh": True})

    assert upload_jobs._read_chunk("e" * 32, chunk) == {"cached": True}
    assert calls == []

    cache.unlink()
    assert upload_jobs._read_chunk("e" * 32, chunk)["fresh"] is True
    assert calls == [True]


def test_chunk_failure_records_reading_stage_and_reason(tmp_path, monkeypatch):
    import pytest

    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    task_id = "6" * 32
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    markdown = tmp_path / "paper.md"
    markdown.write_text("full paper", encoding="utf-8")
    state = {"task_id": task_id, "file_path": str(source), "stage": "saving_file"}
    chunks = [
        Chunk(0, index, "Results", None, f"content {index}", 2)
        for index in range(2)
    ]

    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_jobs, "markdown_path", lambda _task_id: markdown)
    monkeypatch.setattr(upload_jobs, "_chunks_with_preamble", lambda _markdown: chunks)
    monkeypatch.setattr(upload_jobs, "_find_existing_by_hash", lambda _state: None)

    def update_state(_task_id, **changes):
        state.update(changes)
        return dict(state)

    def read_chunk(_task_id, chunk):
        if chunk.chunk_index == 1:
            raise RuntimeError("第二段 LLM 失败")
        return {"chunk": chunk.chunk_index}

    monkeypatch.setattr(upload_jobs, "update_state", update_state)
    monkeypatch.setattr(upload_jobs, "_read_chunk", read_chunk)

    with pytest.raises(RuntimeError, match="第二段 LLM 失败"):
        upload_jobs.process_upload_task(task_id)

    assert state["processing_status"] == "failed"
    assert state["failed_stage"] == "reading"
    assert state["processing_error"] == "第二段 LLM 失败"
