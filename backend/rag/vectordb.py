"""
向量数据库模块（Chroma 封装）。

Chroma 是一个本地向量数据库：
- 数据存在本地文件系统，不需要单独起服务
- PersistentClient 同步操作，适合摄入管线和搜索场景
- 每个 document 存 chunk 文本 + metadata（paper_id, chunk_index 等）

搜索流程：
  用户问题 → embedding API → 向量 → Chroma query → 返回相关 chunks
"""

from __future__ import annotations

import chromadb

from backend.rag.config import settings as rag_settings
from chromadb.config import Settings

CHROMA_DIR = rag_settings.chroma_path

COLLECTION_NAME = "paper_chunks"

_client: chromadb.PersistentClient | None = None


def _get_client() -> chromadb.PersistentClient:
    """获取 PersistentClient 单例。"""
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(
            path=str(CHROMA_DIR),
            settings=Settings(anonymized_telemetry=False),
        )
    return _client


def _get_collection():
    """获取 collection，不存在则创建。"""
    client = _get_client()
    try:
        return client.get_collection(COLLECTION_NAME)
    except Exception:
        return client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )


def add_chunks(
    chunks: list[dict],
    embeddings: list[list[float]],
) -> list[str]:
    """批量添加 chunks 到 Chroma。

    Args:
        chunks: [{"id": str, "paper_id": int, "chunk_index": int,
                   "section_name": str, "content": str}, ...]
        embeddings: 每个 chunk 对应的向量，shape (n_chunks, dim)

    Returns:
        添加成功的 chunk id 列表
    """
    collection = _get_collection()
    ids = [str(c["id"]) for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [
        {
            "paper_id": str(c["paper_id"]),
            "chunk_index": c["chunk_index"],
            "section_name": c.get("section_name", ""),
        }
        for c in chunks
    ]

    collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    return ids


def search_chunks(
    query_embedding: list[float],
    top_k: int = 10,
    where: dict | None = None,
) -> list[dict]:
    """向量搜索。

    Args:
        query_embedding: 用户问题的向量
        top_k: 返回多少条
        where: 过滤条件，如 {"paper_id": "42"}

    Returns:
        [{"id": str, "paper_id": int, "chunk_index": int,
          "section_name": str, "content": str, "distance": float}, ...]
    """
    collection = _get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )

    out = []
    if not results["ids"]:
        return out

    ids = results["ids"][0]
    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for i in range(len(ids)):
        out.append({
            "id": ids[i],
            "paper_id": int(metadatas[i]["paper_id"]),
            "chunk_index": metadatas[i]["chunk_index"],
            "section_name": metadatas[i].get("section_name", ""),
            "content": documents[i],
            "distance": distances[i] if distances[i] is not None else 0.0,
        })

    return out


def delete_paper_chunks(paper_id: int) -> None:
    """删除某篇论文的所有 chunks。"""
    collection = _get_collection()
    collection.delete(where={"paper_id": str(paper_id)})


def collection_stats() -> dict:
    """返回 collection 统计信息。"""
    collection = _get_collection()
    return {
        "name": collection.name,
        "count": collection.count(),
    }
