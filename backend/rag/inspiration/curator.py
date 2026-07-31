"""Inspiration Agent 文献筛选层。

在 Retrieval 之后、EvidenceBuilder 之前，让 LLM 筛选最有价值的文献。
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from openai import OpenAI
from sqlalchemy import select

from backend.rag.config import settings
from backend.rag.database import async_session_factory
from backend.rag.models import Paper
from backend.rag.inspiration.prompts import CURATOR_SYSTEM

logger = logging.getLogger(__name__)


async def load_paper_titles(paper_ids: set[int]) -> dict[int, dict]:
    """从 SQLite 批量加载论文标题等信息。"""
    if not paper_ids:
        return {}
    async with async_session_factory() as session:
        r = await session.execute(
            select(Paper.id, Paper.title, Paper.doi, Paper.year)
            .where(Paper.id.in_(list(paper_ids)))
        )
        return {row[0]: {"title": row[1] or "未知标题", "doi": row[2] or "", "year": row[3] or 0}
                for row in r.fetchall()}


async def curate_papers(
    question: str,
    retrieval_result: dict[str, Any],
) -> dict[str, Any]:
    """LLM 筛选检索结果中最值得深入阅读的文献。

    Args:
        question: 用户问题
        retrieval_result: execute_retrieval 的输出 {"chunks": [...], "kg_results": [...]}

    Returns:
        {"keep_paper_ids": [74, 163], "summary": "筛选摘要"}
    """
    import sys as _sys, time as _time
    _t0 = _time.time()

    chunks = retrieval_result.get("chunks", [])
    if not chunks:
        _sys.stderr.write("  [Curator] 无 chunks\n"); _sys.stderr.flush()
        return {"keep_paper_ids": [], "summary": "未检索到相关文献"}

    paper_ids = {c["paper_id"] for c in chunks if c.get("paper_id")}
    titles = await load_paper_titles(paper_ids)
    catalog = []
    for pid in sorted(paper_ids):
        info = titles.get(pid, {"title": "未知", "doi": "", "year": 0})
        preview = next((c["content"][:200] for c in chunks if c.get("paper_id") == pid), "")
        catalog.append(f"[ID:{pid}] {info['title']} ({info['year']})\n  预览: {preview[:150]}...")
    catalog_text = "\n\n".join(catalog)

    client = OpenAI(
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
    )

    prompt = f"""用户问题: {question}

检索到以下 {len(paper_ids)} 篇文献，请筛选最值得阅读的:

{catalog_text}

请输出 JSON。"""

    try:
        resp = client.chat.completions.create(
            model=settings.deepseek_model,
            messages=[
                {"role": "system", "content": CURATOR_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=500,
        )
        content = resp.choices[0].message.content or "{}"
        result = json.loads(content)
        keep_ids = result.get("keep_paper_ids", [])
        summary = result.get("summary", "")

        # 过滤 chunks：只保留被选中的文献
        all_ids = {c["paper_id"] for c in chunks}
        kept = [pid for pid in keep_ids if pid in all_ids]
        filtered_chunks = [c for c in chunks if c.get("paper_id") in kept]

        _sys.stderr.write(f"  [Curator] {_time.time() - _t0:.1f}s {len(chunks)} chunks/{len(paper_ids)} papers → keep {len(kept)} papers ({len(filtered_chunks)} chunks): {summary[:100]}\n")
        _sys.stderr.flush()

        return {
            "keep_paper_ids": kept,
            "summary": summary,
            "chunks": filtered_chunks,
        }
    except Exception as e:
        _sys.stderr.write(f"[Curator] 失败: {e}\n")
        _sys.stderr.flush()
        return {"keep_paper_ids": list(paper_ids), "summary": "筛选失败，保留全部", "chunks": chunks}
