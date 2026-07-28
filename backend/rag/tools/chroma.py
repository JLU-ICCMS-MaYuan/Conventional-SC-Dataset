"""向量搜索工具 — 论文正文语义检索（Qdrant 后端）。"""

from __future__ import annotations

import asyncio
from typing import Any


def search_chunks(question: str, top_k: int = 10) -> list[dict[str, Any]]:
    """语义搜索论文正文 chunks，返回去重后的结果列表"""
    from backend.rag.search.vector_search import search_by_semantics

    async def _run():
        return await search_by_semantics(question, top_k=top_k)

    result = asyncio.run(_run())  # list[dict] 直接是 chunks 列表

    # 去重按 paper_id
    seen = set()
    items = []
    for c in result[:top_k]:
        pid = c.get("paper_id")
        if pid in seen:
            continue
        seen.add(pid)
        items.append({
            "paper_id": pid,
            "title": c.get("title", "")[:100],
            "snippet": c.get("content", "")[:400],
            "section": c.get("section_name", ""),
        })
    return items
