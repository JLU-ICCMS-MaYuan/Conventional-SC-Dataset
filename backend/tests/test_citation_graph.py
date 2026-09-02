import asyncio
import os
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine


def _tei(*entries: str) -> bytes:
    return (
        '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><back><listBibl>'
        + "".join(entries)
        + "</listBibl></back></text></TEI>"
    ).encode()


def test_grobid_tei_keeps_structured_reference_fields_and_raw_citation(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", "sqlite:////tmp/scwiki-citation-parser-test.db")
    from backend.services.citation_graph import extract_references_from_pdf

    pdf_path = Path(tmp_path) / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4 test")
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            headers={"X-GROBID-Version": "0.8.1"},
            content=_tei(
                """
                <biblStruct>
                  <analytic><title>Example Paper</title>
                    <author><persName><forename>Ada</forename><surname>Lovelace</surname></persName></author>
                  </analytic>
                  <monogr><imprint><date when="2020"/></imprint></monogr>
                  <idno type="DOI">https://doi.org/10.1000/Example.</idno>
                  <note type="raw_reference">[1] Example Paper, Journal 2020.</note>
                </biblStruct>
                """
            ),
            request=request,
        )
    )
    with httpx.Client(transport=transport) as client:
        result = extract_references_from_pdf(pdf_path, grobid_url="http://grobid.test", client=client)

    assert result["status"] == "succeeded"
    assert result["parser_version"] == "0.8.1"
    assert result["references"] == [{
        "reference_index": 0,
        "raw_citation": "[1] Example Paper, Journal 2020.",
        "doi": "10.1000/example",
        "title": "Example Paper",
        "normalized_title": "example paper",
        "authors": ["Ada Lovelace"],
        "year": 2020,
    }]


def test_reference_matching_is_doi_first_and_retries_after_target_approval():
    from backend import models
    from backend.database import Base
    from backend.services.citation_graph import (
        match_references_for_paper,
        persist_reference_extraction,
        reconcile_after_paper_approval,
    )

    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            target = models.Paper(
                id=10,
                title="Title Does Not Matter",
                doi="10.1000/target",
                year=2019,
                content_revision=1,
                review_status="pending",
            )
            source = models.Paper(
                id=11,
                title="Source",
                year=2020,
                content_revision=1,
                review_status="approved",
                approved_revision=1,
            )
            session.add_all([target, source])
            await session.commit()

            await persist_reference_extraction(session, source, {
                "status": "succeeded",
                "references": [
                    {
                        "reference_index": 0,
                        "raw_citation": "DOI reference",
                        "doi": "https://doi.org/10.1000/TARGET",
                        "title": "Different title",
                        "year": 2020,
                    },
                    {
                        "reference_index": 1,
                        "raw_citation": "Unmatched future paper",
                        "title": "Future paper",
                        "year": 2018,
                    },
                    {
                        "reference_index": 2,
                        "raw_citation": "Repeated DOI reference",
                        "doi": "10.1000/target",
                    },
                ],
            })
            await session.commit()

            references = list((await session.scalars(
                select(models.PaperReference).order_by(models.PaperReference.reference_index)
            )).all())
            assert references[0].match_status == "unmatched"
            assert references[1].match_status == "unmatched"
            assert references[2].match_status == "unmatched"

            target.review_status = "approved"
            target.approved_revision = 1
            await session.commit()
            await reconcile_after_paper_approval(session, target.id)
            await session.commit()

            references = list((await session.scalars(
                select(models.PaperReference).order_by(models.PaperReference.reference_index)
            )).all())
            assert references[0].match_status == "matched"
            assert references[0].match_method == "doi"
            assert references[0].cited_paper_id == target.id
            assert references[2].cited_paper_id == target.id
            distinct_sources = await session.scalar(
                select(func.count(func.distinct(models.PaperReference.paper_id))).where(
                    models.PaperReference.cited_paper_id == target.id,
                    models.PaperReference.match_status == "matched",
                )
            )
            assert distinct_sources == 1
        await engine.dispose()

    asyncio.run(scenario())


def test_title_matching_rejects_ambiguous_candidates_and_year_conflicts():
    from backend import models
    from backend.database import Base
    from backend.services.citation_graph import persist_reference_extraction

    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            source = models.Paper(id=20, title="Source", year=2022, content_revision=1, review_status="approved", approved_revision=1)
            candidates = [
                models.Paper(id=21, title="Same Title", year=2020, content_revision=1, review_status="approved", approved_revision=1),
                models.Paper(id=22, title="Same Title", year=2020, content_revision=1, review_status="approved", approved_revision=1),
                models.Paper(id=23, title="Conflict Title", year=2021, content_revision=1, review_status="approved", approved_revision=1),
            ]
            session.add_all([source, *candidates])
            await session.commit()
            await persist_reference_extraction(session, source, {
                "status": "succeeded",
                "references": [
                    {"reference_index": 0, "raw_citation": "ambiguous", "title": "Same Title", "year": 2020},
                    {"reference_index": 1, "raw_citation": "year conflict", "title": "Conflict Title", "year": 2020},
                ],
            })
            await session.commit()
            references = list((await session.scalars(
                select(models.PaperReference).order_by(models.PaperReference.reference_index)
            )).all())
            assert references[0].match_status == "ambiguous"
            assert references[0].cited_paper_id is None
            assert references[1].match_status == "unmatched"
        await engine.dispose()

    asyncio.run(scenario())


def test_revision_reextraction_reads_current_main_pdf(monkeypatch):
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")
    from backend import models
    from backend.api.rag import _reextract_main_pdf_references
    from backend.database import Base
    from backend.services import citation_graph

    async def scenario():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:")
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            paper = models.Paper(
                id=30,
                title="Versioned paper",
                year=2024,
                content_revision=1,
                review_status="approved",
                approved_revision=1,
            )
            paper_file = models.PaperFile(
                paper_id=30,
                paper_revision=1,
                role="main",
                original_filename="paper.pdf",
                stored_path="/tmp/scwiki-versioned-paper.pdf",
                sha256="a" * 64,
                size=1,
                sort_order=0,
            )
            session.add_all([paper, paper_file])
            await session.commit()

            parsed_paths = []

            def fake_extract(pdf_path):
                parsed_paths.append(pdf_path)
                return {"status": "succeeded", "references": []}

            monkeypatch.setattr(citation_graph, "extract_references_from_pdf", fake_extract)
            result = await _reextract_main_pdf_references(session, paper)

            assert result["status"] == "succeeded"
            assert parsed_paths == [Path("/tmp/scwiki-versioned-paper.pdf")]
        await engine.dispose()

    asyncio.run(scenario())
