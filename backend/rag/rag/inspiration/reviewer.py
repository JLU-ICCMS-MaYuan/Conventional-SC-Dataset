"""Inspiration Agent 双角色自省。

生成者（EvidenceBuilder）输出后，审稿人（DualReviewer）审核并提出漏洞。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.prompts import REVIEWER_SYSTEM

logger = logging.getLogger(__name__)

REVIEW_MARKER = "<!--REVIEW"
REVIEW_END = "-->"


def parse_review_verdicts(text: str) -> list[dict]:
    """从文本中提取所有 REVIEW JSON。

    Args:
        text: 包含 <!--REVIEW ... --> marker 的文本

    Returns:
        解析成功的 ReviewVerdict dict 列表
    """
    verdicts: list[dict] = []
    idx = 0
    while True:
        start = text.find(REVIEW_MARKER, idx)
        if start == -1:
            break
        json_start = start + len(REVIEW_MARKER)
        end = text.find(REVIEW_END, json_start)
        if end == -1:
            break
        try:
            verdict = json.loads(text[json_start:end].strip())
            verdicts.append(verdict)
        except json.JSONDecodeError:
            logger.warning("Failed to parse REVIEW JSON")
        idx = end + len(REVIEW_END)
    return verdicts


async def review_stream(
    evidence_text: str,
) -> AsyncIterator[dict[str, Any]]:
    """对生成的证据文本进行双角色自省。

    Args:
        evidence_text: EvidenceBuilder 的完整输出（含 IDEA_CARD marker）

    Yields:
        SSE 事件 dict: token / review_verdict / status
    """
    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    review_prompt = f"""请审核以下研究点子的可行性。对每个点子，找出至少 2 个潜在漏洞。

{evidence_text}

请按格式输出审核意见。"""

    messages: list[dict] = [
        {"role": "system", "content": REVIEWER_SYSTEM},
        {"role": "user", "content": review_prompt},
    ]

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.3,
            max_tokens=1000,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_text += delta.content
                yield {"type": "token", "data": delta.content}
    except Exception as e:
        logger.error(f"Reviewer failed: {e}")
        yield {"type": "token", "data": f"\n\n审核过程出现错误：{e}"}
        return

    # 提取 ReviewVerdict
    verdicts = parse_review_verdicts(full_text)
    for verdict in verdicts:
        yield {"type": "review_verdict", "data": verdict}
