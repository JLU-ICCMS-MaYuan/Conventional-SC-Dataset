"""Deterministic material and structure classification helpers."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
import unicodedata
from typing import Any, Mapping

from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload

from backend import models
from backend.db_helpers import normalize_formula


MATERIAL_DIMENSIONALITIES = {
    "zero_dimensional": "零维",
    "one_dimensional": "一维",
    "two_dimensional": "二维",
    "three_dimensional": "三维",
    "quasi_one_dimensional": "准一维",
    "quasi_two_dimensional": "准二维",
    "unknown": "未知",
}


@dataclass(frozen=True)
class SeedFamilyMatch:
    code: str
    name: str
    matched_by: str


MATERIAL_FAMILY_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "code": "hydrogen_based",
        "name_zh": "氢基超导体",
        "name_en": "Hydrogen-based superconductor",
        "aliases": ("hydrogen_based", "hydride", "氢化物", "高压氢化物", "hydrogen-rich superconductor"),
    },
    {
        "code": "copper_based",
        "name_zh": "铜基超导体",
        "name_en": "Copper-based superconductor",
        "aliases": ("copper_based", "cuprate", "铜氧化物超导体", "铜基"),
    },
    {
        "code": "iron_based",
        "name_zh": "铁基超导体",
        "name_en": "Iron-based superconductor",
        "aliases": ("iron_based", "iron based", "铁基"),
    },
    {
        "code": "nickel_based",
        "name_zh": "镍基超导体",
        "name_en": "Nickel-based superconductor",
        "aliases": ("nickel_based", "nickelate", "镍基"),
    },
    {
        "code": "inorganic_bcn_based",
        "name_zh": "无机硼碳氮基超导体",
        "name_en": "Inorganic boron-carbon-nitrogen-based superconductor",
        "aliases": ("inorganic_bcn_based", "无机硼碳氮基超导", "inorganic bcn based"),
    },
    {
        "code": "organic",
        "name_zh": "有机超导体",
        "name_en": "Organic superconductor",
        "aliases": ("organic", "organic superconductor", "有机超导"),
    },
    {
        "code": "heavy_fermion",
        "name_zh": "重费米子超导体",
        "name_en": "Heavy-fermion superconductor",
        "aliases": ("heavy_fermion", "heavy fermion", "heavy-fermion superconductor", "重费米子超导"),
    },
)


def normalize_classification_name(value: Any) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip().casefold()
    normalized = re.sub(r"[_\-]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized)


def resolve_seed_material_family(value: Any) -> SeedFamilyMatch | None:
    candidate = normalize_classification_name(value)
    if not candidate or candidate in {"carbon", "others"}:
        return None
    for seed in MATERIAL_FAMILY_SEEDS:
        names = (seed["code"], seed["name_zh"], seed["name_en"], *seed["aliases"])
        for name in names:
            if normalize_classification_name(name) == candidate:
                return SeedFamilyMatch(
                    code=str(seed["code"]),
                    name=str(seed["name_zh"]),
                    matched_by=str(name),
                )
    return None


def count_formula_elements(formula: Any) -> int | None:
    try:
        _normalized, elements, _composition, _ratios = normalize_formula(str(formula or ""))
    except (TypeError, ValueError):
        return None
    return len(elements) or None


def _pending_selection(raw_value: Any) -> dict[str, Any] | None:
    name = str(raw_value or "").strip()
    if not name:
        return None
    return {"id": None, "name": name, "status": "pending"}


def convert_legacy_draft(
    draft: Mapping[str, Any],
    *,
    families_by_code: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    """Convert an old top-level sc_type without preserving the legacy field."""
    converted = deepcopy(dict(draft))
    raw_value = converted.pop("sc_type", None)
    converted.pop("sc_type_review_status", None)
    states = converted.get("material_states")
    if not isinstance(states, list):
        states = []
        converted["material_states"] = states
    if raw_value in (None, ""):
        return converted

    seed_match = resolve_seed_material_family(raw_value)
    selection = None
    if seed_match:
        family = families_by_code.get(seed_match.code)
        if family:
            selection = {
                "id": int(family["id"]),
                "name": str(family.get("name") or seed_match.name),
                "status": "confirmed",
            }
    if selection is None:
        selection = _pending_selection(raw_value)

    for state in states:
        if isinstance(state, dict) and not state.get("material_family"):
            state["material_family"] = deepcopy(selection)
    warnings = list(converted.get("classification_migration_warnings") or [])
    warnings.append("旧材料类型已转换；保存后将只保留材料状态级分类。")
    converted["classification_migration_warnings"] = warnings
    return converted


async def load_active_catalogs(session) -> dict[str, Any]:
    material_result = await session.execute(
        select(models.MaterialFamily)
        .where(models.MaterialFamily.is_active.is_(True))
        .options(selectinload(models.MaterialFamily.aliases))
        .order_by(models.MaterialFamily.id)
    )
    structure_result = await session.execute(
        select(models.StructureFamily)
        .where(models.StructureFamily.is_active.is_(True))
        .options(selectinload(models.StructureFamily.aliases))
        .order_by(models.StructureFamily.id)
    )

    def serialize(term) -> dict[str, Any]:
        return {
            "id": term.id,
            "name": term.name_zh,
            "aliases": sorted({alias.alias for alias in term.aliases}),
        }

    return {
        "material_families": [serialize(item) for item in material_result.scalars().all()],
        "structure_families": [serialize(item) for item in structure_result.scalars().all()],
        "material_dimensionalities": [
            {"value": value, "name": name}
            for value, name in MATERIAL_DIMENSIONALITIES.items()
        ],
    }


async def resolve_material_family(session, value: Any):
    normalized = normalize_classification_name(value)
    if not normalized:
        return None
    result = await session.execute(
        select(models.MaterialFamily)
        .outerjoin(models.MaterialFamilyAlias)
        .where(
            models.MaterialFamily.is_active.is_(True),
            or_(
                models.MaterialFamily.normalized_name == normalized,
                models.MaterialFamily.code == normalized.replace(" ", "_"),
                models.MaterialFamilyAlias.normalized_alias == normalized,
            ),
        )
        .distinct()
    )
    return result.scalar_one_or_none()


async def resolve_structure_family(session, value: Any):
    normalized = normalize_classification_name(value)
    if not normalized:
        return None
    result = await session.execute(
        select(models.StructureFamily)
        .outerjoin(models.StructureFamilyAlias)
        .where(
            models.StructureFamily.is_active.is_(True),
            or_(
                models.StructureFamily.normalized_name == normalized,
                models.StructureFamily.code == normalized.replace(" ", "_"),
                models.StructureFamilyAlias.normalized_alias == normalized,
            ),
        )
        .distinct()
    )
    return result.scalar_one_or_none()
