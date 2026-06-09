from backend.db_helpers import (
    build_system_key,
    normalize_formula,
    parse_formula_composition,
)


def test_build_system_key_sorts_symbols():
    assert build_system_key(["La", "H"]) == ("H-La", ["H", "La"])


def test_parse_formula_composition_counts_atoms():
    assert parse_formula_composition("LaH10") == {"La": 1, "H": 10}


def test_normalize_formula_sorts_symbols():
    normalized, elements, composition, ratios = normalize_formula("LaH10")
    assert normalized == "H10La"
    assert elements == ["H", "La"]
    assert composition == {"La": 1, "H": 10}
    assert ratios["La"] == 1 / 11
    assert ratios["H"] == 10 / 11
