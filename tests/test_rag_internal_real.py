from pathlib import Path

import pytest

from backend.rag import service


DATA_ROOT = Path(__file__).resolve().parents[1].parent / "Conventional-SC-Dataset-talk"
DEV_DB = DATA_ROOT / "dev.db"
CHROMA_DIR = DATA_ROOT / "chroma_db"


@pytest.mark.skipif(not DEV_DB.exists() or not CHROMA_DIR.exists(), reason="RAG data not available")
def test_real_rag_health_detects_adjacent_data(monkeypatch):
    monkeypatch.setenv("RAG_DATA_ROOT", str(DATA_ROOT))
    from backend.rag.config import get_rag_settings
    get_rag_settings.cache_clear()

    status = service.health()

    assert status["available"] is True
    assert status["database_available"] is True
    assert status["chroma_available"] is True


@pytest.mark.skipif(not DEV_DB.exists() or not CHROMA_DIR.exists(), reason="RAG data not available")
@pytest.mark.asyncio
async def test_real_rag_search_returns_standard_shape(monkeypatch):
    monkeypatch.setenv("RAG_DATA_ROOT", str(DATA_ROOT))
    from backend.rag.config import get_rag_settings
    get_rag_settings.cache_clear()

    result = await service.search("LaH10", top_k=3)

    assert result["query"] == "LaH10"
    assert "mode" in result
    assert "superconductors" in result
    assert "chunks" in result
    assert "papers" in result
    assert "total" in result
