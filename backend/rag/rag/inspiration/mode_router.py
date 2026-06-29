"""Inspiration Agent 模式路由器。

用一次 LLM 调用判断用户问题适合哪种思考模式，同时生成针对性搜索查询。
"""

from __future__ import annotations

import json
import logging

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.session import ModeResult
from backend.rag.rag.inspiration.prompts import MODE_ROUTER_SYSTEM

logger = logging.getLogger(__name__)


def parse_mode_result(llm_response: str) -> ModeResult:
    """解析 LLM 返回的 JSON，安全降级。

    Args:
        llm_response: LLM 返回的文本（应包含一个 JSON 对象）

    Returns:
        ModeResult，解析失败时返回默认值 gap_detector
    """
    try:
        data = json.loads(llm_response)
        return ModeResult(
            primary_mode=data.get("primary_mode", "gap_detector"),
            secondary_modes=data.get("secondary_modes", []),
            confidence=float(data.get("confidence", 0.0)),
            search_queries=data.get("search_queries", []),
            rationale=data.get("rationale", "解析失败"),
        )
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"ModeResult parse failed: {e}")
        return ModeResult(
            primary_mode="gap_detector",
            confidence=0.0,
            search_queries=[],
            rationale=f"解析失败，默认使用缺口探测模式。原始响应: {llm_response[:200]}",
        )


async def route_mode(
    question: str,
    history: list[dict] | None = None,
) -> ModeResult:
    """LLM 判断用户问题最适合哪种思考模式。

    Args:
        question: 用户问题
        history: 对话历史

    Returns:
        ModeResult 包含模式选择和搜索查询
    """
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    # 构建消息
    messages: list[dict] = [
        {"role": "system", "content": MODE_ROUTER_SYSTEM},
    ]
    if history:
        messages.extend(history[-4:])  # 最近 4 轮
    messages.append({"role": "user", "content": f"用户问题: {question}"})

    try:
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )
        content = resp.choices[0].message.content or ""
        return parse_mode_result(content)
    except Exception as e:
        logger.error(f"ModeRouter LLM call failed: {e}")
        return ModeResult(
            primary_mode="gap_detector",
            confidence=0.0,
            search_queries=[question],
            rationale=f"LLM 调用失败，默认使用缺口探测模式",
        )
