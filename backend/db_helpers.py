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


FORMULA_TOKEN_RE = re.compile(r"([A-Z][a-z]?)(\d+(?:\.\d+)?)?")


def parse_formula_composition(formula: str) -> dict[str, float]:
    if not formula or not formula.strip():
        raise ValueError("chemical formula is required")
    value = formula.strip()
    composition: dict[str, float] = {}
    cursor = 0
    while cursor < len(value):
        match = FORMULA_TOKEN_RE.match(value, cursor)
        if not match:
            raise ValueError(f"invalid chemical formula: {formula}")
        symbol, amount_text = match.groups()
        amount = float(amount_text) if amount_text else 1.0
        if amount <= 0:
            raise ValueError(f"invalid chemical formula amount: {formula}")
        composition[symbol] = composition.get(symbol, 0.0) + amount
        cursor = match.end()
    if not composition:
        raise ValueError(f"invalid chemical formula: {formula}")
    return composition


def _format_formula_amount(amount: float) -> str:
    if amount.is_integer():
        return str(int(amount))
    return f"{amount:g}"


def normalize_formula(formula: str) -> tuple[str, list[str], dict[str, float], dict[str, float]]:
    composition = parse_formula_composition(formula)
    elements = sorted(composition)
    normalized_parts = []
    total = sum(composition.values())
    if total <= 0:
        raise ValueError(f"invalid chemical formula total: {formula}")
    for symbol in elements:
        amount = composition[symbol]
        normalized_parts.append(symbol if amount == 1 else f"{symbol}{_format_formula_amount(amount)}")
    ratios = {symbol: composition[symbol] / total for symbol in elements}
    return "".join(normalized_parts), elements, composition, ratios
