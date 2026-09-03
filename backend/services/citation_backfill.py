"""Controlled backfill for GROBID references on already-approved papers.

The public upload workflow owns new-paper extraction. This module is deliberately
an operator-only path for historical records, with one GROBID call and one write
transaction per paper so a bad PDF cannot undo other successful backfills.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.models import Paper, PaperFile
from backend.services.citation_graph import (
    extract_references_from_pdf,
    persist_reference_extraction,
)


@dataclass(frozen=True)
class CitationBackfillResult:
    paper_id: int
    paper_revision: int | None
    status: str
    reference_count: int
    message: str | None = None

    @property
    def failed(self) -> bool:
        return self.status in {"failed", "unavailable", "skipped"}


def _is_current_approved(paper: Paper) -> bool:
    return (
        paper.review_status == "approved"
        and paper.approved_revision == paper.content_revision
    )


async def list_current_approved_paper_ids(
    session_factory: async_sessionmaker[AsyncSession],
) -> list[int]:
    """Return historical backfill targets in a deterministic order."""
    async with session_factory() as session:
        result = await session.scalars(
            select(Paper.id)
            .where(
                Paper.review_status == "approved",
                Paper.approved_revision == Paper.content_revision,
            )
            .order_by(Paper.id)
        )
        return list(result)


async def _load_current_main_pdf(
    session: AsyncSession,
    paper_id: int,
    data_dir: Path,
) -> tuple[Paper | None, Path | None, str | None]:
    paper = await session.get(Paper, paper_id)
    if paper is None:
        return None, None, "论文不存在"
    if not _is_current_approved(paper):
        return paper, None, "论文不是当前已审核版本"

    stored_path = await session.scalar(
        select(PaperFile.stored_path).where(
            PaperFile.paper_id == paper.id,
            PaperFile.paper_revision == paper.content_revision,
            PaperFile.role == "main",
        )
    )
    if not stored_path:
        return paper, None, "当前版本没有主文件"

    pdf_path = Path(str(stored_path))
    if not pdf_path.is_absolute():
        pdf_path = data_dir / pdf_path
    if pdf_path.suffix.lower() != ".pdf":
        return paper, None, "当前版本的主文件不是 PDF"
    if not pdf_path.is_file():
        return paper, None, "当前版本的主 PDF 不存在"
    return paper, pdf_path, None


def _failed_extraction(message: str) -> dict[str, Any]:
    return {
        "status": "failed",
        "parser_name": "grobid",
        "parser_version": None,
        "error_message": message,
        "references": [],
    }


async def backfill_paper_references(
    session_factory: async_sessionmaker[AsyncSession],
    paper_id: int,
    *,
    data_dir: Path,
    dry_run: bool = False,
    extractor: Callable[[Path], dict[str, Any]] = extract_references_from_pdf,
) -> CitationBackfillResult:
    """Backfill exactly one paper without changing its revision or review state."""
    async with session_factory() as session:
        paper, pdf_path, skip_reason = await _load_current_main_pdf(session, paper_id, data_dir)
        paper_revision = paper.content_revision if paper is not None else None

    if skip_reason:
        return CitationBackfillResult(paper_id, paper_revision, "skipped", 0, skip_reason)
    assert paper_revision is not None and pdf_path is not None
    if dry_run:
        return CitationBackfillResult(paper_id, paper_revision, "dry_run", 0, str(pdf_path))

    try:
        extraction = await asyncio.to_thread(extractor, pdf_path)
    except Exception as exc:
        extraction = _failed_extraction(f"GROBID 解析异常：{exc}")
    if not isinstance(extraction, dict):
        extraction = _failed_extraction("GROBID 返回的解析结果不是对象")

    references = extraction.get("references")
    reference_count = len(references) if isinstance(references, list) else 0
    status = str(extraction.get("status") or "failed")

    async with session_factory() as session:
        async with session.begin():
            current = await session.get(Paper, paper_id)
            if (
                current is None
                or not _is_current_approved(current)
                or current.content_revision != paper_revision
            ):
                return CitationBackfillResult(
                    paper_id,
                    paper_revision,
                    "skipped",
                    0,
                    "GROBID 解析期间论文版本或审核状态发生变化",
                )
            await persist_reference_extraction(session, current, extraction)

    message = extraction.get("error_message")
    return CitationBackfillResult(
        paper_id,
        paper_revision,
        status,
        reference_count,
        str(message) if message else None,
    )


async def backfill_paper_set(
    session_factory: async_sessionmaker[AsyncSession],
    paper_ids: Iterable[int],
    *,
    data_dir: Path,
    dry_run: bool = False,
    extractor: Callable[[Path], dict[str, Any]] = extract_references_from_pdf,
) -> list[CitationBackfillResult]:
    """Process a stable, de-duplicated paper ID sequence one paper at a time."""
    results: list[CitationBackfillResult] = []
    for paper_id in sorted({int(value) for value in paper_ids}):
        results.append(
            await backfill_paper_references(
                session_factory,
                paper_id,
                data_dir=data_dir,
                dry_run=dry_run,
                extractor=extractor,
            )
        )
    return results
