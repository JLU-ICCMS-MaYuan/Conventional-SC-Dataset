import asyncio
import os
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-citation-backfill-test.db")


@pytest.fixture
def citation_backfill_env(tmp_path):
    from backend.database import Base
    from backend.models import Paper, PaperFile

    async def setup():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        pdf_path = Path(tmp_path) / "source.pdf"
        pdf_path.write_bytes(b"%PDF-1.4 test")
        async with session_factory() as session:
            source = Paper(
                id=1,
                title="Source",
                year=2024,
                content_revision=1,
                review_status="approved",
                approved_revision=1,
            )
            pending = Paper(
                id=2,
                title="Pending",
                year=2024,
                content_revision=1,
                review_status="pending",
            )
            source_file = PaperFile(
                paper_id=1,
                paper_revision=1,
                role="main",
                original_filename="source.pdf",
                stored_path=str(pdf_path),
                sha256="a" * 64,
                size=pdf_path.stat().st_size,
                sort_order=0,
            )
            session.add_all([source, pending, source_file])
            await session.commit()
        return engine, session_factory, pdf_path

    engine, session_factory, pdf_path = asyncio.run(setup())
    try:
        yield session_factory, pdf_path
    finally:
        asyncio.run(engine.dispose())


def test_backfill_replaces_current_revision_references_without_bumping_revision(citation_backfill_env, tmp_path):
    from backend.models import Paper, PaperReference
    from backend.services.citation_backfill import backfill_paper_references

    session_factory, _ = citation_backfill_env

    def fake_extract(_pdf_path):
        return {
            "status": "succeeded",
            "parser_name": "grobid",
            "references": [{"raw_citation": "[1] Original reference", "title": "Target", "year": 2020}],
        }

    async def scenario():
        first = await backfill_paper_references(
            session_factory, 1, data_dir=tmp_path, extractor=fake_extract
        )
        second = await backfill_paper_references(
            session_factory, 1, data_dir=tmp_path, extractor=fake_extract
        )
        assert first.status == "succeeded"
        assert second.status == "succeeded"
        async with session_factory() as session:
            paper = await session.get(Paper, 1)
            reference_count = await session.scalar(select(func.count(PaperReference.id)))
            assert paper.content_revision == 1
            assert reference_count == 1

    asyncio.run(scenario())


def test_backfill_skips_nonapproved_papers_and_persists_parser_outage(citation_backfill_env, tmp_path):
    from backend.models import PaperReference, PaperReferenceExtraction
    from backend.services.citation_backfill import backfill_paper_references

    session_factory, _ = citation_backfill_env

    def unavailable_extract(_pdf_path):
        return {
            "status": "unavailable",
            "parser_name": "grobid",
            "error_message": "GROBID offline",
            "references": [],
        }

    async def scenario():
        skipped = await backfill_paper_references(
            session_factory, 2, data_dir=tmp_path, extractor=unavailable_extract
        )
        failed = await backfill_paper_references(
            session_factory, 1, data_dir=tmp_path, extractor=unavailable_extract
        )
        assert skipped.status == "skipped"
        assert failed.status == "unavailable"
        async with session_factory() as session:
            extraction = await session.get(PaperReferenceExtraction, (1, 1))
            reference_count = await session.scalar(select(func.count(PaperReference.id)))
            assert extraction.status == "unavailable"
            assert reference_count == 0

    asyncio.run(scenario())
