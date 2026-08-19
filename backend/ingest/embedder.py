"""
embedder.py — 文本向量化和索引模块。

将文本块转为向量，存入 Chroma。

Embedding 方案：
- 如果配置了 OPENAI_API_KEY，使用 OpenAI text-embedding-3-small
- 如果未配置，抛出明确的错误提示
"""

from __future__ import annotations

from openai import OpenAI

from backend.rag.config import settings
from backend.rag.vectordb import add_chunks


def embed_texts(texts: list[str]) -> list[list[float]]:
    """将文本列表批量向量化。

    Args:
        texts: 文本列表

    Returns:
        向量列表，shape (n_texts, dim)
    """
    if not settings.embedding_key:
        raise RuntimeError(
            "Embedding API key 未配置。请设置 EMBEDDING_API_KEY 或 OPENAI_API_KEY。\n"
            "  在 .env 中添加: EMBEDDING_API_KEY=sk-..."
        )

    client = OpenAI(
        api_key=settings.embedding_key,
        base_url=settings.embedding_url,
    )
    model = settings.embedding_model

    resp = client.embeddings.create(
        model=model,
        input=texts,
    )

    embeddings = [item.embedding for item in resp.data]
    return embeddings


def index_chunks(
    chunk_data: list[dict],
    embeddings: list[list[float]],
) -> list[str]:
    """将 chunks 索引到 Chroma。

    Args:
        chunk_data: [{"id": str, "paper_id": int, "chunk_index": int,
                       "section_name": str, "content": str}, ...]
        embeddings: 对应的向量列表

    Returns:
        成功索引的 chunk id 列表
    """
    ids = add_chunks(chunk_data, embeddings)
    return ids


def embed_and_index_chunks(chunk_data: list[dict]) -> int:
    if not chunk_data:
        return 0
    embeddings = embed_texts([item["content"] for item in chunk_data])
    return len(index_chunks(chunk_data, embeddings))


def chunk_and_embed(markdown_text: str, paper_id: int) -> int:
    """论文全文 → 语义分块 → 向量化 → Chroma。返回索引的 chunk 数。"""
    from backend.ingest.chunker import chunk_paper

    chunks = chunk_paper(markdown_text, paper_id)
    if not chunks:
        print(f"  [RAG] paper_id={paper_id}: 无有效文本块，跳过向量化")
        return 0

    chunk_dicts = [
        {"id": f"paper_{paper_id}_chunk_{c.chunk_index}",
         "paper_id": c.paper_id, "chunk_index": c.chunk_index,
         "section_name": c.section_name or "", "content": c.content}
        for c in chunks
    ]
    texts = [c.content for c in chunks]
    embeddings = embed_texts(texts)
    ids = index_chunks(chunk_dicts, embeddings)
    print(f"  [RAG] paper_id={paper_id}: {len(ids)} chunks 已索引")
    return len(ids)
