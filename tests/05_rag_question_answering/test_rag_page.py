import anyio
from httpx import ASGITransport, AsyncClient

from backend.main import app


def test_rag_page_route_returns_html():
    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/rag")
        assert response.status_code == 200
        assert '<div id="root"></div>' in response.text
        assert "/assets/" in response.text
        assert "/static/js/rag.js" not in response.text

    anyio.run(run)
