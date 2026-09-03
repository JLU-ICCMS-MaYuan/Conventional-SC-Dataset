"""Request-scoped configuration for user-selected OpenAI-compatible LLMs."""

from __future__ import annotations

import contextvars
import ipaddress
import json
import os
import socket
from dataclasses import dataclass
from pathlib import Path
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


_PROVIDER_NAMES_BY_HOST = {
    "api.deepseek.com": "DeepSeek",
    "api.moonshot.cn": "Kimi",
    "open.bigmodel.cn": "GLM",
    "dashscope.aliyuncs.com": "Qwen",
    "api.openai.com": "OpenAI",
    "api.anthropic.com": "Claude",
}
_PROVIDER_NAMES_BY_ID = {
    "deepseek": "DeepSeek",
    "kimi": "Kimi",
    "glm": "GLM",
    "qwen": "Qwen",
    "openai": "OpenAI",
    "claude": "Claude",
    "custom": "Custom",
}


def _default_config_path() -> Path:
    return settings.sc_wiki_data_dir / "runtime" / "default_llm.json"


def _environment_default_config() -> LlmConfig:
    return LlmConfig(
        provider="server-default",
        base_url=settings.completion_base_url,
        model=settings.completion_model,
        api_key=settings.completion_api_key,
    )


def get_server_default_config() -> LlmConfig:
    """Load the superadmin override, falling back to deployment environment settings."""
    path = _default_config_path()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        provider_name = str(data["provider_name"]).strip()
        base_url = validate_base_url(str(data["base_url"]))
        model = str(data["model"]).strip()
        api_key = str(data["api_key"]).strip()
        if not all((provider_name, base_url, model, api_key)):
            raise ValueError("默认 LLM 配置字段不完整")
        return LlmConfig(
            provider="server-default", base_url=base_url, model=model, api_key=api_key,
        )
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError, UserCredentialError):
        return _environment_default_config()


def server_default_metadata() -> dict[str, str | bool]:
    """Return safe-to-display settings for the superadmin configuration panel."""
    config = get_server_default_config()
    path = _default_config_path()
    provider_name = ""
    try:
        provider_name = str(json.loads(path.read_text(encoding="utf-8"))["provider_name"]).strip()
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        host = (urlparse(config.base_url).hostname or "").lower().rstrip(".")
        provider_name = settings.llm_provider_name.strip() or _PROVIDER_NAMES_BY_HOST.get(host, "Server default")
    return {
        "provider_name": provider_name,
        "model": config.model,
        "base_url": config.base_url,
        "api_key_configured": bool(config.api_key),
        "source": "runtime" if path.is_file() else "environment",
    }


def save_server_default_config(
    *, provider_name: str, base_url: str, model: str, api_key: str | None,
) -> dict[str, str | bool]:
    """Atomically persist a superadmin-controlled default without ever returning its key."""
    existing = get_server_default_config()
    name = provider_name.strip()
    normalized_url = validate_base_url(base_url)
    normalized_model = model.strip()
    final_key = api_key.strip() if api_key and api_key.strip() else existing.api_key
    if not all((name, normalized_url, normalized_model, final_key)):
        raise UserCredentialError("供应商名称、Base URL、模型名和 API Key 必须完整", code="LLM_DEFAULT_INVALID")

    path = _default_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    payload = json.dumps({
        "provider_name": name, "base_url": normalized_url,
        "model": normalized_model, "api_key": final_key,
    }, ensure_ascii=False)
    temporary.write_text(payload, encoding="utf-8")
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)
    return server_default_metadata()


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
    return get_server_default_config()


def set_llm_config(config: LlmConfig) -> contextvars.Token[LlmConfig | None]:
    return _current_config.set(config)


def reset_llm_config(token: contextvars.Token[LlmConfig | None]) -> None:
    _current_config.reset(token)


def get_llm_config() -> LlmConfig:
    return _current_config.get() or resolve_llm_config()


def llm_display_metadata(config: LlmConfig | None = None) -> dict[str, str]:
    """Return safe-to-display LLM metadata without endpoint or credential fields."""
    resolved = config or get_llm_config()
    host = (urlparse(resolved.base_url).hostname or "").lower().rstrip(".")
    if resolved.user_supplied:
        provider_name = _PROVIDER_NAMES_BY_ID.get(resolved.provider, resolved.provider)
    elif config is None:
        provider_name = str(server_default_metadata()["provider_name"])
    else:
        provider_name = _PROVIDER_NAMES_BY_HOST.get(host, "Server default")
    return {
        "provider": resolved.provider,
        "provider_name": provider_name,
        "model": resolved.model,
        "source": "browser" if resolved.user_supplied else "server",
    }


async def request_llm_config(request: Request):
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
