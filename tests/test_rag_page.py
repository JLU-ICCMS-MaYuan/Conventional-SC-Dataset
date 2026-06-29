import anyio
from httpx import ASGITransport, AsyncClient

from backend.main import app


def test_rag_page_route_returns_html():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/rag")
        assert response.status_code == 200
        assert "AI 文献助手" in response.text
        assert "流式连续对话" in response.text
        assert "PDF 上传摄入" in response.text
        assert "rag-stats" in response.text
        assert "/static/js/rag.js" in response.text

    anyio.run(run)
