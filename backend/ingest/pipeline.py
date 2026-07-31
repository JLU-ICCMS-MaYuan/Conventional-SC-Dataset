"""
论文入库完整管线（v2 管道化）
PDF → 文本提取 → LLM 提取论文元信息 → 存入 papers 表
                                    → enrich_single 单篇富化
                                    → ingest_paper 增量写入 key_properties
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine

from backend.database import DATABASE_URL
from backend.rag.database import async_session_factory
from backend.ingest.extractor import extract_from_markdown
from backend.ingest.pdf_extractor import extract_text_from_pdf
from backend.ingest.store_papers import store_extraction, ingest_paper


async def _enrich_and_ingest(paper_id: int) -> None:
    """对单篇论文跑 KG 富化 → key_properties 增量写入"""
    from backend.ingest.enrich_papers import enrich_single

    # 单篇富化
    jf = await asyncio.to_thread(enrich_single, paper_id)
    if jf and jf.exists():
        data = json.loads(jf.read_text())
        engine = create_engine(DATABASE_URL)
        n = await asyncio.to_thread(ingest_paper, paper_id, data, engine)
        print(f"  [管线] paper_id={paper_id} → key_properties {n} 条")
    else:
        print(f"  [管线] paper_id={paper_id} 富化失败，跳过 key_properties 写入")


async def ingest_pdf(file_path: Path, original_filename: str) -> dict[str, Any]:
    """完整管线：PDF → papers → KG 富化 → key_properties"""
    text = extract_text_from_pdf(file_path)
    if len(text) < 50:
        raise ValueError("PDF 文本提取失败，可能为扫描件")

    result = extract_from_markdown(text)

    async with async_session_factory() as session:
        paper_id = await store_extraction(result, f"upload/{original_filename}", session)

    if paper_id:
        from backend.ingest.embedder import chunk_and_embed
        await asyncio.gather(
            asyncio.to_thread(chunk_and_embed, text, paper_id),
            _enrich_and_ingest(paper_id),
        )

    return {
        "status": "ok",
        "paper_id": paper_id,
        "title": result.paper.get("title"),
    }
