"""
数据库CRUD与新旧前端兼容转换。
"""
import json
import math
import re
from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

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


def search_compounds_by_elements(db: Session, element_symbols: List[str], mode: str) -> List[dict]:
    allowed_modes = {"only", "combination", "contains"}
    mode = mode if mode in allowed_modes else "combination"
    selection = set(element_symbols)
    matched: List[dict] = []

    for compound in db.query(models.Compound).all():
        symbols = set(get_compound_element_list(compound))
        if not symbols:
            continue
        if mode == "only":
            ok = symbols == selection
        elif mode == "combination":
            ok = symbols.issubset(selection)
        else:
            ok = selection.issubset(symbols)
        if ok:
            matched.append({
                "id": compound.id,
                "element_symbols": get_compound_key(compound),
                "element_list": get_compound_element_list(compound),
                "paper_count": get_compound_papers_count(db, compound.id),
            })

    matched.sort(key=lambda item: (len(item["element_list"]), item["element_symbols"]))
    return matched


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
        pressure_val = item.get("pressure")
        tc_val = item.get("tc")
        s_factor_val = item.get("s_factor")
        if s_factor_val is None:
            s_factor_val = compute_s_factor(pressure_val, tc_val)
        db_data = models.PaperData(
            paper_id=paper_id,
            compound_id=compound_id or item.get("compound_id"),
            article_type=to_storage_article_type(item.get("article_type")),
            superconductor_type=to_storage_superconductor_type(item.get("superconductor_type")),
            chemical_formula=item.get("chemical_formula"),
            crystal_structure=item.get("crystal_structure"),
            tc_press=json.dumps([tc_val, pressure_val], ensure_ascii=False),
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


def get_papers_by_compound(db: Session, compound_id: int, search_params: Optional[schemas.PaperSearchParams] = None, is_admin: bool = False) -> List[models.Paper]:
    query = db.query(models.Paper).join(models.PaperData).filter(models.PaperData.compound_id == compound_id).distinct()
    if search_params:
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
        query = query.order_by(models.Paper.year.desc().nullslast(), models.Paper.id.desc())
        query = query.offset(search_params.offset).limit(search_params.limit)
        return query.all()
    return query.order_by(models.Paper.year.desc().nullslast(), models.Paper.id.desc()).all()


def get_paper_by_id(db: Session, paper_id: int) -> Optional[models.Paper]:
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers_by_ids(db: Session, paper_ids: List[int]) -> List[models.Paper]:
    return db.query(models.Paper).filter(models.Paper.id.in_(paper_ids)).all()


def create_paper_image(db: Session, paper_id: int, image_data: bytes, thumbnail_data: bytes, image_order: int, file_size: int) -> models.PaperImage:
    image = models.PaperImage(
        paper_id=paper_id,
        image_data=image_data,
        thumbnail_data=thumbnail_data,
        image_order=image_order,
        file_size=file_size,
    )
    db.add(image)
    db.commit()
    db.refresh(image)
    return image


def get_paper_images(db: Session, paper_id: int) -> List[models.PaperImage]:
    return db.query(models.PaperImage).filter(models.PaperImage.paper_id == paper_id).all()


def get_image_by_id(db: Session, image_id: int) -> Optional[models.PaperImage]:
    if image_id >= 100:
        row_id, order = divmod(image_id, 100)
        row = db.query(models.PaperImage).filter(models.PaperImage.id == row_id).first()
        if row and 1 <= order <= 40 and getattr(row, f"fig{order}", None):
            setattr(row, "_selected_fig_order", order)
            return row
        return None
    return db.query(models.PaperImage).filter(models.PaperImage.id == image_id).first()


def get_image_by_order(db: Session, paper_id: int, image_order: int) -> Optional[models.PaperImage]:
    row = db.query(models.PaperImage).filter(models.PaperImage.paper_id == paper_id).first()
    if not row:
        return None
    if getattr(row, f"fig{image_order}", None):
        setattr(row, "_selected_fig_order", image_order)
        return row
    return None


def get_paper_image_count(db: Session, paper_id: int) -> int:
    rows = get_paper_images(db, paper_id)
    count = 0
    for row in rows:
        for i in range(1, 41):
            if getattr(row, f"fig{i}", None):
                count += 1
    return count


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


def paper_to_response(db: Session, paper: models.Paper, compound_id: Optional[int] = None) -> dict:
    points = paper.physical_parameters
    if compound_id is not None:
        points = [p for p in points if p.compound_id == compound_id]
    first = points[0] if points else None
    compound = first.compound if first and first.compound else None
    formula = first.chemical_formula if first else None
    structure = first.crystal_structure if first else None
    article_type = normalize_article_type(first.article_type) if first else None
    sc_type = normalize_superconductor_type(first.superconductor_type if first else None)

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
        "image_count": get_paper_image_count(db, paper.id),
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
                "pressure": d.pressure,
                "tc": d.tc,
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
