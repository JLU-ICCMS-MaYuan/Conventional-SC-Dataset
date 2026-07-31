from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, localcontext
from math import inf
from typing import Iterable

from backend.db_helpers import VALID_ELEMENT_SYMBOLS, normalize_formula


_VARIABLE_RE = re.compile(r"(delta|[dxyz]|δ)", re.IGNORECASE)
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?(?:/\d+(?:\.\d+)?)?")


@dataclass(frozen=True)
class AmountConstraint:
    nominal: Decimal | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    variable: bool = False

    @property
    def fixed(self) -> bool:
        return self.nominal is not None and not self.variable and self.min_value is None and self.max_value is None


@dataclass(frozen=True)
class ParsedFormulaExpression:
    raw: str
    elements: list[str]
    amounts: dict[str, AmountConstraint]
    normalized_formula: str | None


class FormulaExpressionError(ValueError):
    pass


def _clean_formula(value: str) -> str:
    return (
        value.strip()
        .replace(" ", "")
        .replace("−", "-")
        .replace("–", "-")
        .replace("—", "-")
        .replace("·", "")
    )


def _decimal(text: str) -> Decimal:
    if "/" in text:
        numerator, denominator = text.split("/", 1)
        denominator_value = Decimal(denominator)
        if denominator_value == 0:
            raise FormulaExpressionError("formula fraction denominator cannot be zero")
        with localcontext() as ctx:
            ctx.prec = max(50, len(text) + 10)
            return Decimal(numerator) / denominator_value
    return Decimal(text)


def _add_amount(a: AmountConstraint, b: AmountConstraint) -> AmountConstraint:
    nominal = None
    if a.nominal is not None and b.nominal is not None:
        nominal = a.nominal + b.nominal
    return AmountConstraint(
        nominal=nominal,
        min_value=(a.min_value + b.min_value) if a.min_value is not None and b.min_value is not None else None,
        max_value=(a.max_value + b.max_value) if a.max_value is not None and b.max_value is not None else None,
        variable=a.variable or b.variable,
    )


def _multiply_amount(amount: AmountConstraint, multiplier: AmountConstraint) -> AmountConstraint:
    if multiplier.nominal is None:
        return AmountConstraint(variable=True)
    nominal = amount.nominal * multiplier.nominal if amount.nominal is not None else None
    min_value = amount.min_value * multiplier.nominal if amount.min_value is not None else None
    max_value = amount.max_value * multiplier.nominal if amount.max_value is not None else None
    return AmountConstraint(
        nominal=nominal,
        min_value=min_value,
        max_value=max_value,
        variable=amount.variable or multiplier.variable,
    )


def _merge_amounts(
    left: dict[str, AmountConstraint],
    right: dict[str, AmountConstraint],
) -> dict[str, AmountConstraint]:
    merged = dict(left)
    for symbol, amount in right.items():
        merged[symbol] = _add_amount(merged[symbol], amount) if symbol in merged else amount
    return merged


def _scale_amounts(amounts: dict[str, AmountConstraint], multiplier: AmountConstraint) -> dict[str, AmountConstraint]:
    return {symbol: _multiply_amount(amount, multiplier) for symbol, amount in amounts.items()}


def _matching_paren(value: str, start: int) -> int:
    depth = 0
    for index in range(start, len(value)):
        if value[index] == "(":
            depth += 1
        elif value[index] == ")":
            depth -= 1
            if depth == 0:
                return index
    raise FormulaExpressionError("unclosed parenthesis in formula")


def _looks_like_formula_group(value: str, open_index: int) -> bool:
    close_index = _matching_paren(value, open_index)
    return any(ch.isupper() for ch in value[open_index + 1:close_index])


def _parse_amount_text(text: str | None) -> AmountConstraint:
    if not text:
        return AmountConstraint(nominal=Decimal("1"))

    value = text.strip()
    if value.startswith("(") and value.endswith(")") and _matching_paren(value, 0) == len(value) - 1:
        value = value[1:-1]

    range_match = re.fullmatch(rf"({_NUMBER_RE.pattern})~({_NUMBER_RE.pattern})", value)
    if range_match:
        low = _decimal(range_match.group(1))
        high = _decimal(range_match.group(2))
        if low > high:
            low, high = high, low
        return AmountConstraint(nominal=(low + high) / Decimal("2"), min_value=low, max_value=high, variable=True)

    plus_minus_match = re.fullmatch(rf"({_NUMBER_RE.pattern})±(.+)", value)
    if plus_minus_match:
        nominal = _decimal(plus_minus_match.group(1))
        return AmountConstraint(nominal=nominal, variable=True)

    if _VARIABLE_RE.search(value):
        numbers = [_decimal(match.group(0)) for match in _NUMBER_RE.finditer(value)]
        lower_value = value.lower()
        nominal = None
        if numbers and ("delta" in lower_value or "δ" in value or re.search(r"\bd\b", lower_value)):
            nominal = numbers[0]
        return AmountConstraint(nominal=nominal, variable=True)

    try:
        amount = _decimal(value)
    except Exception as exc:
        raise FormulaExpressionError(f"invalid formula amount: {text}") from exc
    if amount <= 0:
        raise FormulaExpressionError(f"invalid formula amount: {text}")
    return AmountConstraint(nominal=amount)


def _read_amount(value: str, index: int) -> tuple[AmountConstraint, int]:
    if index >= len(value):
        return AmountConstraint(nominal=Decimal("1")), index
    if value[index] == "(":
        if _looks_like_formula_group(value, index):
            return AmountConstraint(nominal=Decimal("1")), index
        close_index = _matching_paren(value, index)
        return _parse_amount_text(value[index:close_index + 1]), close_index + 1

    start = index
    while index < len(value):
        ch = value[index]
        if ch.isupper() or ch == ")":
            break
        if ch == "(":
            break
        index += 1
    if start == index:
        return AmountConstraint(nominal=Decimal("1")), index
    return _parse_amount_text(value[start:index]), index


def _read_element(value: str, index: int) -> tuple[str, int]:
    if index >= len(value) or not value[index].isupper():
        raise FormulaExpressionError(f"expected element at position {index + 1}")
    if index + 1 < len(value) and value[index + 1].islower():
        two = value[index:index + 2]
        if two in VALID_ELEMENT_SYMBOLS:
            return two, index + 2
    one = value[index]
    if one in VALID_ELEMENT_SYMBOLS:
        return one, index + 1
    raise FormulaExpressionError(f"unknown element symbol near position {index + 1}")


def _parse_sequence(value: str, index: int = 0) -> tuple[dict[str, AmountConstraint], int]:
    amounts: dict[str, AmountConstraint] = {}
    while index < len(value) and value[index] != ")":
        if value[index] == "(":
            close_index = _matching_paren(value, index)
            inner, end_index = _parse_sequence(value, index + 1)
            if end_index != close_index:
                raise FormulaExpressionError("invalid parenthesized formula group")
            multiplier, index = _read_amount(value, close_index + 1)
            amounts = _merge_amounts(amounts, _scale_amounts(inner, multiplier))
            continue

        symbol, index = _read_element(value, index)
        amount, index = _read_amount(value, index)
        amounts = _merge_amounts(amounts, {symbol: amount})

    return amounts, index


def parse_formula_expression(formula: str) -> ParsedFormulaExpression:
    if not formula or not formula.strip():
        raise FormulaExpressionError("formula is required")

    cleaned = _clean_formula(formula)
    amounts, index = _parse_sequence(cleaned)
    if index != len(cleaned):
        if cleaned[index] == ")":
            raise FormulaExpressionError("unmatched closing parenthesis in formula")
        raise FormulaExpressionError(f"invalid formula near position {index + 1}")
    if not amounts:
        raise FormulaExpressionError("formula contains no elements")

    normalized_formula = None
    try:
        normalized_formula = normalize_formula(_fractionless_formula(cleaned))[0]
    except Exception:
        normalized_formula = None

    return ParsedFormulaExpression(
        raw=formula,
        elements=sorted(amounts),
        amounts=amounts,
        normalized_formula=normalized_formula,
    )


def _fractionless_formula(formula: str) -> str:
    return re.sub(r"\d+(?:\.\d+)?/\d+(?:\.\d+)?", lambda m: str(_decimal(m.group(0))), formula)


def _as_decimal(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _composition(item) -> dict[str, Decimal]:
    values = {}
    for symbol, amount in (item.composition or {}).items():
        decimal_amount = _as_decimal(amount)
        if decimal_amount is not None:
            values[symbol] = decimal_amount
    return values


def _ratio_distance(query: ParsedFormulaExpression, composition: dict[str, Decimal]) -> float:
    fixed_symbols = [symbol for symbol, amount in query.amounts.items() if amount.fixed]
    if len(fixed_symbols) >= 2:
        query_total = sum(query.amounts[symbol].nominal for symbol in fixed_symbols if query.amounts[symbol].nominal is not None)
        candidate_total = sum(composition.get(symbol, Decimal("0")) for symbol in fixed_symbols)
        if query_total and candidate_total:
            return float(sum(
                abs(
                    (query.amounts[symbol].nominal or Decimal("0")) / query_total
                    - composition.get(symbol, Decimal("0")) / candidate_total
                )
                for symbol in fixed_symbols
            ))

    nominal_symbols = [symbol for symbol, amount in query.amounts.items() if amount.nominal is not None]
    if len(nominal_symbols) >= 2:
        query_total = sum(query.amounts[symbol].nominal for symbol in nominal_symbols if query.amounts[symbol].nominal is not None)
        candidate_total = sum(composition.get(symbol, Decimal("0")) for symbol in nominal_symbols)
        if query_total and candidate_total:
            return float(sum(
                abs(
                    (query.amounts[symbol].nominal or Decimal("0")) / query_total
                    - composition.get(symbol, Decimal("0")) / candidate_total
                )
                for symbol in nominal_symbols
            ))

    return 0.0


def _range_penalty(query: ParsedFormulaExpression, composition: dict[str, Decimal]) -> float:
    penalty = 0.0
    for symbol, amount in query.amounts.items():
        candidate = composition.get(symbol)
        if candidate is None:
            continue
        if amount.min_value is not None and candidate < amount.min_value:
            penalty += float(amount.min_value - candidate)
        if amount.max_value is not None and candidate > amount.max_value:
            penalty += float(candidate - amount.max_value)
    return penalty


def formula_relevance_key(query: ParsedFormulaExpression, item) -> tuple[float, float, str]:
    composition = _composition(item)
    if not composition:
        return (inf, inf, item.formula_normalized or item.chemical_formula)

    if query.normalized_formula and item.formula_normalized == query.normalized_formula:
        return (0.0, 0.0, item.formula_normalized or item.chemical_formula)

    distance = _ratio_distance(query, composition)
    range_penalty = _range_penalty(query, composition)
    tier = 1.0 if distance == 0 and range_penalty == 0 else 2.0
    return (tier + range_penalty, distance, item.formula_normalized or item.chemical_formula)


def max_record_tc(item) -> float | None:
    values = []
    for record in getattr(item, "records", []) or []:
        values.extend([
            record.experimental_tc,
            record.anisotropic_eliashberg_tc,
            record.isotropic_eliashberg_tc,
            record.allen_dynes_tc,
            record.mcmillan_tc,
        ])
    numeric = [value for value in values if value is not None]
    return max(numeric) if numeric else None


def sort_formula_matches(
    items: Iterable,
    query: ParsedFormulaExpression,
    sort: str = "relevance",
) -> list:
    ranked = list(items)
    relevance = {item.id: formula_relevance_key(query, item) for item in ranked}
    if sort == "tc_desc":
        ranked.sort(key=lambda item: (-(max_record_tc(item) or -inf), relevance[item.id], item.formula_normalized))
    elif sort == "tc_asc":
        ranked.sort(key=lambda item: ((max_record_tc(item) is None), max_record_tc(item) or inf, relevance[item.id], item.formula_normalized))
    else:
        ranked.sort(key=lambda item: relevance[item.id])
    return ranked
