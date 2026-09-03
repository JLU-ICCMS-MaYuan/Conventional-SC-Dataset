"""Issue #73 request-scoped provider configuration tests."""

import pytest
from starlette.requests import Request

from backend.rag import llm_context


def _request(headers: dict[str, str]) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
    }
    return Request(scope)


def test_resolve_all_user_fields_without_server_fallback(monkeypatch):
    monkeypatch.setattr(llm_context.settings, "llm_api_key", "server-key")
    monkeypatch.setattr(llm_context.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("93.184.216.34", 443))
    ])
    config = llm_context.resolve_llm_config(
        "custom", "https://llm.example.com/v1", "custom-model", "user-key"
    )
    assert config.provider == "custom"
    assert config.model == "custom-model"
    assert config.api_key == "user-key"
    assert config.user_supplied is True


def test_missing_user_field_falls_back_to_server(monkeypatch):
    monkeypatch.setattr(llm_context.settings, "llm_api_key", "server-key")
    monkeypatch.setattr(llm_context.settings, "llm_base_url", "https://server.example.com/v1")
    monkeypatch.setattr(llm_context.settings, "llm_model", "server-model")
    config = llm_context.resolve_llm_config("custom", "https://llm.example.com/v1", "", "user-key")
    assert (config.provider, config.model, config.api_key) == (
        "server-default", "server-model", "server-key"
    )


@pytest.mark.parametrize("address", [
    "10.0.0.1", "172.16.0.1", "192.168.1.1", "169.254.169.254", "127.0.0.1",
])
def test_private_and_loopback_addresses_are_rejected(monkeypatch, address):
    monkeypatch.setattr(llm_context.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, (address, 443))
    ])
    if address == "127.0.0.1":
        assert llm_context.validate_base_url("http://127.0.0.1/v1")
        return
    with pytest.raises(llm_context.UserCredentialError) as error:
        llm_context.validate_base_url(f"https://gateway.example/v1")
    assert error.value.code == "LLM_URL_PRIVATE"


def test_request_dependency_sets_and_resets_context(monkeypatch):
    monkeypatch.setattr(llm_context.socket, "getaddrinfo", lambda *args, **kwargs: [
        (None, None, None, None, ("93.184.216.34", 443))
    ])
    dependency = llm_context.request_llm_config(_request({
        "X-LLM-Provider": "custom",
        "X-LLM-Base-URL": "https://llm.example.com/v1",
        "X-LLM-Model": "model",
        "X-LLM-Api-Key": "user-key",
    }))
    config = next(dependency)
    assert llm_context.get_llm_config() == config
    with pytest.raises(StopIteration):
        next(dependency)
    assert llm_context.get_llm_config().provider == "server-default"


def test_mask_api_key():
    assert llm_context.mask_api_key("sk-abcdefghijkl") == "sk-****ijkl"
    assert llm_context.mask_api_key("short") == "****"
