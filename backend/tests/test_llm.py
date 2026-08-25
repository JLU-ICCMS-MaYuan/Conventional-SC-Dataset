import os
from types import SimpleNamespace

import httpx
import pytest
from openai import APIConnectionError, APITimeoutError


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-llm-test.db")
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

from backend.rag import llm


def _chunk(text):
    return SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])


def _request():
    return httpx.Request("POST", "https://example.invalid/v1/chat/completions")


class _FakeCompletions:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        outcome = self.script.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return iter(_chunk(part) for part in outcome)


def _install_client(monkeypatch, completions):
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(llm, "_client", lambda _read_timeout: fake_client)


def test_complete_json_streams_and_reports_partial(monkeypatch):
    completions = _FakeCompletions([['{"paper": {"title": "Pot', 'ential"}}']])
    _install_client(monkeypatch, completions)
    partials = []

    result = llm.complete_json("sys", "user", on_partial=partials.append)

    assert result == {"paper": {"title": "Potential"}}
    assert partials == ['{"paper": {"title": "Pot', '{"paper": {"title": "Potential"}}']
    assert completions.calls == 1


def test_complete_json_retries_once_after_timeout(monkeypatch):
    completions = _FakeCompletions([
        APITimeoutError(request=_request()),
        ['{"ok": true}'],
    ])
    _install_client(monkeypatch, completions)

    assert llm.complete_json("sys", "user", retries=1) == {"ok": True}
    assert completions.calls == 2


def test_complete_json_gives_up_after_single_retry(monkeypatch):
    completions = _FakeCompletions([
        APITimeoutError(request=_request()),
        APIConnectionError(request=_request()),
        ['{"ok": true}'],
    ])
    _install_client(monkeypatch, completions)

    with pytest.raises(APIConnectionError):
        llm.complete_json("sys", "user", retries=1)
    assert completions.calls == 2
