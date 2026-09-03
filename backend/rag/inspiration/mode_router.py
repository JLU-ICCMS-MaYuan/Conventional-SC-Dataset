"""Inspiration Agent 模式路由器。

用一次 LLM 调用判断用户问题适合哪种思考模式，同时生成针对性搜索查询。
"""

from __future__ import annotations

import json
import logging
import sys
import time as _time

from backend.rag.llm_client import get_llm_client
from backend.rag.llm_context import get_llm_config
from backend.rag.inspiration.session import ModeResult
from backend.rag.inspiration.prompts import MODE_ROUTER_SYSTEM

logger = logging.getLogger(__name__)

_SEP = "─" * 50


def _log(msg: str) -> None:
    sys.stderr.write(f"[ModeRouter] {msg}\n")
    sys.stderr.flush()


def parse_mode_result(llm_response: str) -> ModeResult:
    """解析 LLM 返回的 JSON，安全降级。"""
    try:
        data = json.loads(llm_response)
        return ModeResult(
            primary_mode=data.get("primary_mode", "gap_detector"),
            secondary_modes=data.get("secondary_modes", []),
            collections=data.get("collections", []),
            confidence=float(data.get("confidence", 0.0)),
            search_queries=data.get("search_queries", []),
            rationale=data.get("rationale", "解析失败"),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        _log(f"解析失败 {e}")
        return ModeResult(
            primary_mode="gap_detector",
            collections=["paper_chunks"],
            confidence=0.0,
            search_queries=[],
            rationale=f"解析失败，默认使用全文献库。原始响应: {llm_response[:200]}",
        )


async def route_mode(
    question: str,
    history: list[dict] | None = None,
) -> ModeResult:
    """LLM 判断用户问题最适合哪种思考模式。"""
    client = get_llm_client()

    messages: list[dict] = [
        {"role": "system", "content": MODE_ROUTER_SYSTEM},
    ]
    if history:
        messages.extend(history[-4:])
    messages.append({"role": "user", "content": f"用户问题: {question}"})

    t0 = _time.time()
    try:
        resp = client.chat.completions.create(
            model=get_llm_config().model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=500,
        )
        elapsed = _time.time() - t0
        content = resp.choices[0].message.content or ""
        result = parse_mode_result(content)
        _log(f"{elapsed:.1f}s mode={result.primary_mode} "
             f"collections={result.collections} queries={result.search_queries}")
        return result
    except Exception as e:
        _log(f"失败 {e}")
        return ModeResult(
            primary_mode="gap_detector",
            collections=["paper_chunks"],
            confidence=0.0,
            search_queries=[question],
            rationale=f"LLM 调用失败，默认使用全文献库",
        )
