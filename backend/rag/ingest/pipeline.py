"""PDF upload ingestion entry point for the SC-Wiki RAG service."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from backend.rag.database import async_session_factory
from backend.rag.ingest.cross_check import verify_extraction
from backend.rag.ingest.extractor import extract_from_markdown
from backend.rag.ingest.merger import merge
from backend.rag.ingest.pdf_extractor import extract_text_from_pdf
from backend.rag.ingest.storer import store_extraction


async def ingest_pdf(file_path: Path, original_filename: str) -> dict[str, Any]:
    """Extract superconducting data from an uploaded PDF and store it in RAG SQLite."""
    text = extract_text_from_pdf(file_path)
    if len(text) < 50:
        raise ValueError("PDF 文本提取失败，可能为扫描件")

    first = extract_from_markdown(text)
    cross = verify_extraction(text, first.raw_json or {})
    merged = merge(first, cross)

    async with async_session_factory() as session:
        paper_id = await store_extraction(session, merged, f"upload/{original_filename}")

    return {
        "status": "ok",
        "paper_id": paper_id,
        "title": merged.paper.get("title"),
        "data_points": len(merged.data_points),
    }
