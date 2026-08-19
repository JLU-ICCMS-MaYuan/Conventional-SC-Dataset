"""
vector_search.py — 向量语义搜索模块。

将用户问题 embedding 后，到 Qdrant 中搜索语义最相似的 chunks。
"""

from __future__ import annotations

from backend.ingest.embedder import embed_texts
from backend.rag.vectordb import search_chunks as qdrant_search


async def _approved_results(results: list[dict]) -> list[dict]:
    if not results:
        return []
    from sqlalchemy import select
    from backend.models import Paper
    from backend.rag.database import async_session_factory

    paper_ids = {int(item.get("paper_id") or 0) for item in results}
    async with async_session_factory() as session:
        rows = await session.execute(
            select(Paper.id).where(Paper.id.in_(paper_ids), Paper.review_status == "approved")
        )
        approved_ids = set(rows.scalars())
    return [item for item in results if int(item.get("paper_id") or 0) in approved_ids]


async def search_by_semantics(
    query: str,
    top_k: int = 10,
    paper_id: int | None = None,
    collection: str | None = None,
) -> list[dict]:
    """语义搜索。

    Args:
        query: 用户自然语言问题
        top_k: 返回多少条结果
        paper_id: 可限制在某一篇论文内搜索
        collection: Qdrant 集合名，默认 paper_chunks，可传 review_chunks

    Returns:
        [{"id", "paper_id", "chunk_index", "section_name",
          "content", "score"}, ...]
    """
    from backend.rag.vectordb import COLLECTION_NAME, REVIEW_COLLECTION_NAME

    col = collection or COLLECTION_NAME
    # 1. 将用户问题向量化
    query_vec = embed_texts([query])[0]

    # 2. Qdrant 搜索
    where = {"paper_id": str(paper_id)} if paper_id else None
    results = await _approved_results(
        qdrant_search(query_vec, top_k=top_k, where=where, collection=col)
    )

    # 3. Qdrant cosine score 越大越相似，保持原始语义与排序。
    for result in results:
        result["score"] = round(result["score"], 4)

    return results


async def search_by_keywords_in_chunks(
    query: str,
    top_k: int = 20,
) -> list[dict]:
    """先用关键字在 SQLite 的 paper_chunks 里粗筛，再用向量排序。

    这是"混合搜索"的简化版本：先用 SQL LIKE 找到可能相关的 chunks，
    缩小搜索范围，再算向量距离排序。

    Args:
        query: 关键词
        top_k: 返回多少条

    Returns:
        [{"id", "paper_id", "chunk_index", "content", "source"}, ...]
    """
    from sqlalchemy import select
    from backend.rag.database import async_session_factory
    from backend.models import Paper, PaperChunk

    pattern = f"%{query}%"

    async with async_session_factory() as session:
        r = await session.execute(
            select(PaperChunk)
            .join(Paper, Paper.id == PaperChunk.paper_id)
            .where(PaperChunk.content.ilike(pattern))
            .where(Paper.review_status == "approved")
            .limit(top_k * 2)
        )
        chunks = r.scalars().all()

    if not chunks:
        return []

    # 向量化 query 和 chunks，排序
    query_vec = embed_texts([query])[0]
    texts = [c.content for c in chunks]
    chunk_vecs = embed_texts(texts)

    from math import sqrt

    def cosine_sim(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        na = sqrt(sum(x * x for x in a))
        nb = sqrt(sum(y * y for y in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    scored = []
    for i, chunk in enumerate(chunks):
        sim = cosine_sim(query_vec, chunk_vecs[i])
        scored.append({
            "id": str(chunk.id),
            "paper_id": chunk.paper_id,
            "chunk_index": chunk.chunk_index,
            "section_name": chunk.section_name,
            "content": chunk.content,
            "score": sim,
            "source": "keyword_then_vector",
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]
