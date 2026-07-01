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
    deep_context: str = "",
    idea_count: int = 0,
) -> AsyncIterator[dict[str, Any]]:
    """对生成的证据文本进行双角色自省。

    Args:
        evidence_text: EvidenceBuilder 的输出（clean text，marker 已被剥离）
        deep_context: 点子引用的论文原文（可选，帮助审稿人深入了解）
        idea_count: IDEA_CARD 数量（由调用方传入，因 evidence_text 已无 marker）
    """
    import sys as _sys, time as _time
    _t0 = _time.time()

    if not idea_count:
        idea_count = evidence_text.count("<!--IDEA_CARD")
    _sys.stderr.write(f"  [Reviewer] 审核 {idea_count} 个点子, deep={len(deep_context)}字\n")
    _sys.stderr.flush()
    if idea_count == 0:
        _sys.stderr.write(f"  [Reviewer] ⚠️ 跳过（无 IDEA_CARD）\n")
        _sys.stderr.flush()
        return

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    review_prompt = f"""请审核以下研究点子的可行性。对每个点子，找出至少 2 个潜在漏洞。

{evidence_text}
{deep_context}

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
        _sys.stderr.write(f"  [Reviewer] {_time.time() - _t0:.1f}s {len(full_text)}字\n")
        _sys.stderr.flush()
    except Exception as e:
        _sys.stderr.write(f"  [Reviewer] 失败 {e}\n")
        _sys.stderr.flush()
        yield {"type": "token", "data": f"\n\n审核过程出现错误：{e}"}
        return

    verdicts = parse_review_verdicts(full_text)
    for i, v in enumerate(verdicts):
        _sys.stderr.write(f"  [Reviewer] Review #{i+1}: score={v.get('feasibility_score','?')} "
                          f"flaws={len(v.get('flaws',[]))}\n")
        _sys.stderr.flush()

    for verdict in verdicts:
        yield {"type": "review_verdict", "data": verdict}
