"""Read-only space group symbol table built from spglib at import time."""

from __future__ import annotations

from typing import Any

import spglib


def _build_table() -> list[dict[str, Any]]:
    by_number: dict[int, str] = {}
    for hall_number in range(1, 531):
        info = spglib.get_spacegroup_type(hall_number)
        # spglib 2.x names the short Hermann–Mauguin symbol ``international_short``;
        # ``international`` is the spaced full form (e.g. "F m -3 m").
        by_number.setdefault(info.number, info.international_short)
    return [
        {"number": number, "symbol": by_number[number]}
        for number in sorted(by_number)
    ]


_SPACE_GROUPS = _build_table()
_SYMBOL_TO_NUMBER = {entry["symbol"]: entry["number"] for entry in _SPACE_GROUPS}


def all_space_groups() -> list[dict[str, Any]]:
    """Return the 230 space groups as {"number", "symbol"} dicts ordered by number."""
    return [dict(entry) for entry in _SPACE_GROUPS]


def lookup_number(symbol: str) -> int | None:
    """Return the space group number for an exact international symbol, else None."""
    return _SYMBOL_TO_NUMBER.get(str(symbol or "").strip())


# Crystal system ranges are fixed crystallographic facts, so they live as a
# static table instead of being derived from spglib.
_CRYSTAL_SYSTEM_RANGES = {
    "triclinic": range(1, 3),
    "monoclinic": range(3, 16),
    "orthorhombic": range(16, 75),
    "tetragonal": range(75, 143),
    "trigonal": range(143, 168),
    "hexagonal": range(168, 195),
    "cubic": range(195, 231),
}

# Whitelist matching the material_states.crystal_system CHECK constraint.
CRYSTAL_SYSTEMS = tuple(_CRYSTAL_SYSTEM_RANGES) + ("unknown",)


def crystal_system_for_number(number: Any) -> str | None:
    """Return the crystal system name for a 1–230 space group number, else None."""
    try:
        n = int(number)
    except (TypeError, ValueError):
        return None
    for system, numbers in _CRYSTAL_SYSTEM_RANGES.items():
        if n in numbers:
            return system
    return None


def numbers_for_crystal_system(system: str) -> range | None:
    """Return the space group number range for a crystal system name, else None."""
    key = str(system or "").strip().lower()
    return _CRYSTAL_SYSTEM_RANGES.get(key)
