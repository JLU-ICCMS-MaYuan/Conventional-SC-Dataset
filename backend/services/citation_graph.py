"""Citation extraction, conservative matching, and lifecycle reconciliation.

GROBID is the sole automatic source for bibliography records.  This module never
uses an LLM or fuzzy similarity to create a citation edge: a missing match can
be retried later, while an incorrect match would fabricate scientific history.
"""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import re
import unicodedata
from typing import Any
from xml.etree import ElementTree

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Paper, PaperReference, PaperReferenceExtraction


GROBID_DEFAULT_URL = "http://grobid:8070"
GROBID_NAMESPACE = {"tei": "http://www.tei-c.org/ns/1.0"}
GROBID_TIMEOUT_SECONDS = 90.0
EXTRACTION_STATUSES = {"succeeded", "partial", "failed", "unavailable"}


def normalize_doi(value: object) -> str | None:
    """Return a stable DOI form without resolver prefixes or trailing punctuation."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    normalized = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", normalized)
    normalized = re.sub(r"^doi\s*:\s*", "", normalized)
    normalized = normalized.strip(" \t\r\n.,;:)]}>\"")
    return normalized or None


def normalize_title(value: object) -> str | None:
    """Normalize only superficial title formatting; this is not fuzzy matching."""
    if not isinstance(value, str):
        return None
    normalized = unicodedata.normalize("NFKC", value).casefold()
    normalized = re.sub(r"[^\w]+", " ", normalized, flags=re.UNICODE)
    normalized = " ".join(normalized.split())
    return normalized[:512] or None


def _text(element: ElementTree.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(part.strip() for part in element.itertext() if part and part.strip())


def _first_text(element: ElementTree.Element, paths: list[str]) -> str | None:
    for path in paths:
        candidate = _text(element.find(path, GROBID_NAMESPACE))
        if candidate:
            return candidate
    return None


def _author_name(author: ElementTree.Element) -> str | None:
    person = author.find(".//tei:persName", GROBID_NAMESPACE)
    source = person if person is not None else author
    forenames = [_text(item) for item in source.findall(".//tei:forename", GROBID_NAMESPACE)]
    surname = _text(source.find(".//tei:surname", GROBID_NAMESPACE))
    parts = [*filter(None, forenames), surname]
    value = " ".join(parts).strip()
    return value or None


def _extract_year(bibl: ElementTree.Element) -> int | None:
    for date in bibl.findall(".//tei:date", GROBID_NAMESPACE):
        candidate = (date.get("when") or _text(date)).strip()
        match = re.search(r"(?:18|19|20)\d{2}", candidate)
        if match:
            return int(match.group(0))
    return None


def parse_grobid_tei(tei: str | bytes) -> list[dict[str, Any]]:
    """Parse bibliography entries emitted by GROBID's processFulltextDocument."""
    root = ElementTree.fromstring(tei)
    entries = root.findall(".//tei:listBibl/tei:biblStruct", GROBID_NAMESPACE)
    if not entries:
        entries = root.findall(".//tei:biblStruct", GROBID_NAMESPACE)

    references: list[dict[str, Any]] = []
    for reference_index, bibl in enumerate(entries):
        doi = _first_text(bibl, [
            ".//tei:idno[@type='DOI']",
            ".//tei:idno[@type='doi']",
        ])
        title = _first_text(bibl, [
            ".//tei:analytic/tei:title",
            ".//tei:monogr/tei:title",
            ".//tei:title",
        ])
        authors = [
            author_name
            for author in bibl.findall(".//tei:analytic/tei:author", GROBID_NAMESPACE)
            if (author_name := _author_name(author))
        ]
        if not authors:
            authors = [
                author_name
                for author in bibl.findall(".//tei:monogr/tei:author", GROBID_NAMESPACE)
                if (author_name := _author_name(author))
            ]
        raw_citation = _first_text(bibl, [".//tei:note[@type='raw_reference']"]) or _text(bibl)
        references.append({
            "reference_index": reference_index,
            "raw_citation": raw_citation or "[GROBID 未返回原始引文]",
            "doi": normalize_doi(doi),
            "title": title,
            "normalized_title": normalize_title(title),
            "authors": authors or None,
            "year": _extract_year(bibl),
        })
    return references


def extract_references_from_pdf(
    pdf_path: Path,
    *,
    grobid_url: str | None = None,
    client: httpx.Client | None = None,
) -> dict[str, Any]:
    """Call local GROBID and always return a serializable extraction status.

    A parser outage or malformed TEI is deliberately data, not an upload failure.
    """
    target = f"{(grobid_url or os.getenv('GROBID_URL') or GROBID_DEFAULT_URL).rstrip('/')}/api/processFulltextDocument"
    try:
        with pdf_path.open("rb") as source:
            request_client = client or httpx.Client(
                timeout=httpx.Timeout(GROBID_TIMEOUT_SECONDS, connect=10.0),
            )
            try:
                response = request_client.post(
                    target,
                    params={"consolidateCitations": "0"},
                    files={"input": (pdf_path.name, source, "application/pdf")},
                )
            finally:
                if client is None:
                    request_client.close()
    except (OSError, httpx.RequestError) as exc:
        return {
            "status": "unavailable",
            "parser_name": "grobid",
            "parser_version": None,
            "error_message": str(exc),
            "references": [],
        }

    if response.status_code >= 500:
        return {
            "status": "unavailable",
            "parser_name": "grobid",
            "parser_version": None,
            "error_message": f"GROBID HTTP {response.status_code}",
            "references": [],
        }
    if response.status_code >= 400:
        return {
            "status": "failed",
            "parser_name": "grobid",
            "parser_version": None,
            "error_message": f"GROBID HTTP {response.status_code}",
            "references": [],
        }

    try:
        references = parse_grobid_tei(response.content)
    except ElementTree.ParseError as exc:
        return {
            "status": "failed",
            "parser_name": "grobid",
            "parser_version": None,
            "error_message": f"GROBID TEI 无法解析：{exc}",
            "references": [],
        }
    incomplete = any(not item["doi"] and not item["normalized_title"] for item in references)
    return {
        "status": "partial" if incomplete else "succeeded",
        "parser_name": "grobid",
        "parser_version": response.headers.get("X-GROBID-Version"),
        "error_message": None,
        "references": references,
    }


def _normalized_extraction(extraction: object) -> dict[str, Any]:
    raw = extraction if isinstance(extraction, dict) else {}
    status = raw.get("status")
    if status not in EXTRACTION_STATUSES:
        status = "failed"
    references = raw.get("references")
    return {
        "status": status,
        "parser_name": str(raw.get("parser_name") or "grobid")[:32],
        "parser_version": (str(raw["parser_version"])[:64] if raw.get("parser_version") else None),
        "error_message": (str(raw["error_message"]) if raw.get("error_message") else None),
        "references": references if isinstance(references, list) else [],
    }


async def _match_reference(session: AsyncSession, reference: PaperReference) -> None:
    """Match one reference by DOI, then unique title with non-conflicting year."""
    candidates: list[Paper] = []
    method: str | None = None
    doi = normalize_doi(reference.doi)
    if doi:
        result = await session.execute(
            select(Paper).where(
                Paper.doi.is_not(None),
                Paper.review_status == "approved",
                Paper.approved_revision == Paper.content_revision,
            )
        )
        candidates = [
            paper for paper in result.scalars()
            if normalize_doi(paper.doi) == doi
        ]
        method = "doi"
    elif reference.normalized_title:
        result = await session.execute(
            select(Paper).where(
                Paper.title.is_not(None),
                Paper.review_status == "approved",
                Paper.approved_revision == Paper.content_revision,
            )
        )
        candidates = [
            paper for paper in result.scalars()
            if normalize_title(paper.title) == reference.normalized_title
            and (reference.year is None or paper.year is None or reference.year == paper.year)
        ]
        method = "title_year"

    reference.match_checked_at = datetime.now(timezone.utc)
    if len(candidates) == 1:
        reference.cited_paper_id = candidates[0].id
        reference.match_status = "matched"
        reference.match_method = method
    else:
        reference.cited_paper_id = None
        reference.match_status = "ambiguous" if len(candidates) > 1 else "unmatched"
        reference.match_method = None


async def match_references_for_paper(session: AsyncSession, paper: Paper) -> None:
    """Re-evaluate all current-version outbound references for one paper."""
    result = await session.execute(
        select(PaperReference).where(
            PaperReference.paper_id == paper.id,
            PaperReference.paper_revision == paper.content_revision,
        )
    )
    for reference in result.scalars():
        await _match_reference(session, reference)


async def persist_reference_extraction(
    session: AsyncSession,
    paper: Paper,
    extraction: object,
) -> None:
    """Replace the current paper-version bibliography with one parsed GROBID result."""
    data = _normalized_extraction(extraction)
    await session.execute(
        delete(PaperReference).where(
            PaperReference.paper_id == paper.id,
            PaperReference.paper_revision == paper.content_revision,
        )
    )
    existing = await session.get(
        PaperReferenceExtraction,
        (paper.id, paper.content_revision),
    )
    if existing is None:
        existing = PaperReferenceExtraction(
            paper_id=paper.id,
            paper_revision=paper.content_revision,
            status=data["status"],
            parser_name=data["parser_name"],
            parser_version=data["parser_version"],
            error_message=data["error_message"],
            processed_at=datetime.now(timezone.utc),
        )
        session.add(existing)
    else:
        existing.status = data["status"]
        existing.parser_name = data["parser_name"]
        existing.parser_version = data["parser_version"]
        existing.error_message = data["error_message"]
        existing.processed_at = datetime.now(timezone.utc)

    for index, raw_reference in enumerate(data["references"]):
        if not isinstance(raw_reference, dict):
            continue
        raw_citation = str(raw_reference.get("raw_citation") or "").strip()
        if not raw_citation:
            continue
        reference = PaperReference(
            paper_id=paper.id,
            paper_revision=paper.content_revision,
            reference_index=int(raw_reference.get("reference_index", index)),
            raw_citation=raw_citation,
            doi=normalize_doi(raw_reference.get("doi")),
            title=(str(raw_reference["title"]).strip() if raw_reference.get("title") else None),
            normalized_title=normalize_title(raw_reference.get("title") or raw_reference.get("normalized_title")),
            authors=raw_reference.get("authors") if isinstance(raw_reference.get("authors"), list) else None,
            year=(int(raw_reference["year"]) if isinstance(raw_reference.get("year"), int) else None),
            match_status="unmatched",
        )
        session.add(reference)
    await session.flush()
    await match_references_for_paper(session, paper)


async def reconcile_after_paper_approval(session: AsyncSession, paper_id: int) -> None:
    """Retry new paper's own references and all historic unmatched references."""
    paper = await session.get(Paper, paper_id)
    if paper is None or paper.review_status != "approved" or paper.approved_revision != paper.content_revision:
        return
    await match_references_for_paper(session, paper)
    result = await session.execute(
        select(PaperReference).where(PaperReference.match_status.in_(("unmatched", "ambiguous")))
    )
    for reference in result.scalars():
        await _match_reference(session, reference)
