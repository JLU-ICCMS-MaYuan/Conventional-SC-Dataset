import anyio
from httpx import ASGITransport, AsyncClient

from backend.main import app
from backend.rag import service


def test_rag_health_uses_internal_service(monkeypatch):
    monkeypatch.setattr(service, "health", lambda: {
        "available": True,
        "database_available": True,
        "chroma_available": True,
        "chat_available": False,
        "message": "RAG 检索可用，LLM 问答未配置",
    })

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json()["available"] is True
        assert response.json()["chat_available"] is False
        assert response.json()["message"] == "RAG 检索可用，LLM 问答未配置"

    anyio.run(run)


def test_rag_search_internal_success(monkeypatch):
    payload = {"mode": "formula", "query": "LaH10", "superconductors": [], "chunks": [], "papers": [], "total": 0}

    async def fake_search(query, top_k=10, mode=None):
        assert query == "LaH10"
        assert top_k == 10
        assert mode is None
        return payload

    monkeypatch.setattr(service, "search", fake_search)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": " LaH10 ", "top_k": 10})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_search_data_unavailable(monkeypatch):
    async def fake_search(query, top_k=10, mode=None):
        raise service.RagDataUnavailableError("AI 文献助手数据不可用")

    monkeypatch.setattr(service, "search", fake_search)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "LaH10"})
        assert response.status_code == 503
        assert response.json()["detail"]["message"] == "AI 文献助手数据不可用"

    anyio.run(run)


def test_rag_chat_internal_success_with_history(monkeypatch):
    payload = {"answer": "ok", "chunks_used": 0, "citations": [], "model": "deepseek-chat", "source": "rag"}

    async def fake_chat(question, top_k=15, rerank_top_k=5, history=None):
        assert question == "LaH10 的 Tc？"
        assert top_k == 12
        assert rerank_top_k == 4
        assert history == [{"role": "user", "content": "上一问"}]
        return payload

    monkeypatch.setattr(service, "chat", fake_chat)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={
                "question": " LaH10 的 Tc？ ",
                "top_k": 12,
                "rerank_top_k": 4,
                "history": [{"role": "user", "content": "上一问"}],
            })
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_chat_stream_sse(monkeypatch):
    async def fake_chat_stream(question, top_k=15, rerank_top_k=5, history=None):
        assert question == "继续"
        assert history == [{"role": "assistant", "content": "上一答"}]
        yield {"type": "token", "data": "答"}
        yield {"type": "done", "data": {"answer": "答", "citations": []}}

    monkeypatch.setattr(service, "chat_stream", fake_chat_stream)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat/stream", json={
                "question": "继续",
                "history": [{"role": "assistant", "content": "上一答"}],
            })
        assert response.status_code == 200
        assert "event: token" in response.text
        assert 'data: "答"' in response.text
        assert "event: done" in response.text
        assert "event: end" in response.text

    anyio.run(run)


def test_rag_stats_and_details_routes(monkeypatch):
    async def fake_stats():
        return {"papers": 1, "superconductors": 2, "records": 3, "chunks": 4, "chroma_chunks": 5, "chemical_systems": 6}

    async def fake_papers(keyword=None, limit=20):
        assert keyword == "LaH10"
        return [{"id": 1, "title": "paper"}]

    async def fake_paper_detail(paper_id):
        assert paper_id == 1
        return {"id": 1, "title": "paper"}

    async def fake_superconductors(formula=None, elements=None, limit=50):
        assert formula == "LaH10"
        return [{"id": 2, "chemical_formula": "LaH10"}]

    async def fake_superconductor_detail(superconductor_id):
        assert superconductor_id == 2
        return {"id": 2, "chemical_formula": "LaH10"}

    monkeypatch.setattr(service, "stats", fake_stats)
    monkeypatch.setattr(service, "list_papers", fake_papers)
    monkeypatch.setattr(service, "paper_detail", fake_paper_detail)
    monkeypatch.setattr(service, "search_superconductors", fake_superconductors)
    monkeypatch.setattr(service, "superconductor_detail", fake_superconductor_detail)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            assert (await client.get("/api/rag/stats")).json()["data"]["papers"] == 1
            assert (await client.get("/api/rag/papers", params={"keyword": "LaH10"})).json()["data"][0]["id"] == 1
            assert (await client.get("/api/rag/papers/1")).json()["data"]["id"] == 1
            assert (await client.get("/api/rag/superconductors", params={"formula": "LaH10"})).json()["data"][0]["id"] == 2
            assert (await client.get("/api/rag/superconductors/2")).json()["data"]["id"] == 2

    anyio.run(run)


def test_rag_upload_pdf_rejects_non_pdf():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/rag/upload-pdf",
                files={"file": ("note.txt", b"hello", "text/plain")},
            )
        assert response.status_code == 400
        assert response.json()["detail"] == "只支持 PDF 文件"

    anyio.run(run)


def test_rag_chat_llm_unconfigured(monkeypatch):
    async def fake_chat(question, top_k=15, rerank_top_k=5, history=None):
        raise service.RagChatUnavailableError("LLM 问答未配置")

    monkeypatch.setattr(service, "chat", fake_chat)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 503
        assert response.json()["detail"]["message"] == "LLM 问答未配置"

    anyio.run(run)
