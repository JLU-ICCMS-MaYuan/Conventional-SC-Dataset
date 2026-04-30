"""
数据库CRUD与新旧前端兼容转换。
"""
import json
import math
import re
from typing import List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Query, Session

from backend import models, schemas


ARTICLE_TYPE_TO_LONG = {"e": "experimental", "t": "theoretical"}
ARTICLE_TYPE_TO_SHORT = {"experimental": "e", "theoretical": "t"}
SC_TYPE_TO_LONG = {
    "c": "cuprate",
    "i": "iron_based",
    "n": "nickel_based",
    "h": "hydride",
    "cb": "carbon",
    "or": "organic",
    "ot": "others",
}
SC_TYPE_TO_SHORT = {v: k for k, v in SC_TYPE_TO_LONG.items()}
SC_TYPE_TO_SHORT.update({
    "carbon_organic": "cb",
    "conventional": "ot",
    "other_conventional": "ot",
    "unconventional": "ot",
    "other_unconventional": "ot",
    "unknown": "ot",
})


def normalize_article_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return ARTICLE_TYPE_TO_LONG.get(value, value)


def to_storage_article_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return ARTICLE_TYPE_TO_SHORT.get(value, value)


def normalize_superconductor_type(value: Optional[str]) -> str:
    if not value:
        return "others"
    return SC_TYPE_TO_LONG.get(value, value if value in SC_TYPE_TO_SHORT else "others")


def to_storage_superconductor_type(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    return SC_TYPE_TO_SHORT.get(value, value)


def compute_s_factor(pressure: Optional[float], tc: Optional[float]) -> Optional[float]:
    """根据压强与 Tc 计算 s_factor: s = tc / sqrt(1521 + pressure^2)。"""
    if pressure is None or tc is None:
        return None
    try:
        pressure_val = float(pressure)
        tc_val = float(tc)
    except (TypeError, ValueError):
        return None

    denominator = math.sqrt(1521 + pressure_val ** 2)
    return None if denominator == 0 else tc_val / denominator


def safe_json_loads(value, default):
    if value is None:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def parse_formula_counts(formula: Optional[str]) -> dict[str, int]:
    if not formula:
        return {}
    out: dict[str, int] = {}
    for sym, num in re.findall(r"([A-Z][a-z]?)(\d*)", formula):
        out[sym] = out.get(sym, 0) + (int(num) if num else 1)
    return out


def normalize_numeric_range(value) -> Optional[list[float]]:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("区间字段必须是数组")

    cleaned = []
    for item in value:
        if item is None:
            continue
        try:
            cleaned.append(float(item))
        except (TypeError, ValueError) as exc:
            raise ValueError("区间字段必须只包含数字") from exc

    if not cleaned:
        return None
    if len(cleaned) > 2:
        raise ValueError("区间字段最多只能包含两个数值")
    if len(cleaned) == 2 and cleaned[0] > cleaned[1]:
        cleaned.sort()
    return cleaned


def representative_value(values: Optional[list[float]]) -> Optional[float]:
    if not values:
        return None
    if len(values) == 1:
        return values[0]
    return sum(values[:2]) / min(len(values), 2)


def range_to_json(value) -> Optional[str]:
    normalized = normalize_numeric_range(value)
    return json.dumps(normalized, ensure_ascii=False) if normalized is not None else None


def compute_s_factor_from_ranges(pressure_range, tc_range) -> Optional[float]:
    return compute_s_factor(representative_value(pressure_range), representative_value(tc_range))


def get_all_elements(db: Session) -> List[models.Element]:
    return db.query(models.Element).order_by(models.Element.atomic_number).all()


def get_element_by_symbol(db: Session, symbol: str) -> Optional[models.Element]:
    return db.query(models.Element).filter(models.Element.symbol == symbol).first()


def get_elements_by_symbols(db: Session, symbols: List[str]) -> List[models.Element]:
    return db.query(models.Element).filter(models.Element.symbol.in_(symbols)).all()


def get_compound_element_list(compound: models.Compound) -> List[str]:
    values = safe_json_loads(compound.element_list, [])
    return values if isinstance(values, list) else []


def get_compound_key(compound: models.Compound) -> str:
    values = get_compound_element_list(compound)
    return "-".join(values) if values else (compound.chemical_formula or "")


def get_or_create_compound(db: Session, element_symbols: List[str], chemical_formula: Optional[str] = None) -> Optional[models.Compound]:
    """按化学式创建新结构 compound；没有化学式时用元素组合兼容上传流程。"""
    formula = chemical_formula or "".join(element_symbols)
    formula = formula.strip() if formula else None
    if not formula:
        return None

    compound = db.query(models.Compound).filter(models.Compound.chemical_formula == formula).first()
    if compound:
        return compound

    counts = parse_formula_counts(formula)
    elements = sorted(counts) if counts else sorted(set(element_symbols))
    element_rows = get_elements_by_symbols(db, elements)
    element_id_map = {e.symbol: e.id for e in element_rows}
    composition = []
    for symbol in elements:
        composition.extend([symbol, counts.get(symbol, 1)])

    compound = models.Compound(
        chemical_formula=formula,
        element_list=json.dumps(elements, ensure_ascii=False),
        composition=json.dumps(composition, ensure_ascii=False),
        element_id_list=json.dumps([element_id_map[s] for s in elements if s in element_id_map], ensure_ascii=False),
        element_ratio=json.dumps(composition, ensure_ascii=False),
    )
    db.add(compound)
    db.commit()
    db.refresh(compound)
    return compound


def get_compounds_by_symbols(db: Session, element_symbols: List[str], exact: bool = True) -> List[models.Compound]:
    selection = set(element_symbols)
    out = []
    for compound in db.query(models.Compound).all():
        symbols = set(get_compound_element_list(compound))
        if not symbols:
            continue
        if (symbols == selection) if exact else selection.issubset(symbols):
            out.append(compound)
    return out


def get_compound_by_symbols(db: Session, element_symbols: List[str]) -> Optional[models.Compound]:
    matches = get_compounds_by_symbols(db, element_symbols, exact=True)
    return matches[0] if matches else None


def search_compounds_by_elements(db: Session, element_symbols: List[str], mode: str, limit: Optional[int] = None, offset: int = 0) -> dict:
    allowed_modes = {"only", "combination", "contains"}
    mode = mode if mode in allowed_modes else "combination"
    selection = set(element_symbols)
    grouped: dict[str, dict] = {}

    for compound in db.query(models.Compound).all():
        element_list = get_compound_element_list(compound)
        symbols = set(element_list)
        if not symbols:
            continue
        if mode == "only":
            ok = symbols == selection
        elif mode == "combination":
            ok = symbols.issubset(selection)
        else:
            ok = selection.issubset(symbols)
        if not ok:
            continue

        key = get_compound_key(compound)
        if key not in grouped:
            grouped[key] = {
                "id": compound.id,
                "element_symbols": key,
                "element_list": element_list,
                "paper_count": 0,
            }
        grouped[key]["paper_count"] += get_compound_papers_count(db, compound.id)

    matched = list(grouped.values())
    matched.sort(key=lambda item: (len(item["element_list"]), item["element_symbols"]))

    total = len(matched)
    page_size = limit if limit is not None else total
    page_items = matched[offset: offset + limit] if limit is not None else matched
    page = (offset // page_size) + 1 if page_size else 1
    total_pages = (total + page_size - 1) // page_size if page_size and total > 0 else 0

    return {
        "items": page_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": offset > 0,
        "has_next": offset + page_size < total if page_size else False,
    }


def get_matching_compound_ids(db: Session, element_symbols: List[str], mode: str) -> List[int]:
    allowed_modes = {"only", "combination", "contains"}
    mode = mode if mode in allowed_modes else "combination"
    selection = set(element_symbols)
    matched_ids: List[int] = []

    for compound in db.query(models.Compound).all():
        element_list = get_compound_element_list(compound)
        symbols = set(element_list)
        if not symbols:
            continue
        if mode == "only":
            ok = symbols == selection
        elif mode == "combination":
            ok = symbols.issubset(selection)
        else:
            ok = selection.issubset(symbols)
        if ok:
            matched_ids.append(compound.id)

    return matched_ids


def check_compound_has_papers(db: Session, element_symbols: List[str]) -> bool:
    return any(get_compound_papers_count(db, c.id) > 0 for c in get_compounds_by_symbols(db, element_symbols, exact=True))


def create_paper(
    db: Session,
    compound_id: int,
    doi: str,
    title: str,
    article_type: str,
    superconductor_type: str,
    authors: Optional[str] = None,
    journal: Optional[str] = None,
    volume: Optional[str] = None,
    pages: Optional[str] = None,
    year: Optional[int] = None,
    abstract: Optional[str] = None,
    chemical_formula: Optional[str] = None,
    crystal_structure: Optional[str] = None,
    **_,
) -> models.Paper:
    paper = models.Paper(
        doi=doi,
        title=title,
        authors=authors,
        journal=journal,
        volume=volume,
        pages=pages,
        year=year,
        abstract=abstract,
    )
    db.add(paper)
    db.flush()
    db_data = models.PaperData(
        paper_id=paper.id,
        compound_id=compound_id,
        article_type=to_storage_article_type(article_type),
        superconductor_type=to_storage_superconductor_type(superconductor_type),
        chemical_formula=chemical_formula,
        crystal_structure=crystal_structure,
        sequence_in_paper=1,
    )
    db.add(db_data)
    db.commit()
    db.refresh(paper)
    return paper


def create_paper_data(db: Session, paper_id: int, data_list: List[dict], compound_id: Optional[int] = None) -> List[models.PaperData]:
    db_data_list = []
    for idx, item in enumerate(data_list, start=1):
        pressure_range = normalize_numeric_range(item.get("tc_press"))
        tc_range = normalize_numeric_range(item.get("tc"))
        s_factor_val = item.get("s_factor")
        if s_factor_val is None:
            s_factor_val = compute_s_factor_from_ranges(pressure_range, tc_range)
        db_data = models.PaperData(
            paper_id=paper_id,
            compound_id=compound_id or item.get("compound_id"),
            article_type=to_storage_article_type(item.get("article_type")),
            superconductor_type=to_storage_superconductor_type(item.get("superconductor_type")),
            chemical_formula=item.get("chemical_formula"),
            crystal_structure=item.get("crystal_structure"),
            tc=range_to_json(tc_range),
            tc_press=range_to_json(pressure_range),
            lambda_val=item.get("lambda_val"),
            omega_log=item.get("omega_log"),
            n_ef=item.get("n_ef"),
            s_factor=s_factor_val,
            sample_name=item.get("sample_name"),
            data_source_note=item.get("data_source_note"),
            sequence_in_paper=idx,
        )
        db.add(db_data)
        db_data_list.append(db_data)
    db.commit()
    return db_data_list


def check_paper_exists(db: Session, compound_id: int, doi: str) -> bool:
    return db.query(models.Paper).join(models.PaperData).filter(
        models.Paper.doi == doi,
        models.PaperData.compound_id == compound_id,
    ).first() is not None


def _build_papers_query(db: Session, compound_ids: List[int], search_params: Optional[schemas.PaperSearchParams] = None) -> Query:
    query = db.query(models.Paper).join(models.PaperData).filter(models.PaperData.compound_id.in_(compound_ids)).distinct()
    if not search_params:
        return query
    if search_params.keyword:
        keyword = f"%{search_params.keyword}%"
        query = query.filter(or_(
            models.Paper.title.like(keyword),
            models.Paper.abstract.like(keyword),
            models.Paper.authors.like(keyword),
            models.PaperData.chemical_formula.like(keyword),
        ))
    if search_params.year_min:
        query = query.filter(models.Paper.year >= search_params.year_min)
    if search_params.year_max:
        query = query.filter(models.Paper.year <= search_params.year_max)
    if search_params.journal:
        query = query.filter(models.Paper.journal.like(f"%{search_params.journal}%"))
    if search_params.crystal_structure:
        query = query.filter(models.PaperData.crystal_structure.like(f"%{search_params.crystal_structure}%"))
    if search_params.review_status:
        query = query.filter(models.Paper.review_status == search_params.review_status)
    return query


def _apply_papers_sorting(query: Query, search_params: Optional[schemas.PaperSearchParams] = None) -> Query:
    sort_by = search_params.sort_by if search_params and search_params.sort_by else "year"
    sort_order = (search_params.sort_order if search_params and search_params.sort_order else "desc").lower()
    is_asc = sort_order == "asc"

    if sort_by == "created_at":
        primary = models.Paper.created_at.asc().nullslast() if is_asc else models.Paper.created_at.desc().nullslast()
    else:
        primary = models.Paper.year.asc().nullslast() if is_asc else models.Paper.year.desc().nullslast()

    secondary = models.Paper.id.asc() if is_asc else models.Paper.id.desc()
    return query.order_by(primary, secondary)


def get_papers_by_compound(db: Session, compound_id: int, search_params: Optional[schemas.PaperSearchParams] = None, is_admin: bool = False) -> List[models.Paper]:
    query = _build_papers_query(db, [compound_id], search_params)
    query = _apply_papers_sorting(query, search_params)
    if search_params:
        query = query.offset(search_params.offset).limit(search_params.limit)
    return query.all()


def get_papers_by_compounds(db: Session, compound_ids: List[int], search_params: Optional[schemas.PaperSearchParams] = None) -> List[models.Paper]:
    if not compound_ids:
        return []
    query = _build_papers_query(db, compound_ids, search_params)
    query = _apply_papers_sorting(query, search_params)
    if search_params:
        query = query.offset(search_params.offset).limit(search_params.limit)
    return query.all()


def get_papers_by_compounds_count(db: Session, compound_ids: List[int], search_params: Optional[schemas.PaperSearchParams] = None) -> int:
    if not compound_ids:
        return 0
    query = _build_papers_query(db, compound_ids, search_params)
    return query.with_entities(func.count(func.distinct(models.Paper.id))).scalar() or 0


def get_paper_by_id(db: Session, paper_id: int) -> Optional[models.Paper]:
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers_by_ids(db: Session, paper_ids: List[int]) -> List[models.Paper]:
    return db.query(models.Paper).filter(models.Paper.id.in_(paper_ids)).all()


def create_paper_image(image_db: Session, paper_id: int, image_data: bytes, thumbnail_data: bytes, image_order: int, file_size: int) -> models.PaperImage:
    image = models.PaperImage(
        paper_id=paper_id,
        image_data=image_data,
        thumbnail_data=thumbnail_data,
        image_order=image_order,
        file_size=file_size,
    )
    image_db.add(image)
    image_db.commit()
    image_db.refresh(image)
    return image


def get_paper_images(image_db: Session, paper_id: int) -> List[models.PaperImage]:
    return image_db.query(models.PaperImage).filter(models.PaperImage.paper_id == paper_id).all()


def get_image_by_id(image_db: Session, image_id: int) -> Optional[models.PaperImage]:
    if image_id >= 100:
        row_id, order = divmod(image_id, 100)
        row = image_db.query(models.PaperImage).filter(models.PaperImage.id == row_id).first()
        if row and 1 <= order <= 40 and getattr(row, f"fig{order}", None):
            setattr(row, "_selected_fig_order", order)
            return row
        return None
    return image_db.query(models.PaperImage).filter(models.PaperImage.id == image_id).first()


def get_image_by_order(image_db: Session, paper_id: int, image_order: int) -> Optional[models.PaperImage]:
    row = image_db.query(models.PaperImage).filter(models.PaperImage.paper_id == paper_id).first()
    if not row:
        return None
    if getattr(row, f"fig{image_order}", None):
        setattr(row, "_selected_fig_order", image_order)
        return row
    direct_row = image_db.query(models.PaperImage).filter(
        models.PaperImage.paper_id == paper_id,
        models.PaperImage.image_order == image_order,
    ).first()
    if direct_row:
        return direct_row
    return None


def get_paper_image_count(image_db: Session, paper_id: int) -> int:
    rows = get_paper_images(image_db, paper_id)
    count = 0
    for row in rows:
        direct_image_present = bool(row.image_data)
        if direct_image_present:
            count += 1
        fig_count = 0
        for i in range(1, 41):
            if getattr(row, f"fig{i}", None):
                fig_count += 1
        count += fig_count
    return count


def delete_all_paper_images(image_db: Session, paper_id: int) -> int:
    rows = get_paper_images(image_db, paper_id)
    deleted_count = get_paper_image_count(image_db, paper_id)
    for row in rows:
        image_db.delete(row)
    image_db.commit()
    return deleted_count


def get_total_papers_count(db: Session) -> int:
    return db.query(models.Paper).count()


def get_total_compounds_count(db: Session) -> int:
    return db.query(models.Compound).count()


def get_compound_papers_count(db: Session, compound_id: int) -> int:
    return db.query(models.Paper.id).join(models.PaperData).filter(models.PaperData.compound_id == compound_id).distinct().count()


def get_all_crystal_structures(db: Session) -> List[str]:
    results = db.query(models.PaperData.crystal_structure).filter(
        models.PaperData.crystal_structure.isnot(None),
        models.PaperData.crystal_structure != "",
    ).distinct().all()
    return sorted([r[0] for r in results if r[0]])


def paper_to_response(db: Session, paper: models.Paper, compound_id: Optional[int] = None, image_db: Optional[Session] = None) -> dict:
    points = paper.physical_parameters
    if compound_id is not None:
        points = [p for p in points if p.compound_id == compound_id]
    first = points[0] if points else None
    compound = first.compound if first and first.compound else None
    formula = first.chemical_formula if first else None
    structure = first.crystal_structure if first else None
    article_type = normalize_article_type(first.article_type) if first else None
    sc_type = normalize_superconductor_type(first.superconductor_type if first else None)
    image_count = get_paper_image_count(image_db, paper.id) if image_db is not None else 0

    return {
        "id": paper.id,
        "compound_id": compound.id if compound else None,
        "doi": paper.doi or "",
        "title": paper.title or "",
        "authors": authors_to_json(paper.authors),
        "journal": paper.journal,
        "volume": paper.volume,
        "pages": paper.pages,
        "year": paper.year,
        "abstract": paper.abstract,
        "citation_aps": None,
        "citation_bibtex": None,
        "article_type": article_type,
        "superconductor_type": sc_type,
        "chemical_formula": formula or (compound.chemical_formula if compound else None),
        "crystal_structure": structure,
        "contributor_name": paper.contributor_name,
        "contributor_affiliation": paper.contributor_affiliation,
        "notes": paper.notes or (first.data_source_note if first else None),
        "show_in_chart": bool(paper.show_in_chart),
        "created_at": paper.created_at,
        "image_count": image_count,
        "review_status": paper.review_status or "unreviewed",
        "review_comment": paper.review_comment,
        "reviewed_by": paper.reviewed_by,
        "reviewed_at": paper.reviewed_at,
        "reviewer_name": paper.reviewer.real_name if paper.reviewer else None,
        "compound_symbols": get_compound_key(compound) if compound else None,
        "sample_name": first.sample_name if first else None,
        "data_source_note": first.data_source_note if first else None,
        "data": [
            {
                "tc": d.tc_range,
                "tc_press": d.pressure_range,
                "lambda_val": d.lambda_val,
                "omega_log": d.omega_log,
                "n_ef": d.n_ef,
                "s_factor": d.s_factor,
                "article_type": normalize_article_type(d.article_type),
                "superconductor_type": normalize_superconductor_type(d.superconductor_type),
                "chemical_formula": d.chemical_formula,
                "crystal_structure": d.crystal_structure,
                "sample_name": d.sample_name,
                "data_source_note": d.data_source_note,
            }
            for d in points
        ],
    }


def authors_to_json(authors: Optional[str]) -> str:
    if not authors:
        return "[]"
    stripped = authors.strip()
    if stripped.startswith("["):
        return stripped
    parts = [p.strip() for p in re.split(r";|, and | and ", stripped) if p.strip()]
    return json.dumps(parts or [stripped], ensure_ascii=False)
