"""Extract deterministic crystal-structure candidates from searchable PDF text.

This parser intentionally handles only explicit lattice and coordinate tables. It
does not infer missing cells, coordinate systems, occupancies, or disorder.
"""

from __future__ import annotations

import re
from typing import Any

from ase import Atoms

from backend.services.structure_candidates import (
    StructureCandidateError,
    build_structure_candidate,
    serialize_atoms,
)


_NUMBER = r"[-+]?\d+(?:\.\d+)?"
_ELEMENT = r"[A-Z][a-z]?"
_PAGE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->")
_CELL_KEYS = {
    "a": ("_cell_length_a", "cell_length_a"),
    "b": ("_cell_length_b", "cell_length_b"),
    "c": ("_cell_length_c", "cell_length_c"),
    "alpha": ("_cell_angle_alpha", "cell_angle_alpha"),
    "beta": ("_cell_angle_beta", "cell_angle_beta"),
    "gamma": ("_cell_angle_gamma", "cell_angle_gamma"),
}


def _page_for_offset(text: str, offset: int) -> int | None:
    markers = list(_PAGE.finditer(text, 0, offset))
    return int(markers[-1].group(1)) if markers else None


def _cell_parameters(text: str) -> dict[str, float]:
    values: dict[str, float] = {}
    for key, aliases in _CELL_KEYS.items():
        alias_pattern = "|".join(re.escape(alias) for alias in aliases)
        match = re.search(rf"(?:{alias_pattern})\s*[=:]?\s*({_NUMBER})", text, re.IGNORECASE)
        if match:
            values[key] = float(match.group(1))
    # Common prose form: a = 3.5 Å, b = 3.5 Å ...
    for key in ("a", "b", "c", "alpha", "beta", "gamma"):
        if key in values:
            continue
        match = re.search(rf"\b{key}\s*[=:]\s*({_NUMBER})", text, re.IGNORECASE)
        if match:
            values[key] = float(match.group(1))
    return values


def _coordinate_mode(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"fractional|frac(?:tional)?\s+coordinates?|crystallographic", lowered):
        return "fractional"
    if re.search(r"cartesian|cart\.?\s+coordinates?", lowered):
        return "cartesian"
    return None


def _coordinate_rows(text: str, mode: str) -> tuple[list[str], list[tuple[float, float, float]], str] :
    symbols: list[str] = []
    positions: list[tuple[float, float, float]] = []
    rows: list[str] = []
    pattern = re.compile(
        rf"^\s*(?:\d+\s+)?({_ELEMENT})(?:\d+|[A-Za-z]{{0,3}})?\s+(?:({_ELEMENT})\s+)?"
        rf"({_NUMBER})\s+({_NUMBER})\s+({_NUMBER})(?:\s|$)"
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if not match:
            continue
        symbol = match.group(2) or match.group(1)
        symbols.append(symbol)
        positions.append(tuple(float(match.group(index)) for index in (3, 4, 5)))
        rows.append(line.strip())
    return symbols, positions, "\n".join(rows)


def _blocked_candidate(source: dict[str, Any], reason: str, *, page: int | None, quote: str) -> dict[str, Any]:
    file_id = source.get("file_id") or source.get("filename") or "pdf"
    return {
        "candidate_id": f"blocked:pdf:{file_id}:{page or 0}",
        "material_state_ref": f"unassigned:{file_id}",
        "source_kind": "pdf_reported",
        "status": "blocked",
        "confirmation": "unreviewed",
        "original_format": None,
        "original_text": None,
        "validation": {"ase_valid": False, "code": "pdf_structure_incomplete", "message": reason},
        "derivation": None,
        "representations": {},
        "sources": [{**source, "page": page, "quote": quote}],
        "conflicts": [],
        "user_note": None,
    }


def _extract_structure_candidate_block(
    markdown: str,
    *,
    source: dict[str, Any],
    material_state_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Extract explicit coordinate-table candidates while preserving page evidence."""
    text = str(markdown or "")
    if not text.strip():
        return []
    cues = re.search(r"cell_length|lattice\s+parameter|space\s+group|atomic\s+coordinates?|fractional\s+coordinates?|cartesian\s+coordinates?", text, re.IGNORECASE)
    if not cues:
        return []
    cells = _cell_parameters(text)
    mode = _coordinate_mode(text)
    if len(cells) < 6:
        return [_blocked_candidate(source, "PDF 结构缺少完整晶胞参数（a、b、c、alpha、beta、gamma）", page=_page_for_offset(text, cues.start()), quote=text[max(0, cues.start() - 160):cues.end() + 320])]
    if mode is None:
        return [_blocked_candidate(source, "PDF 原子坐标类型不明确，无法区分分数坐标和笛卡尔坐标", page=_page_for_offset(text, cues.start()), quote=text[max(0, cues.start() - 160):cues.end() + 320])]
    symbols, positions, quote = _coordinate_rows(text, mode)
    if not symbols:
        return [_blocked_candidate(source, "PDF 未找到完整原子坐标行，不能仅凭空间群生成结构", page=_page_for_offset(text, cues.start()), quote=text[max(0, cues.start() - 160):cues.end() + 320])]
    cell = [cells[key] for key in ("a", "b", "c", "alpha", "beta", "gamma")]
    atoms = Atoms(symbols=symbols, positions=positions if mode == "cartesian" else None,
                  scaled_positions=positions if mode == "fractional" else None,
                  cell=cell, pbc=True)
    try:
        original = build_structure_candidate(
            structure_format="cif",
            structure_text=serialize_atoms(atoms, "cif"),
            source={**source, "page": _page_for_offset(text, cues.start()), "quote": quote},
            material_state_ref=material_state_ref or f"unassigned:{source.get('file_id') or 'pdf'}",
            source_kind="pdf_reported",
        )
    except StructureCandidateError as exc:
        return [_blocked_candidate(source, str(exc), page=_page_for_offset(text, cues.start()), quote=quote)]
    original["original_format"] = None
    original["original_text"] = None
    original["reported_structure"] = {"coordinate_mode": mode, "cell_parameters": cells, "coordinate_rows": quote}
    original["derivation"] = {"kind": "direct_coordinates", "label": "原文直接报告"}
    return [original]


def extract_structure_candidates(
    markdown: str,
    *,
    source: dict[str, Any],
    material_state_ref: str | None = None,
) -> list[dict[str, Any]]:
    """Extract one candidate per explicit page block to avoid merging conditions."""
    text = str(markdown or "")
    if not text.strip():
        return []
    blocks = re.split(r"(?=<!--\s*page:\s*\d+\s*-->)", text, flags=re.IGNORECASE)
    if len(blocks) == 1:
        blocks = [text]
    candidates: list[dict[str, Any]] = []
    for block in blocks:
        candidates.extend(_extract_structure_candidate_block(
            block,
            source=source,
            material_state_ref=material_state_ref,
        ))
    return candidates
