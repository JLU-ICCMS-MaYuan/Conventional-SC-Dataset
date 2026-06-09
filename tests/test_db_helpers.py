from decimal import Decimal

from backend.db_helpers import (
    build_system_key,
    normalize_formula,
    parse_formula_composition,
)


def test_build_system_key_sorts_symbols():
    assert build_system_key(["La", "H"]) == ("H-La", ["H", "La"])


def test_parse_formula_composition_counts_atoms():
    assert parse_formula_composition("LaH10") == {"La": Decimal("1"), "H": Decimal("10")}


def test_parse_formula_composition_supports_decimal_amounts():
    assert parse_formula_composition("Ba0.6K0.4Fe2As2") == {
        "Ba": Decimal("0.6"),
        "K": Decimal("0.4"),
        "Fe": Decimal("2"),
        "As": Decimal("2"),
    }


def test_parse_formula_composition_rejects_trailing_garbage():
    try:
        parse_formula_composition("LaH10xxx")
    except ValueError:
        return
    raise AssertionError("expected trailing garbage to raise ValueError")


def test_parse_formula_composition_rejects_parentheses():
    try:
        parse_formula_composition("La(OH)2")
    except ValueError:
        return
    raise AssertionError("expected parentheses to raise ValueError")


def test_parse_formula_composition_rejects_zero_amounts():
    try:
        parse_formula_composition("La0H10")
    except ValueError:
        return
    raise AssertionError("expected zero amount to raise ValueError")


def test_normalize_formula_sorts_symbols():
    normalized, elements, composition, ratios = normalize_formula("LaH10")
    assert normalized == "H10La"
    assert elements == ["H", "La"]
    assert composition == {"La": Decimal("1"), "H": Decimal("10")}
    assert ratios["La"] == Decimal("1") / Decimal("11")
    assert ratios["H"] == Decimal("10") / Decimal("11")


def test_normalize_formula_formats_decimal_amounts():
    normalized, elements, composition, ratios = normalize_formula("Ba0.6K0.4Fe2As2")
    assert normalized == "As2Ba0.6Fe2K0.4"
    assert elements == ["As", "Ba", "Fe", "K"]
    assert composition == {"Ba": Decimal("0.6"), "K": Decimal("0.4"), "Fe": Decimal("2"), "As": Decimal("2")}
    assert ratios["Ba"] == Decimal("0.6") / Decimal("5")
    assert ratios["K"] == Decimal("0.4") / Decimal("5")
    assert ratios["Fe"] == Decimal("2") / Decimal("5")
    assert ratios["As"] == Decimal("2") / Decimal("5")


def test_normalize_formula_does_not_emit_scientific_notation():
    normalized, _, _, _ = normalize_formula("H0.00001")
    assert normalized == "H0.00001"
    assert parse_formula_composition(normalized) == {"H": Decimal("0.00001")}


def test_normalize_formula_keeps_very_small_decimal_amounts():
    normalized, _, _, _ = normalize_formula("H0.0000000000001")
    assert normalized == "H0.0000000000001"
    assert "e" not in normalized.lower()
    assert parse_formula_composition(normalized) == {"H": Decimal("0.0000000000001")}


def test_normalize_formula_keeps_sub_float_decimal_amounts():
    amount = "0." + ("0" * 400) + "1"
    normalized, _, _, _ = normalize_formula(f"H{amount}")
    assert normalized == f"H{amount}"
    assert "e" not in normalized.lower()
    assert parse_formula_composition(normalized) == {"H": Decimal(amount)}


def test_normalize_formula_keeps_many_significant_decimal_digits():
    amount = "0.123456789012345678901234567890"
    normalized, _, _, _ = normalize_formula(f"H{amount}")
    assert normalized == f"H{amount.rstrip('0')}"
    assert parse_formula_composition(normalized) == {"H": Decimal(amount)}


def test_normalize_formula_does_not_round_near_integer_decimal_to_integer():
    amount = "1.000000000000000000000000000001"
    normalized, _, _, _ = normalize_formula(f"H{amount}")
    assert normalized == f"H{amount}"
    assert parse_formula_composition(normalized) == {"H": Decimal(amount)}
