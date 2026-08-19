"""RQ jobs for the staged paper upload workflow."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from sqlalchemy import func

from backend.database import SessionLocal
from backend.ingest.chunker import Chunk, chunk_paper
from backend.ingest.extractor import _parse_result
from backend.ingest.pdf_extractor import extract_text_from_pdf
from backend.ingest.upload_tasks import (
    artifact_directory,
    artifact_path,
    data_path,
    get_state,
    markdown_path,
    save_draft,
    update_state,
)
from backend.models import Paper
from backend.rag.llm import complete_json


CHUNK_SYSTEM_PROMPT = """你是超导论文证据提取助手。只根据给出的一个论文分段提取候选事实，返回 JSON。
每个事实都要保留可逐字核对的原文 quote 和最近的 <!-- page: N --> 页码；没有信息时返回空数组或 null，不要猜测。
论文整体类型和材料类型此时只给候选证据，不做最终决定。

返回结构：
{
  "metadata": {"title": null, "doi": null, "authors": [], "journal": null, "year": null, "abstract": null},
  "paper_type_evidence": [{"candidate": "theoretical|experimental|review|unknown", "page": 1, "quote": "原文"}],
  "research_materials": [],
  "referenced_materials": [],
  "material_relations": [{"material": "", "relation": "discovers|investigates|predicts", "page": 1, "quote": ""}],
  "key_properties": [{"material": "", "name": "", "value": null, "unit": null, "condition": {}, "is_primary": false, "article_type": "e|t", "page": 1, "quote": ""}],
  "methodology": [],
  "key_findings": [],
  "sc_type_candidates": [{"value": "", "page": 1, "quote": ""}]
}"""


SUMMARY_SYSTEM_PROMPT = """你是超导材料论文分类与结构化提取专家。汇总整篇论文各分段候选事实，去重并返回 JSON 草稿。

论文整体分类按核心贡献判断：
- 理论提出主要结论、实验只验证理论，归 theoretical。
- 实验发现主要现象、理论用于解释实验，归 experimental。
- 理论和实验同等重要、无法分主次，也归 experimental。
- 以整理评价已有工作为主，归 review。
理论二级类型只允许 calculation、method、theory。新算法、新模型、新研究工具归 method；使用已有计算方法研究具体问题归 calculation；解析推导、理论模型或机制研究归 theory。
材料超导类型必须综合全文判断，可以使用已有类型，也可以提出自由文本新类型，不能只凭化学式猜测。
论文整体 paper_type 与每条物性的 article_type 必须分别判断，article_type 只允许 e 或 t。
每个关键分类和物性保留 section/page/quote 证据；无法确定就返回 unknown 或空值，不要编造。

返回结构：
{
  "paper": {
    "title": "", "doi": null, "authors": [], "journal": null, "volume": null, "pages": null,
    "year": null, "abstract": null, "summary": "", "paper_type": "theoretical|experimental|review|unknown",
    "theoretical_subtype": null, "keywords_tags": [], "methodology": [], "key_finding": "",
    "rationale": "", "research_materials": [], "referenced_materials": [], "material_relations": [], "builds_on": []
  },
  "key_properties": [{
    "material": "", "name": "", "name_raw": "", "value": null, "unit": null,
    "condition": {}, "condition_note": null, "is_primary": false,
    "superconductor_type": "", "article_type": "e|t",
    "evidence": {"section": "", "page": null, "quote": ""}
  }],
  "classification_reason": "",
  "classification_evidence": [{"section": "", "page": null, "quote": ""}],
  "sc_type": "",
  "sc_type_review_status": "none"
}"""


def _original_path(state: dict[str, Any]) -> Path:
    value = state.get("file_path")
    if not value:
        raise RuntimeError("上传文件路径缺失")
    path = Path(str(value))
    if not path.is_file():
        raise RuntimeError("上传文件不存在或已清理")
    return path


def _extract_markdown(state: dict[str, Any], source: Path) -> str:
    if state.get("file_kind") == "pdf":
        text = extract_text_from_pdf(source)
        if len(text.strip()) < 50:
            raise ValueError("PDF 文本提取失败，可能为扫描件，请上传可搜索文本的 PDF")
        return text
    for encoding in ("utf-8", "gbk"):
        try:
            return source.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("无法解码文件内容，请使用 UTF-8 编码")


def _chunks_with_preamble(markdown: str) -> list[Chunk]:
    chunks = chunk_paper(markdown, paper_id=0)
    if not chunks:
        return []
    sample = chunks[0].content[:120]
    offset = markdown.find(sample) if sample else -1
    preamble = markdown[:offset].strip() if offset > 0 else ""
    if len(preamble) >= 10:
        chunks.insert(0, Chunk(0, 0, "论文首页与摘要", None, preamble, max(1, len(preamble) // 4)))
    cursor = 0
    for index, chunk in enumerate(chunks):
        chunk.chunk_index = index
        sample = chunk.content[:120]
        offset = markdown.find(sample, cursor) if sample else -1
        if offset < 0 and sample:
            offset = markdown.find(sample)
        if offset >= 0:
            cursor = offset + len(sample)
            local_marker = re.search(r"<!--\s*page:\s*(\d+)\s*-->", chunk.content)
            if local_marker:
                chunk.source_page = int(local_marker.group(1))
            else:
                markers = list(re.finditer(r"<!--\s*page:\s*(\d+)\s*-->", markdown[:offset]))
                chunk.source_page = int(markers[-1].group(1)) if markers else None
        else:
            chunk.source_page = None
    return chunks


def _chunk_result_path(task_id: str, chunk_index: int) -> Path:
    directory = artifact_directory(task_id) / "chunks"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / f"{chunk_index:05d}.json"


def _read_chunk(task_id: str, chunk: Chunk) -> dict[str, Any]:
    result_path = _chunk_result_path(task_id, chunk.chunk_index)
    if result_path.exists():
        return json.loads(result_path.read_text(encoding="utf-8"))
    prompt = (
        f"章节：{chunk.section_name or '正文'}\n页码：{getattr(chunk, 'source_page', None) or '未知'}\n"
        f"分段编号：{chunk.chunk_index}\n\n{chunk.content}"
    )
    result = complete_json(CHUNK_SYSTEM_PROMPT, prompt)
    result["_source"] = {
        "chunk_index": chunk.chunk_index,
        "section": chunk.section_name or "正文",
        "page": getattr(chunk, "source_page", None),
    }
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def _normalize_text_items(value: Any, *keys: str) -> tuple[list[str], list[dict[str, Any]]]:
    texts: list[str] = []
    evidence: list[dict[str, Any]] = []
    for item in _as_list(value):
        raw = item
        if isinstance(item, dict):
            raw = next((item.get(key) for key in keys if item.get(key) not in (None, "")), "")
            item_evidence = item.get("evidence")
            if isinstance(item_evidence, dict):
                evidence.append(item_evidence)
        text = str(raw or "").strip()
        if text and text not in texts:
            texts.append(text)
    return texts, evidence


def _normalize_authors(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [item.strip() for item in value.split(";") if item.strip()]
    return []


def _flatten_properties(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [dict(item) for item in value if isinstance(item, dict)]
    if not isinstance(value, dict):
        return []
    rows: list[dict[str, Any]] = []
    for material, properties in value.items():
        for item in _as_list(properties):
            if isinstance(item, dict):
                row = dict(item)
                row.setdefault("material", str(material))
                rows.append(row)
    return rows


def _normalize_draft(raw: dict[str, Any]) -> dict[str, Any]:
    parsed = _parse_result(raw)
    raw_paper = raw.get("paper") if isinstance(raw.get("paper"), dict) else raw
    paper_type = str(raw_paper.get("paper_type") or parsed.paper_type or "unknown").strip().lower()
    if paper_type not in {"theoretical", "experimental", "review", "unknown"}:
        paper_type = "unknown"
    subtype = raw_paper.get("theoretical_subtype") if paper_type == "theoretical" else None
    if subtype not in {"calculation", "method", "theory"}:
        subtype = None

    keywords, keywords_evidence = _normalize_text_items(raw_paper.get("keywords_tags"), "keyword", "value", "name")
    methodology, methodology_evidence = _normalize_text_items(raw_paper.get("methodology"), "method", "value", "name")
    research_materials, research_evidence = _normalize_text_items(
        raw_paper.get("research_materials"), "material", "value", "name",
    )
    referenced_materials, referenced_evidence = _normalize_text_items(
        raw_paper.get("referenced_materials"), "material", "value", "name",
    )

    paper = {
        "title": raw_paper.get("title") or parsed.paper.get("title") or "",
        "doi": raw_paper.get("doi") or parsed.paper.get("doi"),
        "authors": _normalize_authors(raw_paper.get("authors") or parsed.paper.get("authors")),
        "journal": raw_paper.get("journal") or parsed.paper.get("journal"),
        "volume": raw_paper.get("volume"),
        "pages": raw_paper.get("pages"),
        "year": raw_paper.get("year") or parsed.paper.get("year"),
        "abstract": raw_paper.get("abstract") or parsed.paper.get("abstract"),
        "summary": raw_paper.get("summary") or parsed.summary or "",
        "paper_type": paper_type,
        "theoretical_subtype": subtype,
        "keywords_tags": keywords or _normalize_text_items(parsed.keywords_tags, "keyword", "value", "name")[0],
        "methodology": methodology,
        "key_finding": raw_paper.get("key_finding") or "",
        "rationale": raw_paper.get("rationale") or raw.get("classification_reason") or "",
        "research_materials": research_materials,
        "referenced_materials": referenced_materials,
        "material_relations": _as_list(raw_paper.get("material_relations")),
        "builds_on": _as_list(raw_paper.get("builds_on")),
    }
    properties = _flatten_properties(raw.get("key_properties"))
    for item in properties:
        item.setdefault("name_raw", item.get("name") or "")
        if item.get("value_raw") in (None, "") and item.get("value") not in (None, ""):
            item["value_raw"] = str(item["value"])
        item.setdefault("condition", {})
        item.setdefault("is_primary", False)
        if item.get("article_type") not in {"e", "t"}:
            item["article_type"] = None
        evidence = item.get("evidence")
        item["evidence"] = evidence if isinstance(evidence, dict) else {
            "section": "",
            "page": None,
            "quote": str(item.pop("quote", "") or ""),
        }
    existing_field_evidence = raw.get("field_evidence")
    field_evidence = dict(existing_field_evidence) if isinstance(existing_field_evidence, dict) else {}
    for field, values in {
        "keywords_tags": keywords_evidence,
        "methodology": methodology_evidence,
        "research_materials": research_evidence,
        "referenced_materials": referenced_evidence,
    }.items():
        if values:
            field_evidence[field] = values

    return {
        "paper": paper,
        "key_properties": properties,
        "classification_reason": raw.get("classification_reason") or paper["rationale"],
        "classification_evidence": _as_list(raw.get("classification_evidence")),
        "sc_type": raw.get("sc_type") or "",
        "sc_type_review_status": raw.get("sc_type_review_status") or "none",
        "field_evidence": field_evidence,
    }


def empty_draft() -> dict[str, Any]:
    return _normalize_draft({"paper": {"paper_type": "unknown"}, "key_properties": []})


def normalize_doi(value: Any) -> str | None:
    doi = str(value or "").strip()
    if not doi:
        return None
    lowered = doi.lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if lowered.startswith(prefix):
            doi = doi[len(prefix):].strip()
            break
    return doi or None


def _find_existing_paper(doi: str | None) -> Paper | None:
    normalized = normalize_doi(doi)
    if not normalized:
        return None
    db = SessionLocal()
    try:
        candidates = db.query(Paper).filter(func.lower(Paper.doi).contains(normalized.lower())).all()
        return next(
            (paper for paper in candidates if (normalize_doi(paper.doi) or "").lower() == normalized.lower()),
            None,
        )
    finally:
        db.close()


def _find_existing_by_hash(state: dict[str, Any]) -> Paper | None:
    expected = str(state.get("file_sha256") or "")
    if not expected:
        return None
    db = SessionLocal()
    try:
        papers = db.query(Paper).filter(Paper.source_file_path.isnot(None)).all()
        for paper in papers:
            path = _resolve_stored_file(paper.source_file_path)
            if path and path.is_file() and sha256_file(path) == expected:
                return paper
        return None
    finally:
        db.close()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_stored_file(source_file_path: str | None) -> Path | None:
    if not source_file_path:
        return None
    path = Path(source_file_path)
    return path if path.is_absolute() else data_path("") / path


def _handle_duplicate(task_id: str, state: dict[str, Any], existing: Paper) -> dict[str, Any]:
    source = _original_path(state)
    existing_path = _resolve_stored_file(existing.source_file_path)
    same_file = bool(existing_path and existing_path.is_file() and sha256_file(source) == sha256_file(existing_path))
    shutil.rmtree(artifact_directory(task_id), ignore_errors=True)
    markdown_path(task_id).unlink(missing_ok=True)

    candidate_path: Path | None = None
    if same_file:
        source.unlink(missing_ok=True)
        action = "duplicate_deleted"
    else:
        candidate_dir = data_path("upload_PDFs") / "candidates" / str(existing.id)
        candidate_dir.mkdir(parents=True, exist_ok=True)
        candidate_path = candidate_dir / f"{task_id}{source.suffix.lower()}"
        shutil.move(str(source), str(candidate_path))
        candidate_path.with_suffix(".json").write_text(
            json.dumps(
                {
                    "existing_paper_id": existing.id,
                    "doi": existing.doi,
                    "task_id": task_id,
                    "user_id": state.get("user_id"),
                    "filename": state.get("filename"),
                    "file_sha256": state.get("file_sha256") or sha256_file(candidate_path),
                    "created_at": state.get("created_at"),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        action = "candidate_saved"

    return update_state(
        task_id,
        stage="ready",
        stage_index=5,
        processing_status="succeeded",
        processing_error=None,
        duplicate=True,
        existing_paper_id=existing.id,
        duplicate_file_action=action,
        candidate_attachment=str(candidate_path) if candidate_path else None,
    )


def process_upload_task(task_id: str) -> dict[str, Any]:
    """Extract, read every chunk, and build an editable draft."""
    state = get_state(task_id)
    if not state:
        raise RuntimeError("上传任务不存在或已过期")
    try:
        source = _original_path(state)
        existing_by_hash = _find_existing_by_hash(state)
        if existing_by_hash:
            return _handle_duplicate(task_id, state, existing_by_hash)
        md_path = markdown_path(task_id)
        update_state(
            task_id, stage="extracting", stage_index=2, processing_status="processing",
            processing_error=None, error_code=None,
        )
        if md_path.exists():
            markdown = md_path.read_text(encoding="utf-8")
        else:
            markdown = _extract_markdown(state, source)
            md_path.write_text(markdown, encoding="utf-8")

        chunks = _chunks_with_preamble(markdown)
        if not chunks:
            raise ValueError("论文正文为空，无法生成可校对草稿")
        update_state(
            task_id, stage="reading", stage_index=3, completed_chunks=0, total_chunks=len(chunks),
        )
        candidates: list[dict[str, Any]] = []
        for completed, chunk in enumerate(chunks, start=1):
            candidates.append(_read_chunk(task_id, chunk))
            update_state(task_id, completed_chunks=completed, total_chunks=len(chunks))

        update_state(task_id, stage="summarizing", stage_index=4)
        raw_draft = complete_json(SUMMARY_SYSTEM_PROMPT, json.dumps(candidates, ensure_ascii=False))
        draft = _normalize_draft(raw_draft)
        current_state = get_state(task_id) or state
        existing = _find_existing_paper(draft["paper"].get("doi")) or _find_existing_by_hash(current_state)
        if existing:
            return _handle_duplicate(task_id, current_state, existing)

        ai_values = json.loads(json.dumps(draft, ensure_ascii=False))
        draft["ai_original"] = ai_values
        artifact_path(task_id).write_text(
            json.dumps(
                {
                    "task_id": task_id,
                    "paper_id": None,
                    "ai_values": ai_values,
                    "user_values": None,
                    "evidence": {
                        "classification": draft.get("classification_evidence", []),
                        "key_properties": [item.get("evidence") for item in draft["key_properties"]],
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        save_draft(task_id, draft)
        return update_state(
            task_id, stage="ready", stage_index=5, processing_status="succeeded",
            processing_error=None, completed_chunks=len(chunks), total_chunks=len(chunks), duplicate=False,
        )
    except Exception as exc:
        current = get_state(task_id) or state
        update_state(
            task_id, processing_status="failed", processing_error=str(exc),
            error_code="paper_processing_failed", failed_stage=current.get("stage"),
        )
        raise
