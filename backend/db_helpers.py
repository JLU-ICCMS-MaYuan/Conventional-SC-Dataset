import re
from decimal import Decimal, localcontext
from typing import Iterable


REVIEW_STATUSES = {"pending", "approved", "rejected"}
USER_ROLES = {"user", "admin", "superadmin"}
SEARCH_MODES = {
    "formula_search",
    "elements_exact_search",
    "elements_combination_search",
    "elements_contained_search",
}
VALID_ELEMENT_SYMBOLS = {
    "Ac", "Ag", "Al", "Am", "Ar", "As", "At", "Au", "B", "Ba", "Be", "Bh",
    "Bi", "Bk", "Br", "C", "Ca", "Cd", "Ce", "Cf", "Cl", "Cm", "Cn", "Co",
    "Cr", "Cs", "Cu", "Db", "Ds", "Dy", "Er", "Es", "Eu", "F", "Fe", "Fl",
    "Fm", "Fr", "Ga", "Gd", "Ge", "H", "He", "Hf", "Hg", "Ho", "Hs", "I",
    "In", "Ir", "K", "Kr", "La", "Li", "Lr", "Lu", "Lv", "Mc", "Md", "Mg",
    "Mn", "Mo", "Mt", "N", "Na", "Nb", "Nd", "Ne", "Nh", "Ni", "No", "Np",
    "O", "Og", "Os", "P", "Pa", "Pb", "Pd", "Pm", "Po", "Pr", "Pt", "Pu",
    "Ra", "Rb", "Re", "Rf", "Rg", "Rh", "Rn", "Ru", "S", "Sb", "Sc", "Se",
    "Sg", "Si", "Sm", "Sn", "Sr", "Ta", "Tb", "Tc", "Te", "Th", "Ti", "Tl",
    "Tm", "Ts", "U", "V", "W", "Xe", "Y", "Yb", "Zn", "Zr",
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

FORMULA_BRACKET_RE = re.compile(r"\([^()]*\)|（[^（）]*）|\[[^\[\]]*\]")
FORMULA_TOKEN_SPLIT_RE = re.compile(r"[^0-9A-Za-z]+")

# Tokens dropped as whole words by the loose fallback extractor: units and
# annotation words (case-sensitive). Matching whole tokens first is essential,
# e.g. "GPa" must never be scanned into the elements P / Pa / G.
FORMULA_NON_ELEMENT_TOKENS = {
    "GPa", "kbar", "bar", "atm", "Pa", "K", "eV", "meV", "T",
    "mol", "wt", "at", "system", "phase", "x",
}


def parse_formula_composition(formula: str) -> dict[str, Decimal]:
    if not formula or not formula.strip():
        raise ValueError("chemical formula is required")
    value = formula.strip()
    composition: dict[str, Decimal] = {}
    cursor = 0
    while cursor < len(value):
        match = FORMULA_TOKEN_RE.match(value, cursor)
        if not match:
            raise ValueError(f"invalid chemical formula: {formula}")
        symbol, amount_text = match.groups()
        if symbol not in VALID_ELEMENT_SYMBOLS:
            raise ValueError(f"unknown element symbol in formula: {symbol}")
        amount = Decimal(amount_text) if amount_text else Decimal("1")
        if amount <= 0:
            raise ValueError(f"invalid chemical formula amount: {formula}")
        if symbol in composition:
            with localcontext() as ctx:
                ctx.prec = max(50, len(value) + 10)
                composition[symbol] += amount
        else:
            composition[symbol] = amount
        cursor = match.end()
    if not composition:
        raise ValueError(f"invalid chemical formula: {formula}")
    return composition


def _is_integral_decimal(amount: Decimal) -> bool:
    exponent = amount.as_tuple().exponent
    if exponent >= 0:
        return True
    fractional_digits = amount.as_tuple().digits[exponent:]
    return all(digit == 0 for digit in fractional_digits)


def _format_formula_amount(amount: Decimal) -> str:
    if _is_integral_decimal(amount):
        return str(int(amount))
    return format(amount, "f").rstrip("0").rstrip(".")


def normalize_formula(formula: str) -> tuple[str, list[str], dict[str, Decimal], dict[str, Decimal]]:
    composition = parse_formula_composition(formula)
    elements = sorted(composition)
    normalized_parts = []
    with localcontext() as ctx:
        ctx.prec = max(50, sum(len(str(value)) for value in composition.values()) + 10)
        total = sum(composition.values(), Decimal("0"))
        ratios = {symbol: composition[symbol] / total for symbol in elements}
    if total <= 0:
        raise ValueError(f"invalid chemical formula total: {formula}")
    for symbol in elements:
        amount = composition[symbol]
        normalized_parts.append(symbol if amount == 1 else f"{symbol}{_format_formula_amount(amount)}")
    return "".join(normalized_parts), elements, composition, ratios


def extract_formula_elements_loose(formula: str) -> list[str]:
    """Fallback for normalize_formula: extract the element set from formulas
    containing variables (LaHx) or annotation text (units, system names)."""
    if not formula or not formula.strip():
        return []
    value = FORMULA_BRACKET_RE.sub(" ", formula)
    elements: set[str] = set()
    for token in FORMULA_TOKEN_SPLIT_RE.split(value):
        if not token or token in FORMULA_NON_ELEMENT_TOKENS:
            continue
        if len(token) == 1 and token.islower():
            continue
        # Prefer the two-letter symbol and fall back to the single letter, so a
        # trailing variable letter never swallows a valid element ("Hx" -> H).
        cursor = 0
        while cursor < len(token):
            if not token[cursor].isupper():
                cursor += 1
                continue
            pair = token[cursor : cursor + 2]
            if len(pair) == 2 and pair[1].islower() and pair in VALID_ELEMENT_SYMBOLS:
                elements.add(pair)
                cursor += 2
            else:
                if token[cursor] in VALID_ELEMENT_SYMBOLS:
                    elements.add(token[cursor])
                cursor += 1
    return sorted(elements)


def build_composition_key(composition: dict[str, Decimal]) -> str:
    """Build the stable, isotope-free composition identity used by the core schema."""
    return "|".join(
        f"{symbol}:{_format_formula_amount(composition[symbol])}"
        for symbol in sorted(composition)
    )
