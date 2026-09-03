"""Issue #73: only superadmins may manage the server default LLM."""

import os

import anyio
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-default-llm-config-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

pytest.importorskip("langchain_openai")

from backend.api.rag import router
from backend.rag import llm_context
from backend.security import get_current_superadmin

app = FastAPI()
app.include_router(router)


def test_default_llm_config_routes_require_superadmin_and_hide_key(monkeypatch, tmp_path):
    monkeypatch.setattr(llm_context.settings, "sc_wiki_data_dir", tmp_path)
    monkeypatch.setattr(llm_context.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("93.184.216.34", 443))
    ])

    async def run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            denied = await client.get("/api/rag/llm/default-config")
            assert denied.status_code in {401, 403}

            app.dependency_overrides[get_current_superadmin] = lambda: object()
            response = await client.put("/api/rag/llm/default-config", json={
                "provider_name": "OpenAI", "base_url": "https://bot.ccnccn.cn/v1",
                "model": "gpt-5.6-sol", "api_key": "private-key",
            })
            assert response.status_code == 200
            data = response.json()["data"]
            assert data["provider_name"] == "OpenAI"
            assert data["api_key_configured"] is True
            assert "private-key" not in str(data)
            assert set(data) == {"provider_name", "model", "base_url", "api_key_configured", "source"}
        app.dependency_overrides.clear()

    try:
        anyio.run(run)
    finally:
        app.dependency_overrides.clear()
