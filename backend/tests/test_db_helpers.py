from backend.db_helpers import extract_formula_elements_loose


def test_loose_extraction_drops_unit_tokens_and_parenthetical_notes():
    elements = extract_formula_elements_loose("LaHx (x = 1–12) 150 GPa")

    assert elements == ["H", "La"]
    assert len(elements) == 2
    assert "P" not in elements
    assert "Pa" not in elements
    assert "G" not in elements


def test_loose_extraction_handles_variable_stoichiometry():
    assert extract_formula_elements_loose("LaHx") == ["H", "La"]
    assert extract_formula_elements_loose("LaH10") == ["H", "La"]


def test_loose_extraction_splits_on_dash_and_drops_annotation_words():
    assert extract_formula_elements_loose("Y–H system") == ["H", "Y"]


def test_loose_extraction_matches_strict_results_on_plain_formulas():
    assert extract_formula_elements_loose("CeCu2Si2") == ["Ce", "Cu", "Si"]
    assert extract_formula_elements_loose("FeSe0.5Te0.5") == ["Fe", "Se", "Te"]


def test_loose_extraction_returns_empty_for_plain_words():
    assert extract_formula_elements_loose("hydrogen") == []
    assert extract_formula_elements_loose("") == []
