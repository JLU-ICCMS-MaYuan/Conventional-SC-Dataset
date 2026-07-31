"""
Paper and superconductor record APIs.
"""

from __future__ import annotations

import json
import re
import time
import threading
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.database import get_db
from backend.db_helpers import build_system_key
from backend.repositories.superconductors import search_superconductors
from backend.sc_types import SC_TYPE_LABELS, normalize_sc_type
from backend.utils.citation import generate_aps_citation, generate_bibtex_citation


router = APIRouter(prefix="/api/papers", tags=["papers"])

# 化学式中的元素符号（大写字母 + 可选小写字母），用于集合语义的元素匹配
_ELEMENT_TOKEN_RE = re.compile(r"[A-Z][a-z]?")


def _formula_element_set(formula: str | None) -> set[str]:
    """从化学式提取元素符号集合，如 LaH10 → {'La', 'H'}"""
    return set(_ELEMENT_TOKEN_RE.findall(formula or ""))


def _kp_to_dict(kp: models.KeyProperty) -> dict[str, Any]:
    """key_properties 序列化（含规范名中文标签与范围值）"""
    from backend.ingest.prop_names import PROP_LABELS
    return {
        "id": kp.id,
        "paper_id": kp.paper_id,
        "superconductor_id": kp.superconductor_id,
        "material": kp.material,
        "name": kp.name,
        "label": PROP_LABELS.get(kp.name, kp.name),
        "name_raw": kp.name_raw,
        "name_note": kp.name_note,
        "value_min": kp.value_min,
        "value_max": kp.value_max,
        "value_raw": kp.value_raw,
        "unit": kp.unit,
        "pressure_gpa": kp.pressure_gpa,
        "temperature_k": kp.temperature_k,
        "condition_json": kp.condition_json,
        "condition_note": kp.condition_note,
        "is_primary": kp.is_primary,
        "superconductor_type": kp.superconductor_type,
        "article_type": kp.article_type,
        "source_label": kp.source_label,
        "structure_text": kp.structure_text,
        "structure_format": kp.structure_format,
    }


def _paper_to_dict(paper: models.Paper, include_records: bool = True) -> dict[str, Any]:
    kps = paper.key_properties
    first_sc = next((kp.superconductor for kp in kps if kp.superconductor), None)
    payload = {
        "id": paper.id,
        "doi": paper.doi,
        "title": paper.title,
        "authors": paper.authors,
        "journal": paper.journal,
        "volume": paper.volume,
        "pages": paper.pages,
        "year": paper.year,
        "abstract": paper.abstract,
        "summary": paper.summary,
        "paper_type": paper.paper_type,
        "keywords_tags": paper.keywords_tags,
        "methodology": paper.methodology,
        "key_finding": paper.key_finding,
        "rationale": paper.rationale,
        "review_status": paper.review_status,
        "review_comment": paper.review_comment,
        "reviewed_by_user_id": paper.reviewed_by_user_id,
        "reviewed_at": paper.reviewed_at,
        "uploaded_by_user_id": paper.uploaded_by_user_id,
        "chemical_formula": first_sc.chemical_formula if first_sc else None,
        "compound_symbols": "-".join(first_sc.elements_list) if first_sc else None,
        "created_at": paper.created_at,
        "updated_at": paper.updated_at,
    }
    # Tc 摘要 — critical_temperature 物性的最大值
    tc_values = [kp.value_max for kp in kps
                 if kp.name == "critical_temperature" and kp.value_max is not None]
    payload["tc_max"] = max(tc_values) if tc_values else None
    # 聚合摘要
    payload["article_types"] = list({kp.article_type for kp in kps if kp.article_type})
    payload["superconductor_types"] = list({kp.superconductor_type for kp in kps if kp.superconductor_type})
    payload["pressures_gpa"] = sorted({kp.pressure_gpa for kp in kps if kp.pressure_gpa is not None})
    payload["materials"] = list({kp.material for kp in kps})
    if include_records:
        payload["key_properties"] = [_kp_to_dict(kp) for kp in kps]
    return payload


def _build_ris_content(papers: list[models.Paper]) -> str:
    entries: list[str] = []
    for paper in papers:
        lines = ["TY  - JOUR"]
        for author in crud.authors_to_list(paper.authors):
            if author:
                lines.append(f"AU  - {author}")
        if paper.title:
            lines.append(f"TI  - {paper.title}")
        if paper.journal:
            lines.append(f"JO  - {paper.journal}")
        if paper.year:
            lines.append(f"PY  - {paper.year}")
        if paper.volume:
            lines.append(f"VL  - {paper.volume}")
        if paper.pages:
            lines.append(f"SP  - {paper.pages}")
        if paper.doi:
            lines.append(f"DO  - {paper.doi}")
        first_sc = next((kp.superconductor for kp in paper.key_properties if kp.superconductor), None)
        if first_sc:
            lines.append(f"N1  - 化学式 {first_sc.chemical_formula}")
        lines.append("ER  - ")
        entries.append("\n".join(lines))
    return "\n\n".join(entries)


def _papers_response(
    papers: list[models.Paper],
    export_format: str,
    filename_base: str,
) -> Response:
    if export_format == "json":
        payload = {
            "papers": [_paper_to_dict(paper, include_records=True) for paper in papers],
            "total": len(papers),
        }
        return Response(
            content=json.dumps(payload, ensure_ascii=False, default=str, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.json"},
        )
    if export_format == "ris":
        return Response(
            content=_build_ris_content(papers),
            media_type="application/x-research-info-systems",
            headers={"Content-Disposition": f"attachment; filename={filename_base}.ris"},
        )
    raise HTTPException(status_code=400, detail="format 仅支持 json 或 ris")


def _query_papers_for_superconductors(
    db: Session,
    superconductor_ids: list[int],
    *,
    keyword: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    journal: str | None = None,
    crystal_structure: str | None = None,
    review_status: str | None = None,
    sort_by: str = "year",
    sort_order: str = "desc",
):
    query = (
        db.query(models.Paper)
        .join(models.KeyProperty)
        .join(models.Superconductor, models.KeyProperty.superconductor_id == models.Superconductor.id)
        .filter(models.Superconductor.id.in_(superconductor_ids))
        .distinct()
    )
    if keyword:
        pattern = f"%{keyword}%"
        query = query.filter(
            or_(
                models.Paper.title.like(pattern),
                models.Paper.doi.like(pattern),
                models.Paper.journal.like(pattern),
                models.Superconductor.chemical_formula.like(pattern),
            )
        )
    if year_min is not None:
        query = query.filter(models.Paper.year >= year_min)
    if year_max is not None:
        query = query.filter(models.Paper.year <= year_max)
    if journal:
        query = query.filter(models.Paper.journal.like(f"%{journal}%"))
    # crystal_structure：v2 物性表无该字段，条件忽略
    if review_status:
        query = query.filter(models.Paper.review_status == review_status)

    sort_column = models.Paper.created_at if sort_by == "created_at" else models.Paper.year
    query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
    return query


# 简单的内存缓存：key → (total, timestamp)
_count_cache: dict[str, tuple[int, float]] = {}
import time as _time

def _paginate(query, limit: int, offset: int, *, cache_key: str | None = None) -> dict[str, Any]:
    if cache_key is None:
        cache_key = str(query.statement.compile(compile_kwargs={"literal_binds": True}))
    if cache_key in _count_cache:
        total, ts = _count_cache[cache_key]
        if _time.time() - ts < 30:
            pass
        else:
            del _count_cache[cache_key]
            total = query.count()
            _count_cache[cache_key] = (total, _time.time())
    else:
        total = query.count()
        _count_cache[cache_key] = (total, _time.time())
    items = query.offset(offset).limit(limit).all()
    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [_paper_to_dict(paper, include_records=True) for paper in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": offset > 0,
        "has_next": offset + page_size < total,
    }


def _paginate_paper_items(items: list[models.Paper], limit: int, offset: int) -> dict[str, Any]:
    total = len(items)
    page_items = items[offset:offset + limit]
    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [_paper_to_dict(paper, include_records=True) for paper in page_items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": offset > 0,
        "has_next": offset + page_size < total,
    }


def _query_papers_preserving_superconductor_order(
    db: Session,
    superconductors: list[models.Superconductor],
    *,
    keyword: str | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    journal: str | None = None,
    crystal_structure: str | None = None,
    review_status: str | None = None,
    sort_by: str = "year",
    sort_order: str = "desc",
) -> list[models.Paper]:
    ordered: list[models.Paper] = []
    seen: set[int] = set()
    for superconductor in superconductors:
        query = _query_papers_for_superconductors(
            db,
            [superconductor.id],
            keyword=keyword,
            year_min=year_min,
            year_max=year_max,
            journal=journal,
            crystal_structure=crystal_structure,
            review_status=review_status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        for paper in query.all():
            if paper.id in seen:
                continue
            ordered.append(paper)
            seen.add(paper.id)
    return ordered


@router.get("/stats/user-ranking")
def get_user_ranking(db: Session = Depends(get_db)):
    users = db.query(models.User).all()
    rankings = [
        {
            "name": user.real_name,
            "count": db.query(models.Paper).filter(models.Paper.uploaded_by_user_id == user.id).count(),
        }
        for user in users
    ]
    rankings.sort(key=lambda item: item["count"], reverse=True)
    return rankings[:20]


@router.get("/compound/{element_symbols}")
def get_papers_by_compound(
    element_symbols: str,
    keyword: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    journal: Optional[str] = None,
    crystal_structure: Optional[str] = None,
    review_status: Optional[str] = None,
    sort_by: str = "year",
    sort_order: str = "desc",
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    _, symbols = build_system_key(element_symbols.split("-"))
    result = search_superconductors(
        db,
        "elements_exact_search",
        elements=symbols,
        limit=10000,
        offset=0,
    )
    if not result.items:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": limit,
            "total_pages": 0,
            "has_prev": False,
            "has_next": False,
        }
    query = _query_papers_for_superconductors(
        db,
        [item.id for item in result.items],
        keyword=keyword,
        year_min=year_min,
        year_max=year_max,
        journal=journal,
        crystal_structure=crystal_structure,
        review_status=review_status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return _paginate(query, limit, offset)


@router.post("/search-by-mode")
def search_papers_by_mode(
    request: schemas.PaperModeSearchRequest,
    db: Session = Depends(get_db),
):
    mode_map = {
        "only": "elements_exact_search",
        "combination": "elements_combination_search",
        "contains": "elements_contained_search",
        "formula_search": "formula_search",
        "elements_exact_search": "elements_exact_search",
        "elements_combination_search": "elements_combination_search",
        "elements_contained_search": "elements_contained_search",
    }
    mode = mode_map.get(request.mode, request.mode)
    result = search_superconductors(
        db,
        mode,
        formula=request.formula,
        elements=request.elements,
        formula_sort=request.formula_sort or "relevance",
        limit=10000,
        offset=0,
    )
    if not result.items:
        return {
            "items": [],
            "total": 0,
            "page": 1,
            "page_size": request.limit,
            "total_pages": 0,
            "has_prev": False,
            "has_next": False,
        }

    # 提取前端筛选参数
    tc_min = getattr(request, 'tc_min', None)
    tc_max = getattr(request, 'tc_max', None)
    pressure_min = getattr(request, 'pressure_min', None)
    pressure_max = getattr(request, 'pressure_max', None)
    sc_type = normalize_sc_type(getattr(request, 'superconductor_type', None))
    space_min = getattr(request, 'space_group_min', None)
    space_max = getattr(request, 'space_group_max', None)
    chart_only = getattr(request, 'chart_only', None)

    if mode == "formula_search":
        papers = _query_papers_preserving_superconductor_order(
            db,
            result.items,
            keyword=request.keyword,
            year_min=request.year_min,
            year_max=request.year_max,
            journal=request.journal,
            crystal_structure=request.crystal_structure,
            review_status=request.review_status,
            sort_by=request.sort_by or "year",
            sort_order=request.sort_order or "desc",
        )
        return _paginate_paper_items(papers, request.limit, request.offset)
    query = _query_papers_for_superconductors(
        db,
        [item.id for item in result.items],
        keyword=request.keyword,
        year_min=request.year_min,
        year_max=request.year_max,
        journal=request.journal,
        crystal_structure=request.crystal_structure,
        review_status=request.review_status,
        sort_by=request.sort_by or "year",
        sort_order=request.sort_order or "desc",
    )
    papers = query.all()

    # 论文级筛选：其 critical_temperature 物性满足 Tc/压强/类型/图表条件
    def _paper_matches(paper) -> bool:
        for kp in paper.key_properties:
            if kp.name != "critical_temperature" or kp.value_max is None:
                continue
            if tc_min is not None and kp.value_max < tc_min: continue
            if tc_max is not None and (kp.value_min or kp.value_max) > tc_max: continue
            if pressure_min is not None and (kp.pressure_gpa is None or kp.pressure_gpa < pressure_min): continue
            if pressure_max is not None and (kp.pressure_gpa is not None and kp.pressure_gpa > pressure_max): continue
            if sc_type and (kp.superconductor_type or '').lower() != sc_type: continue
            if chart_only and not kp.is_primary: continue
            return True
        return False

    if any(v is not None for v in (tc_min, tc_max, pressure_min, pressure_max)) or sc_type or chart_only:
        papers = [p for p in papers if _paper_matches(p)]
    return _paginate_paper_items(papers, request.limit, request.offset)


@router.post("/search/records")
def search_records_flat(
    request: schemas.PaperModeSearchRequest,
    db: Session = Depends(get_db),
):
    """返回扁平记录列表（基于 key_properties 的 critical_temperature 物性）"""
    mode_map = {
        "only": "elements_exact_search", "combination": "elements_combination_search",
        "contains": "elements_contained_search", "formula_search": "formula_search",
        "elements_exact_search": "elements_exact_search", "elements_combination_search": "elements_combination_search",
        "elements_contained_search": "elements_contained_search",
    }
    mode = mode_map.get(request.mode, request.mode)
    result = search_superconductors(db, mode, formula=request.formula, elements=request.elements,
                                     formula_sort=request.formula_sort or "relevance", limit=10000, offset=0)
    if not result.items:
        return {"items": [], "total": 0}
    sc_ids = [item.id for item in result.items]

    # 筛选参数
    tc_min = getattr(request, 'tc_min', None)
    tc_max = getattr(request, 'tc_max', None)
    pressure_min = getattr(request, 'pressure_min', None)
    pressure_max = getattr(request, 'pressure_max', None)
    sc_type = normalize_sc_type(getattr(request, 'superconductor_type', None))
    chart_only = getattr(request, 'chart_only', None)

    KP, P = models.KeyProperty, models.Paper
    query = (
        db.query(KP, P)
        .join(P, KP.paper_id == P.id)
        .filter(KP.superconductor_id.in_(sc_ids))
        .filter(KP.name == "critical_temperature")
        .filter(KP.value_max.isnot(None))
    )
    if request.keyword:
        pattern = f"%{request.keyword}%"
        query = query.filter(or_(
            P.title.like(pattern), P.doi.like(pattern),
            P.journal.like(pattern), KP.material.like(pattern),
        ))
    if request.year_min is not None:
        query = query.filter(P.year >= request.year_min)
    if request.year_max is not None:
        query = query.filter(P.year <= request.year_max)
    if request.journal:
        query = query.filter(P.journal.like(f"%{request.journal}%"))
    if request.review_status:
        query = query.filter(P.review_status == request.review_status)
    # Tc 区间筛选按范围相交语义
    if tc_min is not None:
        query = query.filter(KP.value_max >= tc_min)
    if tc_max is not None:
        query = query.filter(KP.value_min <= tc_max)
    if pressure_min is not None:
        query = query.filter(KP.pressure_gpa >= pressure_min)
    if pressure_max is not None:
        query = query.filter(KP.pressure_gpa <= pressure_max)
    if sc_type:
        query = query.filter(KP.superconductor_type == sc_type)
    if chart_only:
        query = query.filter(KP.is_primary.is_(True))

    sort_col = P.created_at if (request.sort_by == "created_at") else P.year
    query = query.order_by(sort_col.asc() if request.sort_order == "asc" else sort_col.desc(), KP.id.asc())

    total = query.count()
    page_size = request.limit or 50
    offset = request.offset or 0
    rows = query.offset(offset).limit(page_size).all()

    status_map = {'pending': 'Pending', 'approved': 'Approved', 'reviewed': 'Approved', 'rejected': 'Rejected'}

    def _tc_display(kp: models.KeyProperty) -> str:
        if kp.value_min is not None and kp.value_max is not None and kp.value_min != kp.value_max:
            return f"{kp.value_min:.1f}–{kp.value_max:.1f} K"
        return f"{kp.value_max:.1f} K"

    items = [{
        "record_id": kp.id,
        "paper_id": paper.id,
        "year": paper.year or 0,
        "formula": kp.material or "-",
        "type": SC_TYPE_LABELS.get(kp.superconductor_type or "", "Unknown"),
        "pressure": f"{kp.pressure_gpa:g} GPa" if kp.pressure_gpa is not None else "-",
        "tc": _tc_display(kp),
        "space_group": "-",
        "source": "Local",
        "status": status_map.get(paper.review_status, "Pending"),
        "doi": paper.doi or "-",
    } for kp, paper in rows]
    return {"items": items, "total": total}


@router.get("/crystal-structures")
def get_crystal_structures(db: Session = Depends(get_db)):
    # v2 物性表暂无晶体结构字段
    return []


@router.get("/share-export")
def export_share_papers(
    format: Literal["json", "ris"] = Query("json", description="导出格式"),
    scope: Literal["all", "search"] = Query("all", description="导出范围"),
    mode: str = Query("elements_combination_search", description="搜索模式"),
    formula: str | None = Query(None, description="化学式搜索表达式"),
    elements: str | None = Query(None, description="逗号分隔的元素符号"),
    db: Session = Depends(get_db),
):
    if scope == "all":
        papers = db.query(models.Paper).order_by(models.Paper.year.desc().nullslast(), models.Paper.id.desc()).all()
        return _papers_response(papers, format, "sc-wiki-all-papers")

    requested_elements = [item.strip() for item in (elements or "").split(",") if item.strip()]
    if mode == "formula_search" and not formula:
        raise HTTPException(status_code=400, detail="化学式检索需要 formula")
    if mode != "formula_search" and not requested_elements:
        raise HTTPException(status_code=400, detail="元素检索需要 elements")

    mode_map = {
        "only": "elements_exact_search",
        "combination": "elements_combination_search",
        "contains": "elements_contained_search",
        "formula_search": "formula_search",
        "elements_exact_search": "elements_exact_search",
        "elements_combination_search": "elements_combination_search",
        "elements_contained_search": "elements_contained_search",
    }
    normalized_mode = mode_map.get(mode)
    if normalized_mode is None:
        raise HTTPException(status_code=400, detail="不支持的搜索模式")

    result = search_superconductors(
        db,
        normalized_mode,
        formula=formula,
        elements=requested_elements,
        formula_sort="relevance",
        limit=10000,
        offset=0,
    )
    if not result.items:
        return _papers_response([], format, "sc-wiki-search-empty")

    if normalized_mode == "formula_search":
        papers = _query_papers_preserving_superconductor_order(db, result.items)
    else:
        query = _query_papers_for_superconductors(db, [item.id for item in result.items])
        papers = query.all()

    filename_key = formula if normalized_mode == "formula_search" else "-".join(sorted(requested_elements))
    safe_key = re.sub(r"[^A-Za-z0-9_.-]+", "-", filename_key or "search").strip("-") or "search"
    return _papers_response(papers, format, f"sc-wiki-{safe_key}")


@router.get("/{paper_id}")
def get_paper_detail(paper_id: int, db: Session = Depends(get_db)):
    paper = crud.get_paper_by_id(db, paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="文献不存在")
    return _paper_to_dict(paper)


@router.get("/{paper_id}/images/{image_order}")
def get_paper_image(paper_id: int, image_order: int):
    raise HTTPException(status_code=410, detail="文献图片存储已下线")


@router.get("/images/{image_id}")
def get_image_by_id(image_id: int):
    raise HTTPException(status_code=410, detail="文献图片存储已下线")


@router.post("/export")
def export_papers(export_data: schemas.ExportFormat, db: Session = Depends(get_db)):
    papers = crud.get_papers_by_ids(db, export_data.paper_ids)
    if not papers:
        raise HTTPException(status_code=404, detail="未找到文献")

    citations = []
    for paper in papers:
        authors = crud.authors_to_list(paper.authors)
        if export_data.format == "aps":
            citations.append(generate_aps_citation(authors, paper.title, paper.journal, paper.volume, paper.pages, paper.year, paper.doi))
        elif export_data.format == "bibtex":
            citations.append(generate_bibtex_citation(authors, paper.title, paper.journal, paper.volume, paper.pages, paper.year, paper.doi))

    return Response(
        content="\n\n".join(citations),
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename=citations.{export_data.format}"},
    )


@router.get("/stats/tc-pressure")
def get_tc_pressure_chart_data(db: Session = Depends(get_db)):
    KP, P = models.KeyProperty, models.Paper
    rows = (
        db.query(KP, P)
        .outerjoin(P, KP.paper_id == P.id)
        .filter(KP.name == "critical_temperature")
        .filter(KP.value_max.isnot(None))
        .filter(KP.pressure_gpa.isnot(None))
        .all()
    )
    return [
        {
            "x": kp.pressure_gpa,
            "y": kp.value_max,
            "type": "experimental" if kp.article_type == "e" else "theoretical",
            "year": paper.year if paper else None,
            "label": kp.material,
            "sc_type": kp.superconductor_type or "others",
            "formula": kp.material,
            "space_group": None,
            "source_label": kp.source_label,
        }
        for kp, paper in rows
        if kp.is_primary
    ]


@router.get("/stats/tc-year")
def get_tc_year_chart_data(db: Session = Depends(get_db)):
    KP, P = models.KeyProperty, models.Paper
    rows = (
        db.query(KP, P)
        .join(P, KP.paper_id == P.id)
        .filter(KP.name == "critical_temperature")
        .filter(KP.value_max.isnot(None))
        .filter(P.year.isnot(None))
        .all()
    )
    return [
        {
            "x": paper.year,
            "y": kp.value_max,
            "type": "experimental" if kp.article_type == "e" else "theoretical",
            "sc_type": kp.superconductor_type or "others",
            "label": kp.material,
            "formula": kp.material,
            "doi": paper.doi,
            "source_label": kp.source_label,
        }
        for kp, paper in rows
        if kp.is_primary
    ]


@router.get("/stats/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    return get_tc_pressure_chart_data(db)


# ---------- 全数据库聚合搜索（带缓存）----------

_search_cache: dict[str, dict[str, Any]] = {}
_search_cache_lock = threading.Lock()
_CACHE_TTL = 300  # 5 分钟


def _build_cache_key(elements: list[str], mode: str) -> str:
    return "-".join(sorted(elements)) + "|" + (mode or "contains")


def _fetch_all_sources(elements: list[str], mode: str) -> list[dict]:
    """取三源全量数据，合并为统一格式列表"""
    items: list[dict] = []

    # 1. 本地
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        from backend.repositories.superconductors import search_superconductors
        result = search_superconductors(db, mode, elements=elements, limit=10000, offset=0)
        if result.items:
            query = _query_papers_for_superconductors(db, [r.id for r in result.items])
            for paper in query.all():
                d = _paper_to_dict(paper, include_records=True)
                d["_source"] = "local"
                items.append(d)
    finally:
        db.close()

    # 2. Alexandria
    try:
        from backend.services.alexandria_mysql import query_by_elements
        alex_mode = {"elements_exact_search": "only", "elements_combination_search": "combination", "elements_contained_search": "contains"}.get(mode, "contains")
        alex_result = query_by_elements(elements=elements, mode=alex_mode, limit=10000, offset=0)
        for m in (alex_result.get("items") or []):
            m["_source"] = "alexandria"
            items.append(m)
    except Exception:
        pass

    # 3. HTSC-2025
    try:
        from backend.api.htsc2025 import _entry_matches, _load_dataset

        htsc_mode = {"elements_exact_search": "only", "elements_combination_search": "combination", "elements_contained_search": "contains"}.get(mode, "contains")
        query_set = set(elements)
        data = _load_dataset()
        for item in (data.get("records") or []):
            entry_elements = set(item.get("elements") or [])
            if _entry_matches(entry_elements, query_set, htsc_mode):
                copied = dict(item)
                copied["_source"] = "htsc2025"
                items.append(copied)
    except Exception:
        pass

    return items


def _group_and_sort(items: list[dict]) -> list[dict]:
    """按 compound 分组，组间按条目数降序，组内按 Tc 降序"""
    grouped: dict[str, list[dict]] = {}
    for item in items:
        if item.get("_source") == "local":
            key = item.get("compound_symbols") or item.get("chemical_formula") or "未知"
        else:
            key = "-".join(sorted(item.get("elements") or []))
        grouped.setdefault(key, []).append(item)

    # 组内按 Tc 降序
    def _tc(item):
        if item.get("_source") == "alexandria":
            return item.get("tc_allen_dynes") or item.get("tc_max") or 0
        if item.get("_source") == "htsc2025":
            return item.get("tc") or 0
        return item.get("experimental_tc") or item.get("anisotropic_eliashberg_tc") or item.get("isotropic_eliashberg_tc") or item.get("allen_dynes_tc") or item.get("mcmillan_tc") or 0

    # 过滤无 Tc 的条目
    for k in list(grouped.keys()):
        grouped[k] = [item for item in grouped[k] if _tc(item) > 0]
        if not grouped[k]:
            del grouped[k]

    # 排序优先级：来源（本地 > Alexandria > HTSC），再按 Tc 降序
    _src_order = {"local": 0, "alexandria": 1, "htsc2025": 2}
    for k in grouped:
        grouped[k].sort(key=lambda item: (_src_order.get(item.get("_source", ""), 3), -_tc(item)))

    def _local_count(kv):
        return sum(1 for item in kv[1] if item.get("_source") == "local")

    # 组间：按本地条目数降序，相同则按最高 Tc 降序
    sorted_groups = sorted(grouped.items(), key=lambda kv: (_local_count(kv), max((_tc(i) for i in kv[1]), default=0)), reverse=True)

    # 展平
    flat = []
    for key, group_items in sorted_groups:
        flat.append({"_type": "section", "key": key, "count": len(group_items)})
        flat.extend(group_items)
    return flat


@router.post("/search/all")
def search_all(request: schemas.PaperModeSearchRequest, db: Session = Depends(get_db)):
    elements = request.elements or []
    mode = request.mode or "elements_contained_search"
    page = max(1, request.offset // request.limit + 1)
    page_size = request.limit or 30

    # 全部来源检索必须提供元素（空集合在 contains 模式下会匹配全量外部数据）
    if not elements:
        return {"items": [], "total": 0, "page": 1, "page_size": page_size,
                "total_pages": 0, "has_prev": False, "has_next": False, "cached": False}

    cache_key = _build_cache_key(elements, mode)

    with _search_cache_lock:
        entry = _search_cache.get(cache_key)
        if entry and time.time() - entry["ts"] < _CACHE_TTL:
            flat = entry["flat"]
        else:
            items = _fetch_all_sources(elements, mode)
            flat = _group_and_sort(items)
            _search_cache[cache_key] = {"flat": flat, "ts": time.time()}

    start = (page - 1) * page_size
    page_items = flat[start:start + page_size]
    total = sum(1 for i in flat if i.get("_type") != "section")

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size) if total > 0 else 0,
        "has_prev": start > 0,
        "has_next": start + page_size < len(flat),
        "cached": cache_key in _search_cache,
    }
