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
        self.statements = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    async def scalar(self, statement):
        self.statement = statement
        self.statements.append(statement)
        return self.scalar_value

    async def execute(self, statement):
        self.statement = statement
        self.statements.append(statement)
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
    paper = Paper(id=4, title="Approved", review_status="approved")
    session = FakeAsyncSession(scalar_value=0, execute_values=[paper])

    detail = asyncio.run(sql_search.get_paper_detail(session, 4))

    assert any("review_status" in str(statement) for statement in session.statements)
    assert any("paper_revision" in str(statement) for statement in session.statements)
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


class FakeBegin:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class FakePaperSession:
    def __init__(self):
        self.added = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def begin(self):
        return FakeBegin()

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def execute(self, statement):
        return FakeResult([])


def _state_with_material(material):
    return {"material": material}


def _minimal_non_review_draft(material_states, research_materials=None):
    paper = {
        "title": "测试论文",
        "year": 2024,
        "paper_type": "experimental",
        "superconductor_kind": "unknown",
        "material_families": [{"id": None, "name": "氢化物", "status": "pending"}],
    }
    if research_materials is not None:
        paper["research_materials"] = research_materials
    return {"paper": paper, "material_states": material_states}


def test_validate_draft_accepts_materials_from_states():
    draft = _minimal_non_review_draft([_state_with_material("LaH10")])

    _paper, states = rag._validate_draft(draft)

    assert states[0]["material"] == "LaH10"


def test_validate_draft_rejects_when_materials_missing_everywhere():
    draft = _minimal_non_review_draft([_state_with_material("  ")])

    try:
        rag._validate_draft(draft)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["code"] == "research_material_required"
    else:
        raise AssertionError("paper 与材料状态均为空时必须拒绝")


def test_create_pending_paper_derives_research_materials(tmp_path, monkeypatch):
    import backend.rag.database as rag_database
    from backend.ingest import scientific_drafts, upload_jobs

    monkeypatch.setattr(upload_jobs, "_normalize_draft", lambda draft: draft)

    async def _resolve_noop(_session, _draft):
        return None

    async def _persist_noop(_session, _paper, _draft):
        return []

    monkeypatch.setattr(rag, "_resolve_draft_classifications", _resolve_noop)
    monkeypatch.setattr(scientific_drafts, "persist_scientific_draft", _persist_noop)
    monkeypatch.setattr(upload_tasks, "markdown_path", lambda _task_id: tmp_path / "missing.md")
    session = FakePaperSession()
    monkeypatch.setattr(rag_database, "async_session_factory", lambda: session)

    draft = _minimal_non_review_draft([
        _state_with_material("LaH10"),
        _state_with_material("CeCu2Si2"),
        _state_with_material("LaH10"),
    ])
    asyncio.run(rag._create_pending_paper("c" * 32, {"user_id": 1}, draft))

    paper = next(obj for obj in session.added if isinstance(obj, Paper))
    assert paper.research_materials == ["LaH10", "CeCu2Si2"]


def test_space_groups_endpoint_returns_full_table():
    result = asyncio.run(rag.list_space_groups(SimpleNamespace(id=1)))

    groups = result["space_groups"]
    assert len(groups) == 230
    assert [item["number"] for item in groups] == sorted(item["number"] for item in groups)
    assert {"number": 225, "symbol": "Fm-3m"} in groups
    assert all(set(item) == {"number", "symbol"} for item in groups)


def test_validate_draft_accepts_one_sided_pressure_range():
    state = _state_with_material("LaH10")
    state["pressure_min_gpa"] = 200
    state["pressure_max_gpa"] = None
    draft = _minimal_non_review_draft([state])

    _paper, states = rag._validate_draft(draft)

    assert states[0]["pressure_min_gpa"] == 200


def test_validate_draft_rejects_inverted_pressure_range():
    state = _state_with_material("LaH10")
    state["pressure_min_gpa"] = 300
    state["pressure_max_gpa"] = 200
    draft = _minimal_non_review_draft([state])

    try:
        rag._validate_draft(draft)
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["code"] == "invalid_pressure_range"
        assert "第 1 个材料状态的压强区间 min 不能大于 max" in exc.detail["message"]
    else:
        raise AssertionError("min > max 的压强区间必须在提交校验时拒绝")


def _half_filled_draft():
    state = _state_with_material("LaH10")
    state["tc_results"] = [{"result_kind": "experimental"}]
    return _minimal_non_review_draft([state])


def test_put_draft_saves_half_filled_draft(monkeypatch):
    import backend.rag.database as rag_database
    from backend.ingest import upload_jobs

    task_id = "d" * 32
    monkeypatch.setattr(rag, "_task_for_user", lambda _task_id, _user: {"task_id": task_id})
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: None)
    monkeypatch.setattr(upload_jobs, "_normalize_draft", lambda draft: draft)

    async def _resolve_noop(_session, _draft):
        return None

    monkeypatch.setattr(rag, "_resolve_draft_classifications", _resolve_noop)
    monkeypatch.setattr(rag_database, "async_session_factory", lambda: FakeAsyncSession())

    saved = {}

    def _save(_task_id, draft):
        saved["draft"] = draft
        return draft

    monkeypatch.setattr(upload_tasks, "save_draft", _save)

    result = asyncio.run(rag.put_upload_draft(task_id, _half_filled_draft(), SimpleNamespace(id=1)))

    assert result["ok"] is True
    assert result["data"]["material_states"][0]["tc_results"] == [{"result_kind": "experimental"}]
    assert saved["draft"] == result["data"]


def test_put_draft_rejects_experimental_tc_calculation_context(monkeypatch):
    import backend.rag.database as rag_database
    from backend.ingest import upload_jobs

    task_id = "f" * 32
    draft = _minimal_non_review_draft([{
        "material": "LaH10",
        "tc_results": [{
            "result_kind": "experimental",
            "tc_method": "experimental",
            "tc_value_k": 203,
            "calculation_context": {"lambda_ep": 2.1},
        }],
    }])
    monkeypatch.setattr(rag, "_task_for_user", lambda _task_id, _user: {"task_id": task_id})
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: None)
    monkeypatch.setattr(upload_jobs, "_normalize_draft", lambda value: value)

    async def _resolve_noop(_session, _draft):
        return None

    monkeypatch.setattr(rag, "_resolve_draft_classifications", _resolve_noop)
    monkeypatch.setattr(rag_database, "async_session_factory", lambda: FakeAsyncSession())
    monkeypatch.setattr(upload_tasks, "save_draft", lambda *_args: (_ for _ in ()).throw(AssertionError("不应保存非法草稿")))

    try:
        asyncio.run(rag.put_upload_draft(task_id, draft, SimpleNamespace(id=1)))
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["code"] == "experimental_tc_calculation_context_forbidden"
        assert "第 1 个材料状态的第 1 条 Tc" in exc.detail["message"]
    else:
        raise AssertionError("实验 Tc 携带计算上下文必须被草稿保存端点拒绝")


def test_submit_rejects_same_half_filled_draft():
    try:
        rag._validate_draft(_half_filled_draft())
    except HTTPException as exc:
        assert exc.status_code == 400
        assert exc.detail["code"] == "tc_method_required"
    else:
        raise AssertionError("半成品草稿在提交校验时必须拒绝")


def test_submit_failure_rolls_state_back_to_ready(monkeypatch):
    from backend.ingest import upload_contracts

    task_id = "e" * 32
    draft = {"paper": {"title": "t"}, "material_states": []}

    async def _no_submitted(_task_id):
        return None

    monkeypatch.setattr(rag, "_submitted_paper_for_task", _no_submitted)
    monkeypatch.setattr(
        rag,
        "_task_for_user",
        lambda _task_id, _user: {
            "task_id": task_id,
            "user_id": 2,
            "stage": "ready",
            "processing_status": "succeeded",
        },
    )
    monkeypatch.setattr(upload_tasks, "get_draft", lambda _task_id: draft)
    monkeypatch.setattr(
        upload_contracts.CleanupContext, "from_state", staticmethod(lambda _task_id, _state: None)
    )

    state_calls = []

    def _update_state(_task_id, **fields):
        state_calls.append(fields)

    monkeypatch.setattr(upload_tasks, "update_state", _update_state)

    async def _boom(_task_id, _state, _draft):
        raise RuntimeError("模拟提交写入失败")

    monkeypatch.setattr(rag, "_create_pending_paper", _boom)

    try:
        asyncio.run(rag._submit_upload_draft_locked(task_id, SimpleNamespace(id=2)))
    except RuntimeError:
        pass
    else:
        raise AssertionError("提交异常必须继续向上抛出")

    assert state_calls[0] == {"status": "submitting", "submission_status": "submitting"}
    assert state_calls[-1] == {"status": "ready", "submission_status": "failed"}
