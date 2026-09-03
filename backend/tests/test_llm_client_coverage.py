"""Issue #73 factory coverage and endpoint validation."""

import pytest

pytest.importorskip("langchain_openai")

from backend.rag import llm_client, llm_context


def test_factory_revalidates_worker_configuration(monkeypatch):
    config = llm_context.LlmConfig("custom", "http://remote.example/v1", "model", "key", True)
    monkeypatch.setattr(llm_context, "get_llm_config", lambda: config)
    monkeypatch.setattr(llm_client, "get_llm_config", lambda: config)
    with pytest.raises(llm_context.UserCredentialError) as error:
        llm_client.get_llm_client()
    assert error.value.code == "LLM_URL_INSECURE"


def test_generation_sources_do_not_construct_clients_from_server_keys():
    from pathlib import Path
    root = Path(__file__).parents[1]
    source_files = list((root / "rag").rglob("*.py")) + [root / "ingest" / "extractor.py"]
    violations = []
    for path in source_files:
        text = path.read_text(encoding="utf-8")
        if path.name in {"llm_client.py", "config.py"}:
            continue
        if "OpenAI(api_key=settings.deepseek" in text or "ChatOpenAI(api_key=settings.deepseek" in text:
            violations.append(str(path))
    assert violations == []
