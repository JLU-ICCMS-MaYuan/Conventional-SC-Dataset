"""
向量数据库模块（Qdrant 封装）。

通过 Qdrant gRPC/HTTP API 提供高并发向量搜索能力：
- 默认连接本地 Qdrant 服务 (http://127.0.0.1:6333)
- 每个集合对应一个 Qdrant collection
- 搜索返回 Qdrant cosine score，越大越相似

搜索流程：
  用户问题 → embedding API → 向量 → Qdrant search → 返回相关文档
"""

from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from backend.rag.config import settings as rag_settings

# ── 默认集合名 ───────────────────────────────────────────────────────────
COLLECTION_NAME = "paper_chunks"
REVIEW_COLLECTION_NAME = "review_chunks"

# ── Qdrant 客户端（全局单例，线程安全）───────────────────────────────────

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    """获取 Qdrant 客户端单例。

    QdrantClient 内置连接池，线程安全，无需每个线程独立实例。
    """
    global _client
    if _client is None:
        _client = QdrantClient(
            host=rag_settings.qdrant_host,
            port=rag_settings.qdrant_port,
        )
    return _client


def _ensure_collection(name: str, dim: int = 1536) -> None:
    """确保集合存在，不存在则创建。"""
    client = _get_client()
    try:
        client.get_collection(name)
    except Exception:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


# ── 公共 API（与旧 ChromaDB 接口兼容）───────────────────────────────────

def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
    collection: str = COLLECTION_NAME,
) -> list[str]:
    """批量添加文档块到 Qdrant。

    Args:
        chunks: [{"id": str, "paper_id": int, "chunk_index": int,
                   "section_name": str, "content": str}, ...]
        embeddings: 每个 chunk 对应的向量，shape (n_chunks, dim)
        collection: 目标集合名，默认 paper_chunks

    Returns:
        添加成功的 chunk id 列表
    """
    dim = len(embeddings[0]) if embeddings else 1536
    _ensure_collection(collection, dim)

    points = []
    ids_out = []
    for i, c in enumerate(chunks):
        cid = str(c["id"])
        payload = {
            "document": c["content"],
            "paper_id": str(c["paper_id"]),
            "chunk_index": c["chunk_index"],
            "section_name": c.get("section_name", ""),
        }
        point_id = int(cid) if cid.isdigit() else abs(hash(cid)) % (10 ** 15)
        points.append(PointStruct(id=point_id, vector=embeddings[i], payload=payload))
        ids_out.append(cid)

    _get_client().upsert(collection_name=collection, points=points)
    return ids_out


def search_chunks(
    query_embedding: list[float],
    top_k: int = 10,
    where: dict | None = None,
    collection: str = COLLECTION_NAME,
) -> list[dict]:
    """向量搜索。

    Args:
        query_embedding: 用户问题的向量
        top_k: 返回多少条
        where: 过滤条件，如 {"paper_id": "42"}
        collection: 搜索的集合名

    Returns:
        [{"id": str, "paper_id": int, "chunk_index": int,
          "section_name": str, "content": str, "score": float}, ...]
    """
    client = _get_client()

    # 构建 Qdrant 过滤条件
    query_filter = None
    if where:
        from qdrant_client.models import Filter, FieldCondition, MatchValue
        conditions = []
        for key, value in where.items():
            conditions.append(
                FieldCondition(key=key, match=MatchValue(value=str(value)))
            )
        if conditions:
            query_filter = Filter(must=conditions)

    results = client.query_points(
        collection_name=collection,
        query=query_embedding,
        limit=top_k,
        query_filter=query_filter,
        with_payload=True,
    ).points

    out = []
    for r in results:
        payload = r.payload or {}
        out.append({
            "id": str(r.id),
            "paper_id": int(payload.get("paper_id", 0)),
            "chunk_index": payload.get("chunk_index", 0),
            "section_name": payload.get("section_name", ""),
            "content": payload.get("document", ""),
            "score": r.score if r.score is not None else 0.0,
        })

    return out


def delete_paper_chunks(paper_id: int, collection: str = COLLECTION_NAME) -> None:
    """删除某篇论文的所有 chunks。"""
    client = _get_client()
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    client.delete(
        collection_name=collection,
        points_selector=Filter(
            must=[FieldCondition(key="paper_id", match=MatchValue(value=str(paper_id)))]
        ),
    )


def get_chunks(
    where: dict,
    include_embeddings: bool = False,
    collection: str = COLLECTION_NAME,
) -> dict:
    """从集合中获取 chunks（含 payload）。

    Args:
        where: 过滤条件，如 {"paper_id": "42"}
        include_embeddings: 是否返回向量（Qdrant 不支持通过 filter 获取向量）
        collection: 集合名

    Returns:
        {"ids": [...], "documents": [...], "metadatas": [...]}
    """
    client = _get_client()
    from qdrant_client.models import Filter, FieldCondition, MatchValue

    conditions = []
    for key, value in where.items():
        conditions.append(
            FieldCondition(key=key, match=MatchValue(value=str(value)))
        )

    # Scroll 获取所有匹配的点
    records, _ = client.scroll(
        collection_name=collection,
        scroll_filter=Filter(must=conditions) if conditions else None,
        with_payload=True,
        with_vectors=include_embeddings,
        limit=10000,
    )

    ids = []
    documents = []
    metadatas = []
    embeddings = []

    for r in records:
        ids.append(str(r.id))
        payload = r.payload or {}
        documents.append(payload.get("document", ""))
        metadatas.append({
            k: v for k, v in payload.items()
            if k != "document"
        })
        if include_embeddings and r.vector:
            embeddings.append(r.vector)

    result = {"ids": ids, "documents": documents, "metadatas": metadatas}
    if include_embeddings:
        result["embeddings"] = embeddings
    return result


def collection_stats(collection: str = COLLECTION_NAME) -> dict:
    """返回集合统计信息。"""
    client = _get_client()
    try:
        info = client.get_collection(collection)
        return {
            "name": collection,
            "count": info.points_count,
        }
    except Exception:
        return {"name": collection, "count": 0}
