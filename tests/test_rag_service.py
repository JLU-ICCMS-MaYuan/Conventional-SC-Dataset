from pathlib import Path

import pytest

from backend.rag.config import get_rag_settings
from backend.rag import service


def test_health_reports_missing_data(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATA_ROOT", str(tmp_path / "missing-talk"))
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is False
    assert status["database_available"] is False
    assert status["chroma_available"] is False
    assert status["chat_available"] is False
    assert status["message"] == "AI 文献助手数据不可用"


def test_health_reports_search_available_without_llm(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True
    assert status["chat_available"] is False
    assert status["message"] == "RAG 检索可用，LLM 问答未配置"


@pytest.mark.asyncio
async def test_search_raises_when_data_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATA_ROOT", str(tmp_path / "missing-talk"))
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagDataUnavailableError):
        await service.search("LaH10", top_k=3)


@pytest.mark.asyncio
async def test_chat_raises_when_llm_missing(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagChatUnavailableError):
        await service.chat("LaH10 的 Tc？")


@pytest.mark.asyncio
async def test_chat_passes_history_and_ranking(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    get_rag_settings.cache_clear()

    async def fake_ask(question, top_k=15, rerank_top_k=5, history=None, verbose=False):
        assert question == "继续"
        assert top_k == 11
        assert rerank_top_k == 3
        assert history == [{"role": "user", "content": "上一问"}]
        assert verbose is True
        return {"answer": "ok"}

    import backend.rag.rag.engine as engine
    monkeypatch.setattr(engine, "ask", fake_ask)

    result = await service.chat(
        "继续",
        top_k=11,
        rerank_top_k=3,
        history=[{"role": "user", "content": "上一问"}],
    )

    assert result == {"answer": "ok"}


@pytest.mark.asyncio
async def test_chat_stream_passes_history(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    (data_root / "dev.db").write_bytes(b"")
    (data_root / "chroma_db").mkdir()
    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    get_rag_settings.cache_clear()

    async def fake_ask_stream(question, top_k=15, rerank_top_k=5, history=None):
        assert question == "继续"
        assert top_k == 9
        assert rerank_top_k == 2
        assert history == [{"role": "assistant", "content": "上一答"}]
        yield {"type": "token", "data": "ok"}

    import backend.rag.rag.engine as engine
    monkeypatch.setattr(engine, "ask_stream", fake_ask_stream)

    events = []
    async for event in service.chat_stream(
        "继续",
        top_k=9,
        rerank_top_k=2,
        history=[{"role": "assistant", "content": "上一答"}],
    ):
        events.append(event)

    assert events == [{"type": "token", "data": "ok"}]



def test_knowledge_graph_uses_configured_rag_data_root(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    db_path = data_root / "dev.db"

    import sqlite3
    conn = sqlite3.connect(db_path)
    conn.executescript("""
        create table papers (id integer primary key, title text, review_status text);
        create table superconductors (id integer primary key, chemical_formula text);
        create table superconductor_records (
            id integer primary key,
            superconductor_id integer,
            paper_id integer,
            allen_dynes_tc real,
            experimental_tc real,
            pressure_gpa real,
            lambda_value real,
            omega_log real,
            space_group_symbol text
        );
        insert into papers values (1, 'Configured DB Paper', 'approved');
        insert into superconductors values (1, 'TestH10');
        insert into superconductor_records values (1, 1, 1, 321.0, null, 200.0, 2.5, 100.0, 'Fm-3m');
    """)
    conn.commit()
    conn.close()

    monkeypatch.setenv("RAG_DATA_ROOT", str(data_root))
    get_rag_settings.cache_clear()

    import backend.rag.knowledge_graph as kg

    rows = kg.query("超导温度(AD)", operator=">", value="300")

    assert rows == [{
        "subject": "TestH10",
        "predicate": "超导温度(AD)",
        "object": "321.0",
        "paper_id": 1,
        "paper_title": "Configured DB Paper",
    }]
