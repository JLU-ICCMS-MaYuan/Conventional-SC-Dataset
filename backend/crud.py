"""
Small data-access helpers for the redesigned MySQL schema.
"""

from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy.orm import Session

from backend import models
from backend.db_helpers import build_system_key, normalize_formula


def _json_number(value: Decimal) -> int | float:
    if value == value.to_integral_value():
        return int(value)
    return float(value)


def _json_decimal_mapping(values: dict[str, Decimal]) -> dict[str, int | float]:
    return {key: _json_number(value) for key, value in values.items()}


def get_or_create_chemical_system(db: Session, elements: Iterable[str]) -> models.ChemicalSystem:
    system_key, elements_list = build_system_key(elements)
    system = db.query(models.ChemicalSystem).filter_by(system_key=system_key).first()
    if system:
        return system

    system = models.ChemicalSystem(
        system_key=system_key,
        elements_list=elements_list,
        element_count=len(elements_list),
    )
    db.add(system)
    db.flush()
    return system


def get_or_create_superconductor(db: Session, chemical_formula: str) -> models.Superconductor:
    normalized, elements, composition, ratios = normalize_formula(chemical_formula)
    existing = db.query(models.Superconductor).filter_by(formula_normalized=normalized).first()
    if existing:
        return existing

    system = get_or_create_chemical_system(db, elements)
    superconductor = models.Superconductor(
        chemical_system_id=system.id,
        chemical_formula=chemical_formula,
        formula_normalized=normalized,
        display_name=chemical_formula,
        elements_list=elements,
        composition=_json_decimal_mapping(composition),
        element_ratio=_json_decimal_mapping(ratios),
    )
    db.add(superconductor)
    db.flush()
    return superconductor


def get_paper_by_id(db: Session, paper_id: int) -> models.Paper | None:
    return db.query(models.Paper).filter(models.Paper.id == paper_id).first()


def get_papers_by_ids(db: Session, paper_ids: list[int]) -> list[models.Paper]:
    if not paper_ids:
        return []
    return db.query(models.Paper).filter(models.Paper.id.in_(paper_ids)).all()


def authors_to_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return [str(value)]
