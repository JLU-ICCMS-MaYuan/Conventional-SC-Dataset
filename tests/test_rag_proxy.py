import anyio
import httpx
from httpx import ASGITransport, AsyncClient

from backend.main import app


def test_rag_health_available(monkeypatch):
    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/health"
        return {"status": "ok"}

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json() == {
            "available": True,
            "service_url_configured": True,
        }

    anyio.run(run)


def test_rag_health_unavailable_on_connection_error(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/health")
        assert response.status_code == 200
        assert response.json()["available"] is False
        assert response.json()["service_url_configured"] is True
        assert response.json()["message"] == "AI 文献助手服务暂不可用"

    anyio.run(run)


def test_rag_search_rejects_blank_query():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "   "})
        assert response.status_code == 400
        assert response.json()["detail"] == "搜索内容不能为空"

    anyio.run(run)


def test_rag_search_proxies_success(monkeypatch):
    payload = {
        "mode": "formula",
        "query": "LaH10",
        "superconductors": [],
        "papers": [],
        "chunks": [],
        "related_paper_ids": [],
        "total": 0,
    }

    async def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert path == "/api/search"
        assert kwargs["params"] == {"q": "LaH10", "top_k": 10}
        return payload

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": " LaH10 ", "top_k": 10})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_chat_rejects_blank_question():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "  "})
        assert response.status_code == 400
        assert response.json()["detail"] == "问题不能为空"

    anyio.run(run)


def test_rag_chat_proxies_success(monkeypatch):
    payload = {
        "answer": "LaH10 的 Tc 与压力取决于具体文献记录。",
        "chunks_used": 3,
        "citations": [],
        "model": "deepseek-chat",
        "source": "rag",
        "papers": {},
        "top10": [],
    }

    async def fake_request(method, path, **kwargs):
        assert method == "POST"
        assert path == "/api/chat"
        assert kwargs["json"] == {"question": "LaH10 的 Tc？"}
        return payload

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": " LaH10 的 Tc？ "})
        assert response.status_code == 200
        assert response.json() == {"ok": True, "data": payload}

    anyio.run(run)


def test_rag_search_connection_error_returns_503(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/rag/search", params={"q": "LaH10"})
        assert response.status_code == 503
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手服务暂不可用"

    anyio.run(run)


def test_rag_chat_timeout_returns_504(monkeypatch):
    async def fake_request(method, path, **kwargs):
        raise httpx.TimeoutException("timeout")

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 504
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手响应超时，请稍后重试"

    anyio.run(run)


def test_rag_chat_talk_http_error_returns_502(monkeypatch):
    async def fake_request(method, path, **kwargs):
        request = httpx.Request(method, f"http://rag.local{path}")
        response = httpx.Response(500, json={"detail": "boom"}, request=request)
        raise httpx.HTTPStatusError("server error", request=request, response=response)

    monkeypatch.setattr("backend.api.rag._request_talk_json", fake_request)

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post("/api/rag/chat", json={"question": "LaH10 的 Tc？"})
        assert response.status_code == 502
        assert response.json()["detail"]["ok"] is False
        assert response.json()["detail"]["message"] == "AI 文献助手返回错误"
        assert "HTTP 500" in response.json()["detail"]["detail"]

    anyio.run(run)
