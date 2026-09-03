"""Factories for request-scoped generation clients."""

from __future__ import annotations

import httpx
from openai import OpenAI
from langchain_openai import ChatOpenAI

from backend.rag.llm_context import get_llm_config, validate_base_url


def get_llm_client(*, read_timeout: float = 90.0) -> OpenAI:
    config = get_llm_config()
    if not config.api_key:
        raise RuntimeError("LLM API key 未配置")
    base_url = validate_base_url(config.base_url)
    return OpenAI(
        api_key=config.api_key,
        base_url=base_url,
        max_retries=0,
        timeout=httpx.Timeout(600.0, connect=10.0, read=read_timeout),
    )


def get_langchain_llm() -> ChatOpenAI:
    config = get_llm_config()
    if not config.api_key:
        raise RuntimeError("LLM API key 未配置")
    base_url = validate_base_url(config.base_url)
    return ChatOpenAI(
        model=config.model,
        api_key=config.api_key,
        base_url=base_url,
        temperature=0.3,
        max_tokens=2000,
    )
