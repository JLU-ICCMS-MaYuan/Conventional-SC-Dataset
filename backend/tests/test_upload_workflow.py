import asyncio
import json
import os
from types import SimpleNamespace


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-upload-workflow-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from fastapi import HTTPException

from backend.api import rag
from backend.ingest import upload_tasks
from backend.models import Paper
from backend.rag.config import RagSettings
from backend.rag.search import sql_search, vector_search


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def setex(self, key, ttl, value):
        self.commands.append((key, ttl, value))

    def execute(self):
        for key, ttl, value in self.commands:
            self.client.values[key] = value
            self.client.ttls[key] = ttl


class FakeRedis:
    def __init__(self, values):
        self.values = values
        self.ttls = {}
        self.transaction = None

    def get(self, key):
        return self.values.get(key)

    def pipeline(self, transaction):
        self.transaction = transaction
        return FakePipeline(self)


class FakeResult:
    def __init__(self, values):
        self.values = values

    def unique(self):
        return self

    def scalar_one_or_none(self):
        return self.values[0] if self.values else None

    def scalars(self):
        return self

    def all(self):
        return self.values

    def __iter__(self):
        return iter(self.values)


class FakeAsyncSession:
    def __init__(self, scalar_value=None, execute_values=None):
        self.scalar_value = scalar_value
        self.execute_values = execute_values or []
        self.statement = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def scalar(self, statement):
        self.statement = statement
        return self.scalar_value

    async def execute(self, statement):
        self.statement = statement
        return FakeResult(self.execute_values)


def test_save_draft_refreshes_state_and_draft_atomically(monkeypatch):
    task_id = "a" * 32
    client = FakeRedis({
        upload_tasks.task_key(task_id): json.dumps({"task_id": task_id, "updated_at": 1}),
    })
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: client)

    upload_tasks.save_draft(task_id, {"paper": {"title": "draft"}})

    assert client.transaction is True
    assert json.loads(client.values[upload_tasks.task_key(task_id)])["updated_at"] > 1
    assert json.loads(client.values[upload_tasks.draft_key(task_id)])["paper"]["title"] == "draft"
    assert client.ttls[upload_tasks.task_key(task_id)] == upload_tasks.TASK_TTL
    assert client.ttls[upload_tasks.draft_key(task_id)] == upload_tasks.TASK_TTL


def test_save_draft_rejects_expired_task(monkeypatch):
    monkeypatch.setattr(upload_tasks, "redis_client", lambda: FakeRedis({}))
    try:
        upload_tasks.save_draft("a" * 32, {})
    except KeyError as exc:
        assert "已过期" in str(exc)
    else:
        raise AssertionError("expired task must not create an orphan draft")


def test_database_url_uses_main_database_environment(monkeypatch):
    monkeypatch.delenv("RAG_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://user:pass@mysql/scwiki")
    settings = RagSettings(_env_file=None, rag_database_url=None)
    assert settings.database_url == "mysql+pymysql://user:pass@mysql/scwiki"


def test_candidate_attachment_listing_and_safe_lookup(tmp_path, monkeypatch):
    monkeypatch.setattr(upload_tasks.settings, "sc_wiki_data_dir", tmp_path)
    task_id = "b" * 32
    root = tmp_path / "upload_PDFs" / "candidates" / "42"
    root.mkdir(parents=True)
    (root / f"{task_id}.pdf").write_bytes(b"pdf")
    (root / f"{task_id}.json").write_text(json.dumps({
        "task_id": task_id,
        "filename": "candidate.pdf",
        "file_sha256": "abc",
        "user_id": 7,
        "created_at": 123,
    }), encoding="utf-8")

    attachments = rag._candidate_attachments(42)
    assert attachments == [{
        "id": task_id,
        "filename": "candidate.pdf",
        "file_sha256": "abc",
        "file_size": 3,
        "uploaded_by_user_id": 7,
        "created_at": 123,
    }]
    assert rag._candidate_attachment_path(42, task_id)[0] == root / f"{task_id}.pdf"
    assert rag._candidate_attachment_path(42, "../secret") is None


def test_public_sql_detail_requires_approved_and_hides_file_path():
    paper = Paper(id=4, title="Approved", review_status="approved", source_file_path="private.pdf")
    paper.key_properties = []
    session = FakeAsyncSession(execute_values=[paper])

    detail = asyncio.run(sql_search.get_paper_detail(session, 4))

    assert "review_status" in str(session.statement)
    assert detail is not None and "source_file_path" not in detail


def test_vector_results_only_keep_approved_papers(monkeypatch):
    session = FakeAsyncSession(execute_values=[2])
    import backend.rag.database as rag_database

    monkeypatch.setattr(rag_database, "async_session_factory", lambda: session)
    results = asyncio.run(vector_search._approved_results([
        {"paper_id": 1, "content": "pending"},
        {"paper_id": 2, "content": "approved"},
    ]))
    assert results == [{"paper_id": 2, "content": "approved"}]


def test_publish_uses_committed_chunk_ids(monkeypatch):
    paper = SimpleNamespace(id=42, review_status="approved")
    chunks = [SimpleNamespace(id=501, chunk_index=0, section_name="Results", content="text")]
    session = FakeAsyncSession(scalar_value=paper, execute_values=chunks)
    import backend.rag.database as rag_database
    import backend.ingest.embedder as embedder

    captured = []
    monkeypatch.setattr(rag_database, "async_session_factory", lambda: session)
    monkeypatch.setattr(embedder, "embed_and_index_chunks", lambda values: captured.extend(values) or len(values))

    result = asyncio.run(rag.publish_approved_paper(42, None))

    assert result["indexed_chunks"] == 1
    assert captured[0]["id"] == "501"


def test_publish_rejects_pending_paper(monkeypatch):
    session = FakeAsyncSession(scalar_value=None)
    import backend.rag.database as rag_database

    monkeypatch.setattr(rag_database, "async_session_factory", lambda: session)
    try:
        asyncio.run(rag.publish_approved_paper(42, None))
    except HTTPException as exc:
        assert exc.status_code == 409
    else:
        raise AssertionError("pending paper must not be published")
