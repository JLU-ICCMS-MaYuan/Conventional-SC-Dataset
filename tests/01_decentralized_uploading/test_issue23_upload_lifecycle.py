import asyncio
import json
from contextlib import nullcontext

from backend.ingest import upload_tasks


def test_expired_redis_state_preserves_files_for_submitted_paper(monkeypatch):
    events = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: 42)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda task_id, **kwargs: events.append((task_id, kwargs["preserve_review_snapshot"])),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda _task_id: (_ for _ in ()).throw(AssertionError("正式文件不得删除")),
    )

    upload_tasks.cleanup_upload_task("a" * 32, expected_updated_at=1)

    assert events == [("a" * 32, True)]


def test_missing_paper_id_in_redis_still_preserves_persisted_paper(monkeypatch):
    events = []
    state = {"task_id": "b" * 32, "updated_at": 1, "paper_id": None}
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: 43)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda task_id, **kwargs: events.append((task_id, kwargs["preserve_review_snapshot"])),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda _task_id: (_ for _ in ()).throw(AssertionError("正式文件不得删除")),
    )

    upload_tasks.cleanup_upload_task("b" * 32, expected_updated_at=1)

    assert events == [("b" * 32, True)]


def test_expired_unsubmitted_task_is_deleted(monkeypatch):
    deleted = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "submitted_paper_id", lambda _task_id: None)
    monkeypatch.setattr(upload_tasks, "upload_task_lock", lambda _task_id: nullcontext())
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_transient_data",
        lambda task_id, **_kwargs: deleted.append(("transient", task_id)),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_unsubmitted_files",
        lambda task_id: deleted.append(("files", task_id)),
    )
    monkeypatch.setattr(
        upload_tasks,
        "cleanup_duplicate_candidate",
        lambda task_id, paper_id: deleted.append(("candidate", task_id, paper_id)),
    )

    upload_tasks.cleanup_upload_task("c" * 32, expected_updated_at=1)

    assert deleted == [
        ("transient", "c" * 32),
        ("files", "c" * 32),
        ("candidate", "c" * 32, None),
    ]


def test_submitted_paper_is_found_from_durable_upload_task_id(sqlite_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from backend import database
    from backend.models import Paper

    task_id = "1" * 32
    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session.begin() as session:
        paper = Paper(
            title="Persisted",
            review_status="pending",
            upload_task_id=task_id,
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
        lambda context, delay=upload_tasks.TASK_TTL: rescheduled.append((context, delay)),
    )

    upload_tasks.cleanup_upload_task(task_id, expected_updated_at=9)

    assert deleted == []
    assert rescheduled[0][0].task_id == task_id
    assert rescheduled[0][0].expected_updated_at == 9
    assert rescheduled[0][1] == upload_tasks.TASK_TTL


def test_review_artifact_is_located_from_durable_upload_task_id(tmp_path, sqlite_engine, monkeypatch):
    from sqlalchemy.orm import sessionmaker

    from backend import database
    from backend.api import rag
    from backend.models import Paper

    task_id = "4" * 32
    Session = sessionmaker(bind=sqlite_engine, future=True)
    with Session.begin() as session:
        paper = Paper(
            title="Recoverable",
            review_status="pending",
            upload_task_id=task_id,
        )
        session.add(paper)
        session.flush()
        paper_id = paper.id
    artifact = tmp_path / "review_artifacts" / task_id / "result.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text(
        json.dumps({"task_id": task_id, "paper_id": paper_id, "paper_revision": 1}),
        encoding="utf-8",
    )
    monkeypatch.setattr(database, "SessionLocal", Session)
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)

    context = rag._paper_review_context(paper_id)
    found = rag._artifact_by_paper_id(paper_id, context["task_id"])

    assert found is not None
    assert found[0] == task_id
    assert found[2]["paper_id"] == paper_id


def test_submit_retry_recovers_committed_paper_without_creating_duplicate(monkeypatch):
    from types import SimpleNamespace

    from backend.api import rag

    task_id = "5" * 32
    monkeypatch.setattr(rag, "_submitted_paper_for_task", lambda _task_id: _async_value({
        "paper_id": 77,
        "uploaded_by_user_id": 7,
        "review_status": "pending",
        "paper_revision": 1,
    }))
    monkeypatch.setattr(rag, "_recover_submitted_upload", lambda *_args: None)

    async def must_not_create(*_args):
        raise AssertionError("已提交论文不得重复创建")

    monkeypatch.setattr(rag, "_create_pending_paper", must_not_create)

    result = asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=7)))

    assert result["paper_id"] == 77


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


def test_full_paper_summary_only_receives_current_paper_classification_candidates(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    task_id = "5" * 32
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"pdf")
    markdown = tmp_path / "paper.md"
    markdown.write_text("full paper", encoding="utf-8")
    artifact = tmp_path / "result.json"
    state = {
        "task_id": task_id, "file_path": str(source),
        "stage": "saving_file", "updated_at": 1,
    }
    chunks = [
        Chunk(0, 0, "Introduction", None, "introduction", 3),
        Chunk(0, 1, "Methods", None, "methods", 2),
    ]
    chunk_results = {
        0: {
            "paper_type_evidence": [
                {"candidate": "unknown", "scope": "current_paper", "quote": "Title"},
                {
                    "candidate": "experimental", "scope": "referenced_work",
                    "quote": "Subsequent experimental work found two states.",
                },
                {"candidate": "review", "quote": "Legacy unscoped review evidence."},
            ],
            "sc_type_candidates": [{
                "value": "Bardeen-Cooper-Schrieffer superconductor",
                "scope": "referenced_work", "quote": "the materials were BCS superconductors",
            }],
        },
        1: {
            "paper_type_evidence": [{
                "candidate": "theoretical", "scope": "current_paper",
                "quote": "The phase diagram is constructed through structure searching simulations.",
            }],
            "sc_type_candidates": [{
                "value": "高压三元氢化物超导体", "scope": "current_paper",
                "quote": "ternary Li2MgH16",
            }],
        },
    }
    summary_inputs = []

    monkeypatch.setattr(upload_jobs, "get_state", lambda _task_id: state)
    monkeypatch.setattr(upload_jobs, "markdown_path", lambda _task_id: markdown)
    monkeypatch.setattr(upload_jobs, "artifact_path", lambda _task_id: artifact)
    monkeypatch.setattr(upload_jobs, "_chunks_with_preamble", lambda _markdown: chunks)
    monkeypatch.setattr(
        upload_jobs, "_read_chunk",
        lambda _task_id, chunk: chunk_results[chunk.chunk_index],
    )
    monkeypatch.setattr(upload_jobs, "_find_existing_by_hash", lambda _state: None)
    monkeypatch.setattr(upload_jobs, "_find_existing_paper", lambda _doi: None)
    monkeypatch.setattr(upload_jobs, "save_draft", lambda _task_id, _draft: None)

    def update_state(_task_id, **changes):
        state.update(changes)
        return dict(state)

    def complete_json(_system_prompt, prompt):
        summary_inputs.append(json.loads(prompt))
        return {
            "paper": {
                "title": "Li2MgH16", "paper_type": "theoretical",
                "theoretical_subtype": "calculation",
            },
            "sc_type": "高压三元氢化物超导体",
            "key_properties": [],
        }

    monkeypatch.setattr(upload_jobs, "update_state", update_state)
    monkeypatch.setattr(upload_jobs, "complete_json", complete_json)

    upload_jobs.process_upload_task(task_id)

    assert len(summary_inputs[0]) == 2
    assert summary_inputs[0][0]["paper_type_evidence"] == []
    assert summary_inputs[0][0]["sc_type_candidates"] == []
    assert summary_inputs[0][1]["paper_type_evidence"] == [chunk_results[1]["paper_type_evidence"][0]]
    assert summary_inputs[0][1]["sc_type_candidates"] == [chunk_results[1]["sc_type_candidates"][0]]


def test_cached_chunk_is_reused_while_missing_chunk_calls_llm(tmp_path, monkeypatch):
    from backend.ingest import upload_jobs
    from backend.ingest.chunker import Chunk

    monkeypatch.setattr(upload_jobs, "artifact_directory", lambda _task_id: tmp_path)
    chunk = Chunk(0, 0, "Results", None, "content", 2)
    cache = tmp_path / "chunks/00000.json"
    cache.parent.mkdir()
    cached_result = {
        "_schema_version": upload_jobs.CHUNK_RESULT_SCHEMA_VERSION,
        "cached": True,
    }
    cache.write_text(json.dumps(cached_result), encoding="utf-8")
    calls = []
    monkeypatch.setattr(upload_jobs, "complete_json", lambda *_args: calls.append(True) or {"fresh": True})

    assert upload_jobs._read_chunk("e" * 32, chunk) == cached_result
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
