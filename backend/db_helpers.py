import re
from typing import Iterable


REVIEW_STATUSES = {"pending", "approved", "rejected", "needs_revision"}
USER_ROLES = {"user", "admin", "superadmin"}
SEARCH_MODES = {
    "formula_search",
    "elements_exact_search",
    "elements_combination_search",
    "elements_contained_search",
}


def normalize_element_symbols(symbols: Iterable[str]) -> list[str]:
    cleaned = []
    for symbol in symbols:
        value = str(symbol).strip()
        if value:
            cleaned.append(value)
    return sorted(set(cleaned))


def build_system_key(symbols: Iterable[str]) -> tuple[str, list[str]]:
    normalized = normalize_element_symbols(symbols)
    return "-".join(normalized), normalized


def parse_formula_composition(formula: str) -> dict[str, int]:
    if not formula or not formula.strip():
        raise ValueError("chemical formula is required")
    matches = re.findall(r"([A-Z][a-z]?)(\d*)", formula.strip())
    if not matches:
        raise ValueError(f"invalid chemical formula: {formula}")
    composition: dict[str, int] = {}
    for symbol, amount in matches:
        composition[symbol] = composition.get(symbol, 0) + (int(amount) if amount else 1)
    return composition


def normalize_formula(formula: str) -> tuple[str, list[str], dict[str, int], dict[str, float]]:
    composition = parse_formula_composition(formula)
    elements = sorted(composition)
    normalized_parts = []
    total = sum(composition.values())
    for symbol in elements:
        amount = composition[symbol]
        normalized_parts.append(symbol if amount == 1 else f"{symbol}{amount}")
    ratios = {symbol: composition[symbol] / total for symbol in elements}
    return "".join(normalized_parts), elements, composition, ratios
