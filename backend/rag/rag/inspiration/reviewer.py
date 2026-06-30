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
    """对生成的证据文本进行双角色自省。"""
    import sys as _sys, time as _time
    _t0 = _time.time()

    # 先看有没有 IDEA_CARD
    idea_count = evidence_text.count("<!--IDEA_CARD")
    _sys.stderr.write(f"[Reviewer] 开始审核 | evidence_len={len(evidence_text)} "
                      f"idea_cards_found={idea_count}\n")
    _sys.stderr.flush()

    if idea_count == 0:
        _sys.stderr.write(f"[Reviewer] ⚠️ 证据文本中没有 IDEA_CARD，跳过审核\n")
        _sys.stderr.flush()
        return

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
        _sys.stderr.write(f"[Reviewer] 审核完成 | {_time.time() - _t0:.1f}s "
                          f"text_len={len(full_text)}\n")
        _sys.stderr.flush()
    except Exception as e:
        _sys.stderr.write(f"[Reviewer] 失败! {e}\n")
        _sys.stderr.flush()
        logger.error(f"Reviewer failed: {e}")
        yield {"type": "token", "data": f"\n\n审核过程出现错误：{e}"}
        return

    verdicts = parse_review_verdicts(full_text)
    if verdicts:
        for i, v in enumerate(verdicts):
            _sys.stderr.write(f"[Reviewer] REVIEW #{i+1}: score={v.get('feasibility_score','?')} "
                              f"flaws={len(v.get('flaws',[]))} "
                              f"dims={v.get('dimensions',{})}\n")
            _sys.stderr.flush()
    else:
        _sys.stderr.write(f"[Reviewer] ⚠️ 未找到 REVIEW marker!\n")
        _sys.stderr.flush()

    for verdict in verdicts:
        yield {"type": "review_verdict", "data": verdict}
