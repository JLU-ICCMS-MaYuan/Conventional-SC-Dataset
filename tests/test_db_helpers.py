from backend.db_helpers import (
    build_system_key,
    normalize_formula,
    parse_formula_composition,
)


def test_build_system_key_sorts_symbols():
    assert build_system_key(["La", "H"]) == ("H-La", ["H", "La"])


def test_parse_formula_composition_counts_atoms():
    assert parse_formula_composition("LaH10") == {"La": 1, "H": 10}


def test_parse_formula_composition_supports_decimal_amounts():
    assert parse_formula_composition("Ba0.6K0.4Fe2As2") == {
        "Ba": 0.6,
        "K": 0.4,
        "Fe": 2.0,
        "As": 2.0,
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
    assert composition == {"La": 1, "H": 10}
    assert ratios["La"] == 1 / 11
    assert ratios["H"] == 10 / 11


def test_normalize_formula_formats_decimal_amounts():
    normalized, elements, composition, ratios = normalize_formula("Ba0.6K0.4Fe2As2")
    assert normalized == "As2Ba0.6Fe2K0.4"
    assert elements == ["As", "Ba", "Fe", "K"]
    assert composition == {"Ba": 0.6, "K": 0.4, "Fe": 2.0, "As": 2.0}
    assert ratios["Ba"] == 0.6 / 5.0
    assert ratios["K"] == 0.4 / 5.0
    assert ratios["Fe"] == 2.0 / 5.0
    assert ratios["As"] == 2.0 / 5.0
