"""
Paper and superconductor record APIs.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from backend import crud, models, schemas
from backend.chart_rules import (
    include_in_tc_pressure_chart,
    include_in_tc_year_chart,
    representative_tc,
)
from backend.database import get_db
from backend.db_helpers import build_system_key
from backend.repositories.superconductors import search_superconductors
from backend.security import get_current_user
from backend.utils.citation import generate_aps_citation, generate_bibtex_citation
from backend.utils.doi_resolver import get_doi_metadata, validate_doi


router = APIRouter(prefix="/api/papers", tags=["papers"])


def _is_admin(user: models.User) -> bool:
    return user.role in {"admin", "superadmin"}


def _parse_json(value: str | None, default: Any) -> Any:
    if value is None or value == "":
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"JSON 格式错误: {exc.msg}") from exc


def _first_number(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, list):
        return _first_number(value[0]) if value else None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _record_payloads(records: str | None, physical_data: str | None, defaults: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = _parse_json(records, None)
    if raw_items is None:
        raw_items = _parse_json(physical_data, None)
    if not isinstance(raw_items, list) or not raw_items:
        raise HTTPException(status_code=400, detail="records 必须是非空 JSON 数组")

    normalized: list[dict[str, Any]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise HTTPException(status_code=400, detail="records 中的每一项都必须是对象")
        item = {**defaults, **raw}
        formula = item.get("chemical_formula")
        if not formula:
            raise HTTPException(status_code=400, detail="每条记录都必须提供 chemical_formula")
        pressure = _first_number(item.get("pressure_gpa", item.get("tc_press")))
        if pressure is None:
            raise HTTPException(status_code=400, detail=f"{formula} 缺少 pressure_gpa")

        tc_value = _first_number(item.get("tc"))
        if tc_value is not None:
            if item.get("article_type") == "experimental":
                item.setdefault("experimental_tc", tc_value)
            else:
                item.setdefault("mcmillan_tc", tc_value)

        item["chemical_formula"] = formula
        item["pressure_gpa"] = pressure
        item.setdefault("space_group_symbol", item.get("crystal_structure"))
        normalized.append(item)
    return normalized


def _create_record(db: Session, paper: models.Paper, item: dict[str, Any]) -> models.SuperconductorRecord:
    superconductor = crud.get_or_create_superconductor(db, item["chemical_formula"])
    record = models.SuperconductorRecord(
        superconductor_id=superconductor.id,
        paper_id=paper.id,
        source_label=item.get("source_label") or "paper",
        pressure_gpa=item["pressure_gpa"],
        space_group_symbol=item.get("space_group_symbol"),
        space_group_number=item.get("space_group_number"),
        crystal_structure=item.get("crystal_structure"),
        thermodynamically_stable=item.get("thermodynamically_stable"),
        dynamically_stable=item.get("dynamically_stable"),
        energy_above_hull=item.get("energy_above_hull"),
        mcmillan_tc=item.get("mcmillan_tc"),
        allen_dynes_tc=item.get("allen_dynes_tc"),
        isotropic_eliashberg_tc=item.get("isotropic_eliashberg_tc"),
        anisotropic_eliashberg_tc=item.get("anisotropic_eliashberg_tc"),
        experimental_tc=item.get("experimental_tc"),
        lambda_value=item.get("lambda_value"),
        omega_log=item.get("omega_log"),
        n_ef_total=item.get("n_ef_total"),
        element_n_ef=item.get("element_n_ef"),
        pseudopotential_type=item.get("pseudopotential_type"),
        pseudopotential_name=item.get("pseudopotential_name"),
        exchange_correlation_functional=item.get("exchange_correlation_functional"),
        calculation_code=item.get("calculation_code"),
        k_grid=item.get("k_grid"),
        q_grid=item.get("q_grid"),
        energy_cutoff_value=item.get("energy_cutoff_value"),
        energy_cutoff_unit=item.get("energy_cutoff_unit"),
        show_in_chart=bool(item.get("show_in_chart", False)),
        s_factor=item.get("s_factor"),
        method=item.get("method"),
        note=item.get("note"),
    )
    db.add(record)
    return record


def _record_to_dict(record: models.SuperconductorRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "superconductor_id": record.superconductor_id,
        "chemical_formula": record.superconductor.chemical_formula if record.superconductor else None,
        "source_label": record.source_label,
        "pressure_gpa": record.pressure_gpa,
        "space_group_symbol": record.space_group_symbol,
        "space_group_number": record.space_group_number,
        "crystal_structure": record.crystal_structure,
        "thermodynamically_stable": record.thermodynamically_stable,
        "dynamically_stable": record.dynamically_stable,
        "energy_above_hull": record.energy_above_hull,
        "mcmillan_tc": record.mcmillan_tc,
        "allen_dynes_tc": record.allen_dynes_tc,
        "isotropic_eliashberg_tc": record.isotropic_eliashberg_tc,
        "anisotropic_eliashberg_tc": record.anisotropic_eliashberg_tc,
        "experimental_tc": record.experimental_tc,
        "lambda_value": record.lambda_value,
        "omega_log": record.omega_log,
        "n_ef_total": record.n_ef_total,
        "element_n_ef": record.element_n_ef,
        "pseudopotential_type": record.pseudopotential_type,
        "pseudopotential_name": record.pseudopotential_name,
        "exchange_correlation_functional": record.exchange_correlation_functional,
        "calculation_code": record.calculation_code,
        "k_grid": record.k_grid,
        "q_grid": record.q_grid,
        "energy_cutoff_value": record.energy_cutoff_value,
        "energy_cutoff_unit": record.energy_cutoff_unit,
        "show_in_chart": record.show_in_chart,
        "s_factor": record.s_factor,
        "method": record.method,
        "note": record.note,
    }


def _paper_to_dict(paper: models.Paper, include_records: bool = True) -> dict[str, Any]:
    first_record = paper.records[0] if paper.records else None
    first_superconductor = first_record.superconductor if first_record else None
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
        "review_status": paper.review_status,
        "review_comment": paper.review_comment,
        "reviewed_by_user_id": paper.reviewed_by_user_id,
        "reviewed_at": paper.reviewed_at,
        "uploaded_by_user_id": paper.uploaded_by_user_id,
        "chemical_formula": first_superconductor.chemical_formula if first_superconductor else None,
        "compound_symbols": "-".join(first_superconductor.elements_list) if first_superconductor else None,
        "created_at": paper.created_at,
        "updated_at": paper.updated_at,
    }
    if include_records:
        payload["records"] = [_record_to_dict(record) for record in paper.records]
    return payload


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
        .join(models.SuperconductorRecord)
        .join(models.Superconductor)
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
    if crystal_structure:
        query = query.filter(models.SuperconductorRecord.crystal_structure.like(f"%{crystal_structure}%"))
    if review_status:
        query = query.filter(models.Paper.review_status == review_status)

    sort_column = models.Paper.created_at if sort_by == "created_at" else models.Paper.year
    query = query.order_by(sort_column.asc() if sort_order == "asc" else sort_column.desc())
    return query


def _paginate(query, limit: int, offset: int) -> dict[str, Any]:
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if total > 0 else 0
    return {
        "items": [_paper_to_dict(paper, include_records=False) for paper in items],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": offset > 0,
        "has_next": offset + page_size < total,
    }


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


@router.post("/")
async def create_paper(
    doi: str = Form(...),
    title: Optional[str] = Form(None),
    authors: str = Form("[]"),
    journal: Optional[str] = Form(None),
    volume: Optional[str] = Form(None),
    pages: Optional[str] = Form(None),
    year: Optional[int] = Form(None),
    abstract: Optional[str] = Form(None),
    records: Optional[str] = Form(None),
    physical_data: Optional[str] = Form(None),
    chemical_formula: Optional[str] = Form(None),
    crystal_structure: Optional[str] = Form(None),
    article_type: Optional[str] = Form(None),
    superconductor_type: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Annotated[models.User, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录后再上传文献")
    if db.query(models.Paper).filter(models.Paper.doi == doi).first():
        raise HTTPException(status_code=400, detail=f"文献 {doi} 已存在")

    metadata = None
    if title is None:
        if not _is_admin(current_user) and not await validate_doi(doi):
            raise HTTPException(status_code=400, detail=f"DOI {doi} 无效或不存在，请检查格式")
        metadata = await get_doi_metadata(doi)
        if not metadata and not _is_admin(current_user):
            raise HTTPException(status_code=500, detail="无法获取文献元数据，请稍后重试")
        metadata = metadata or {}

    authors_list = _parse_json(authors, None)
    if authors_list is None:
        authors_list = metadata.get("authors", []) if metadata else []
    if not isinstance(authors_list, list):
        raise HTTPException(status_code=400, detail="authors 必须是 JSON 数组")

    defaults = {
        "chemical_formula": chemical_formula,
        "crystal_structure": crystal_structure,
        "article_type": article_type,
        "superconductor_type": superconductor_type,
        "note": notes,
    }
    record_items = _record_payloads(records, physical_data, defaults)

    paper = models.Paper(
        doi=doi,
        title=title or metadata.get("title") or f"Manual Entry: {doi}",
        journal=journal or (metadata.get("journal") if metadata else None),
        volume=volume or (metadata.get("volume") if metadata else None),
        pages=pages or (metadata.get("pages") if metadata else None),
        year=year or (metadata.get("year") if metadata else None),
        abstract=abstract or (metadata.get("abstract") if metadata else None),
        authors=authors_list,
        uploaded_by_user_id=current_user.id,
        review_status="pending",
    )

    try:
        db.add(paper)
        db.flush()
        for item in record_items:
            _create_record(db, paper, item)
        db.commit()
        db.refresh(paper)
    except Exception:
        db.rollback()
        raise

    return _paper_to_dict(paper)


@router.post("/batch-upload")
async def batch_upload_papers(
    file: UploadFile = File(...),
    current_user: Annotated[models.User, Depends(get_current_user)] = None,
):
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录后再进行批量上传")
    raise HTTPException(status_code=501, detail="批量导入将按新 MySQL 结构重新实现")


@router.get("/batch-upload-example")
def get_batch_upload_example():
    raise HTTPException(status_code=501, detail="批量上传示例需按新 superconductor_records 格式重新生成")


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
        elements=request.elements,
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
    return _paginate(query, request.limit, request.offset)


@router.get("/crystal-structures")
def get_crystal_structures(db: Session = Depends(get_db)):
    rows = (
        db.query(models.SuperconductorRecord.crystal_structure)
        .filter(models.SuperconductorRecord.crystal_structure.isnot(None))
        .distinct()
        .all()
    )
    return sorted(value for (value,) in rows if value)


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
    rows = db.query(models.SuperconductorRecord).join(models.SuperconductorRecord.superconductor).all()
    return [
        {
            "x": row.pressure_gpa,
            "y": representative_tc(row),
            "formula": row.superconductor.chemical_formula,
            "space_group": row.space_group_symbol,
            "source_label": row.source_label,
        }
        for row in rows
        if include_in_tc_pressure_chart(row)
    ]


@router.get("/stats/tc-year")
def get_tc_year_chart_data(db: Session = Depends(get_db)):
    rows = (
        db.query(models.SuperconductorRecord)
        .join(models.SuperconductorRecord.paper)
        .join(models.SuperconductorRecord.superconductor)
        .all()
    )
    return [
        {
            "x": row.paper.year,
            "y": representative_tc(row),
            "formula": row.superconductor.chemical_formula,
            "doi": row.paper.doi,
            "source_label": row.source_label,
        }
        for row in rows
        if row.paper and row.paper.year and include_in_tc_year_chart(row)
    ]


@router.get("/stats/chart-data")
def get_chart_data(db: Session = Depends(get_db)):
    return get_tc_pressure_chart_data(db)
