"""统一的 OpenAI 兼容 LLM JSON 调用入口。"""

from __future__ import annotations

import json
from typing import Any

from openai import OpenAI

from backend.rag.config import settings


def _client() -> OpenAI:
    if not settings.completion_api_key:
        raise RuntimeError("LLM API key 未配置")
    return OpenAI(
        api_key=settings.completion_api_key,
        base_url=settings.completion_base_url,
    )


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


def complete_json(system_prompt: str, user_prompt: str) -> dict[str, Any]:
    response = _client().chat.completions.create(
        model=settings.completion_model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.1,
    )
    return _extract_json(response.choices[0].message.content or "")
