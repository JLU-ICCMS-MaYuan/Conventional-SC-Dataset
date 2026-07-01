from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend import models
from backend.db_helpers import build_system_key, normalize_element_symbols, normalize_formula


@dataclass
class SuperconductorSearchResult:
    items: list[models.Superconductor]
    total: int
    page: int
    page_size: int
    has_prev: bool
    has_next: bool


def _paginate(items: list[models.Superconductor], limit: int, offset: int) -> SuperconductorSearchResult:
    total = len(items)
    page_items = items[offset: offset + limit]
    page_size = limit
    page = (offset // page_size) + 1 if page_size else 1
    return SuperconductorSearchResult(
        items=page_items,
        total=total,
        page=page,
        page_size=page_size,
        has_prev=offset > 0,
        has_next=offset + limit < total,
    )


def search_superconductors(
    db: Session,
    mode: str,
    *,
    formula: str | None = None,
    elements: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> SuperconductorSearchResult:
    query = db.query(models.Superconductor).join(models.ChemicalSystem)

    if mode == "formula_search":
        if not formula:
            return _paginate([], limit, offset)
        normalized, _, _, _ = normalize_formula(formula)
        items = query.filter(models.Superconductor.formula_normalized == normalized).all()
        return _paginate(items, limit, offset)

    normalized_elements = normalize_element_symbols(elements or [])
    if not normalized_elements:
        return _paginate([], limit, offset)

    if mode == "elements_exact_search":
        system_key, _ = build_system_key(normalized_elements)
        items = query.filter(models.ChemicalSystem.system_key == system_key).all()
        return _paginate(items, limit, offset)

    all_items = query.all()
    selection = set(normalized_elements)
    if mode == "elements_combination_search":
        matched = [item for item in all_items if set(item.elements_list).issubset(selection)]
    elif mode == "elements_contained_search":
        matched = [item for item in all_items if selection.issubset(set(item.elements_list))]
    else:
        matched = []

    matched.sort(key=lambda item: (len(item.elements_list), item.formula_normalized))
    return _paginate(matched, limit, offset)
