"""Request-scoped configuration for user-selected OpenAI-compatible LLMs."""

from __future__ import annotations

import contextvars
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urlparse
from fastapi import HTTPException, Request

from backend.rag.config import settings


class UserCredentialError(RuntimeError):
    """A user supplied LLM credential or endpoint failed."""

    def __init__(self, message: str, *, code: str = "LLM_USER_CREDENTIAL_FAILED") -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class LlmConfig:
    provider: str
    base_url: str
    model: str
    api_key: str
    user_supplied: bool = False


_current_config: contextvars.ContextVar[LlmConfig | None] = contextvars.ContextVar(
    "scwiki_llm_config", default=None
)


def mask_api_key(value: str) -> str:
    value = str(value or "")
    if len(value) <= 8:
        return "****"
    return f"{value[:3]}****{value[-4:]}"


def validate_base_url(value: str) -> str:
    raw = str(value or "").strip()
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise UserCredentialError("Base URL 必须是有效的 http(s) 地址", code="LLM_URL_INVALID")
    host = parsed.hostname.lower().rstrip(".")
    local_exception = host in {"localhost", "127.0.0.1"}
    if parsed.scheme != "https" and not local_exception:
        raise UserCredentialError("非本机 Base URL 必须使用 https", code="LLM_URL_INSECURE")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(host, parsed.port, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise UserCredentialError("无法解析 Base URL 主机", code="LLM_URL_UNRESOLVABLE") from exc
    for address in addresses:
        ip = ipaddress.ip_address(address)
        if local_exception:
            continue
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise UserCredentialError("Base URL 不允许访问内网地址", code="LLM_URL_PRIVATE")
    return raw.rstrip("/")


def resolve_llm_config(
    provider: str | None = None,
    base_url: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
) -> LlmConfig:
    values = [str(item or "").strip() for item in (provider, base_url, model, api_key)]
    if all(values):
        return LlmConfig(
            provider=values[0],
            base_url=validate_base_url(values[1]),
            model=values[2],
            api_key=values[3],
            user_supplied=True,
        )
    return LlmConfig(
        provider="server-default",
        base_url=settings.completion_base_url,
        model=settings.completion_model,
        api_key=settings.completion_api_key,
    )


def set_llm_config(config: LlmConfig) -> contextvars.Token[LlmConfig | None]:
    return _current_config.set(config)


def reset_llm_config(token: contextvars.Token[LlmConfig | None]) -> None:
    _current_config.reset(token)


def get_llm_config() -> LlmConfig:
    return _current_config.get() or resolve_llm_config()


def request_llm_config(request: Request):
    """FastAPI dependency which scopes header-derived config to one request."""
    try:
        config = resolve_llm_config(
            request.headers.get("X-LLM-Provider"),
            request.headers.get("X-LLM-Base-URL"),
            request.headers.get("X-LLM-Model"),
            request.headers.get("X-LLM-Api-Key"),
        )
        if any("\n" in value or "\r" in value for value in (
            request.headers.get("X-LLM-Provider") or "",
            request.headers.get("X-LLM-Base-URL") or "",
            request.headers.get("X-LLM-Model") or "",
            request.headers.get("X-LLM-Api-Key") or "",
        )):
            raise UserCredentialError("LLM 配置不能包含换行符", code="LLM_HEADER_INVALID")
    except UserCredentialError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": str(exc)}) from exc
    token = set_llm_config(config)
    try:
        yield config
    finally:
        reset_llm_config(token)
