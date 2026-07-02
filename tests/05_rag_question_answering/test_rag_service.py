from pathlib import Path

import pytest

from backend.rag.config import get_rag_settings
from backend.rag import service


def test_health_reports_missing_data_when_mysql_unreachable(monkeypatch):
    monkeypatch.setenv("RAG_DATABASE_URL", "mysql+asyncmy://nobody:bad@127.0.0.1:3306/nonexistent_db")
    monkeypatch.setenv("RAG_CHROMA_PATH", "/nonexistent/chroma")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # 覆盖 .env 中的 Key
    monkeypatch.setenv("OPENAI_API_KEY", "")
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is False
    assert status["database_available"] is False
    assert status["chroma_available"] is False
    assert status["chat_available"] is False
    assert status["message"] == "AI 文献助手数据不可用"


def test_health_reports_search_available_without_llm(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_dir))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # 覆盖 .env 中的 Key
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True
    assert status["chat_available"] is False
    assert status["message"] == "RAG 检索可用，LLM 问答未配置"


@pytest.mark.asyncio
async def test_search_raises_when_data_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("RAG_DATABASE_URL", "mysql+asyncmy://nobody:bad@127.0.0.1:3306/nonexistent_db")
    monkeypatch.setenv("RAG_CHROMA_PATH", "/nonexistent/chroma")
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagDataUnavailableError):
        await service.search("LaH10", top_k=3)


@pytest.mark.asyncio
async def test_chat_raises_when_llm_missing(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_dir))
    monkeypatch.setenv("DEEPSEEK_API_KEY", "")  # 覆盖 .env 中的 Key
    get_rag_settings.cache_clear()

    with pytest.raises(service.RagChatUnavailableError):
        await service.chat("LaH10 的 Tc？")


@pytest.mark.asyncio
async def test_chat_passes_history_and_ranking(monkeypatch, tmp_path):
    monkeypatch.setenv(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_dir))
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
    monkeypatch.setenv(
        "RAG_DATABASE_URL",
        "mysql+asyncmy://work:12345678@127.0.0.1:3306/superconductor_dataset?charset=utf8mb4",
    )
    chroma_dir = tmp_path / "chroma_db"
    chroma_dir.mkdir()
    monkeypatch.setenv("RAG_CHROMA_PATH", str(chroma_dir))
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


@pytest.mark.asyncio
async def test_knowledge_graph_query_async(monkeypatch, tmp_path):
    data_root = tmp_path / "talk"
    data_root.mkdir()
    db_path = data_root / "dev.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    import sqlite3
    conn = sqlite3.connect(str(db_path))
    conn.executescript("""
        CREATE TABLE papers (id INTEGER PRIMARY KEY, title TEXT, review_status TEXT);
        CREATE TABLE superconductors (id INTEGER PRIMARY KEY, chemical_formula TEXT);
        CREATE TABLE superconductor_records (
            id INTEGER PRIMARY KEY,
            superconductor_id INTEGER,
            paper_id INTEGER,
            allen_dynes_tc REAL
        );
        INSERT INTO papers VALUES (1, 'Configured DB Paper', 'approved');
        INSERT INTO superconductors VALUES (1, 'TestH10');
        INSERT INTO superconductor_records VALUES (1, 1, 1, 321.0);
    """)
    conn.commit()
    conn.close()

    # 重写 database 模块的全局 session factory，指向测试 SQLite
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

    test_engine = create_async_engine(db_url, echo=False)
    test_factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    monkeypatch.setattr("backend.rag.database.async_session_factory", test_factory)
    monkeypatch.setattr("backend.rag.knowledge_graph.async_session_factory", test_factory)

    from backend.rag import knowledge_graph as kg

    rows = await kg.query("超导温度(AD)", operator=">", value="300")

    assert rows == [{
        "subject": "TestH10",
        "predicate": "超导温度(AD)",
        "object": "321.0",
        "paper_id": 1,
        "paper_title": "Configured DB Paper",
    }]

    await test_engine.dispose()
