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
    if not settings.openai_api_key:
        raise RuntimeError(
            "OpenAI API key 未配置。向量化需要设置 OPENAI_API_KEY。\n"
            "  在 .env 中添加: OPENAI_API_KEY=sk-..."
        )

    client = OpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
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
