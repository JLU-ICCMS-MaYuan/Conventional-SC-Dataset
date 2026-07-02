from backend.formula_similarity import parse_formula_expression


def test_parse_formula_expression_supports_fractional_amounts():
    parsed = parse_formula_expression("Ba1/2K1/2Fe2As2")

    assert parsed.elements == ["As", "Ba", "Fe", "K"]
    assert parsed.amounts["Ba"].nominal == parsed.amounts["K"].nominal


def test_parse_formula_expression_supports_variable_formula():
    parsed = parse_formula_expression("FeSe1-xTex")

    assert parsed.elements == ["Fe", "Se", "Te"]
    assert parsed.amounts["Fe"].nominal == 1
    assert parsed.amounts["Se"].variable is True
    assert parsed.amounts["Te"].variable is True


def test_parse_formula_expression_supports_nested_parentheses():
    parsed = parse_formula_expression("((Ba1/2K1/2)Fe2As2)")

    assert parsed.elements == ["As", "Ba", "Fe", "K"]
    assert parsed.amounts["Fe"].nominal == 2
