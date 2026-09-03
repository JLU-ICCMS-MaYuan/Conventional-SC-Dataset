"""统一的 OpenAI 兼容 LLM JSON 调用入口。"""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

from openai import APIConnectionError, APITimeoutError, OpenAI
from backend.rag.llm_client import get_llm_client
from backend.rag.llm_context import get_llm_config


def _client(read_timeout: float) -> OpenAI:
    return get_llm_client(read_timeout=read_timeout)


def _extract_json(content: str) -> dict[str, Any]:
    text = (content or "").strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end <= start:
            raise RuntimeError("LLM 未返回有效 JSON")
        return json.loads(text[start : end + 1])


def _stream_json(
    system_prompt: str,
    user_prompt: str,
    *,
    on_partial: Callable[[str], None] | None,
    read_timeout: float,
) -> dict[str, Any]:
    """单次流式调用：逐块累积文本，可选回报中间内容，结束后解析 JSON。"""
    stream = _client(read_timeout).chat.completions.create(
        model=get_llm_config().model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
        stream=True,
    )
    accumulated: list[str] = []
    for chunk in stream:
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta.content
        if not delta:
            continue
        accumulated.append(delta)
        if on_partial is not None:
            on_partial("".join(accumulated))
    return _extract_json("".join(accumulated))


def complete_json(
    system_prompt: str,
    user_prompt: str,
    *,
    on_partial: Callable[[str], None] | None = None,
    read_timeout: float = 90.0,
    retries: int = 1,
) -> dict[str, Any]:
    """流式请求 LLM 并解析 JSON。连接中断或读超时最多额外重试 retries 次。"""
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return _stream_json(
                system_prompt, user_prompt,
                on_partial=on_partial, read_timeout=read_timeout,
            )
        except (APITimeoutError, APIConnectionError) as exc:
            last_error = exc
            if attempt >= retries:
                break
            print(f"  [LLM] 请求中断（{exc}），{attempt + 1}/{retries} 次重试")
    assert last_error is not None
    raise last_error
