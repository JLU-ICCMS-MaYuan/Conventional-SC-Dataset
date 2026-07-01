"""Inspiration Agent 证据构建层。

生成自然对话 + 嵌入式 IdeaCard marker。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.rag.inspiration.prompts import (
    EVIDENCE_BUILDER_SYSTEM,
    build_explore_prompt,
)

logger = logging.getLogger(__name__)

IDEA_CARD_MARKER = "<!--IDEA_CARD"
IDEA_CARD_END = "-->"


def parse_idea_cards(text: str) -> list[dict]:
    """从文本中提取所有 IDEA_CARD JSON。

    Args:
        text: 包含 <!--IDEA_CARD ... --> marker 的文本

    Returns:
        解析成功的 IdeaCard dict 列表
    """
    cards: list[dict] = []
    idx = 0
    while True:
        start = text.find(IDEA_CARD_MARKER, idx)
        if start == -1:
            break
        json_start = start + len(IDEA_CARD_MARKER)
        end = text.find(IDEA_CARD_END, json_start)
        if end == -1:
            break
        try:
            raw = text[json_start:end].strip()
            card = json.loads(raw)
            cards.append(card)
        except json.JSONDecodeError:
            import sys
            raw = text[json_start:end].strip()[:300]
            sys.stderr.write(f"  [EvidenceBuilder] JSON解析失败: {raw}\n")
            sys.stderr.flush()
            logger.warning("Failed to parse IDEA_CARD JSON")
        idx = end + len(IDEA_CARD_END)
    return cards


async def build_evidence_stream(
    session: InspirationSession,
    mode_result: Any,  # ModeResult
    retrieval_result: dict[str, Any],
) -> AsyncIterator[dict[str, Any]]:
    """流式生成对话 + IdeaCard。

    Args:
        session: 当前会话
        mode_result: ModeRouter 的输出
        retrieval_result: execute_retrieval 的输出

    Yields:
        SSE 事件 dict: token / evidence_card / status
    """
    from backend.rag.rag.inspiration.retrieval import format_rag_context
    from backend.rag.rag.inspiration.session import MODE_LABELS

    rag_context = format_rag_context(retrieval_result)
    mode_label = MODE_LABELS.get(mode_result.primary_mode, mode_result.primary_mode)

    prompt = build_explore_prompt(
        question=session.user_question,
        mode=mode_result.primary_mode,
        mode_label=mode_label,
        rationale=mode_result.rationale,
        rag_context=rag_context,
        history=session.history,
    )

    import sys as _sys, time as _time
    _t0 = _time.time()

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    messages: list[dict] = [
        {"role": "system", "content": EVIDENCE_BUILDER_SYSTEM},
    ]
    if session.history:
        messages.extend(session.history[-6:])
    messages.append({"role": "user", "content": prompt})

    _sys.stderr.write(f"  [EvidenceBuilder] 生成中...\n")
    _sys.stderr.flush()

    full_text = ""
    try:
        stream = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=messages,
            temperature=0.7,
            max_tokens=3500,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                full_text += delta.content
        _sys.stderr.write(f"  [EvidenceBuilder] {_time.time() - _t0:.1f}s {len(full_text)}字\n")
        _sys.stderr.flush()
    except Exception as e:
        _sys.stderr.write(f"  [EvidenceBuilder] 失败 {e}\n")
        _sys.stderr.flush()
        yield {"type": "token", "data": f"\n\n抱歉，生成过程出现错误：{e}"}
        return

    # 提取 IDEA_CARD → 从文本中移除 → 剩余干净文本流式输出
    cards = parse_idea_cards(full_text)
    clean_text = full_text
    if cards:
        for i, card in enumerate(cards):
            _sys.stderr.write(f"  [EvidenceBuilder] Idea #{i+1}: {card.get('title','?')[:60]} "
                              f"({len(card.get('fragments',[]))}引用, {len(card.get('assumptions',[]))}假设)\n")
            _sys.stderr.flush()
            session.add_idea(card)
            yield {"type": "evidence_card", "data": card}
        # 移除所有 IDEA_CARD marker
        import re
        clean_text = re.sub(r'<!--IDEA_CARD[\s\S]*?-->', '', full_text).strip()
        # 也移除 IDEATE 模式里附带的可行性备注行（理论★ 合成★ 测量★）
        clean_text = re.sub(r'\n*可行性：.*$', '', clean_text, flags=re.MULTILINE).strip()
    else:
        _sys.stderr.write(f"  [EvidenceBuilder] ⚠️ 无 IDEA_CARD\n")
        _sys.stderr.flush()

    # 流式输出清理后的文本
    for char in clean_text:
        yield {"type": "token", "data": char}

    session.history.append({"role": "user", "content": session.user_question})
    session.history.append({"role": "assistant", "content": clean_text})
