"""Issue #73 integration coverage for scoped LLM request paths."""

import asyncio

import httpx
import pytest
from fastapi import HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError

from backend.api import rag
from backend.rag import llm_context, service


def _user_config() -> llm_context.LlmConfig:
    return llm_context.LlmConfig(
        "custom", "https://llm.example.com/v1", "test-model", "test-key", True,
    )


def test_explore_thread_pool_keeps_request_scoped_base_url(monkeypatch):
    monkeypatch.setattr(service, "_ensure_data_available", lambda: None)
    import backend.rag.agent as agent

    observed = []

    def fake_run(_question, _previous_messages=None):
        observed.append(llm_context.get_llm_config().base_url)
        return {"answer": "ok", "mode": "test", "ideas": []}

    monkeypatch.setattr(agent, "run", fake_run)
    token = llm_context.set_llm_config(_user_config())
    try:
        events = asyncio.run(_collect_events(service.chat_stream("question", explore=True)))
    finally:
        llm_context.reset_llm_config(token)

    assert observed == ["https://llm.example.com/v1"]
    assert events[-1]["data"]["provider"] == "custom"


async def _collect_events(stream):
    return [event async for event in stream]


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_code"),
    [
        (APITimeoutError(httpx.Request("POST", "https://llm.example.com")), 504, "LLM_TIMEOUT"),
        (APIConnectionError(message="offline", request=httpx.Request("POST", "https://llm.example.com")), 502, "LLM_UNREACHABLE"),
        (
            APIStatusError(
                "bad key",
                response=httpx.Response(401, request=httpx.Request("POST", "https://llm.example.com")),
                body=None,
            ),
            400,
            "LLM_AUTH_FAILED",
        ),
        (
            APIStatusError(
                "model not found",
                response=httpx.Response(404, request=httpx.Request("POST", "https://llm.example.com")),
                body=None,
            ),
            400,
            "LLM_MODEL_NOT_FOUND",
        ),
    ],
)
def test_connection_error_mapping(monkeypatch, error, expected_status, expected_code):
    class FailingCompletion:
        def create(self, **_kwargs):
            raise error

    class FailingClient:
        class chat:
            completions = FailingCompletion()

    monkeypatch.setattr(rag, "get_llm_config", _user_config)
    monkeypatch.setattr(rag, "get_llm_client", lambda **_kwargs: FailingClient())

    with pytest.raises(HTTPException) as raised:
        rag.test_llm_connection()

    assert raised.value.status_code == expected_status
    assert raised.value.detail["code"] == expected_code
