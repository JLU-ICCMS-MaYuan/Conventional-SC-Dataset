from backend.db_helpers import build_system_key, normalize_formula
from backend.models import ChemicalSystem, Superconductor
from backend.repositories.superconductors import search_superconductors


def _json_numbers(values):
    return {key: float(value) for key, value in values.items()}


def add_superconductor(db, formula):
    normalized, elements, composition, ratios = normalize_formula(formula)
    system_key, system_elements = build_system_key(elements)
    system = db.query(ChemicalSystem).filter_by(system_key=system_key).first()
    if system is None:
        system = ChemicalSystem(
            system_key=system_key,
            elements_list=system_elements,
            element_count=len(system_elements),
        )
        db.add(system)
        db.flush()
    superconductor = Superconductor(
        chemical_system_id=system.id,
        chemical_formula=formula,
        formula_normalized=normalized,
        display_name=formula,
        elements_list=elements,
        composition=_json_numbers(composition),
        element_ratio=_json_numbers(ratios),
    )
    db.add(superconductor)
    db.commit()
    return superconductor


def test_formula_search_finds_normalized_formula(db_session):
    add_superconductor(db_session, "LaH10")
    result = search_superconductors(db_session, "formula_search", formula="H10La")
    assert [item.chemical_formula for item in result.items] == ["LaH10"]
    assert result.total == 1


def test_elements_exact_search_matches_same_system(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "H3S")
    result = search_superconductors(db_session, "elements_exact_search", elements=["La", "H"])
    assert [item.chemical_formula for item in result.items] == ["LaH10"]


def test_elements_combination_search_matches_subsets(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "H3S")
    add_superconductor(db_session, "LaH3S")
    result = search_superconductors(db_session, "elements_combination_search", elements=["La", "H", "S"])
    assert {item.chemical_formula for item in result.items} == {"LaH10", "H3S", "LaH3S"}


def test_elements_contained_search_matches_supersets(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "LaH3S")
    result = search_superconductors(db_session, "elements_contained_search", elements=["La", "H"])
    assert {item.chemical_formula for item in result.items} == {"LaH10", "LaH3S"}


def test_search_pagination(db_session):
    add_superconductor(db_session, "LaH10")
    add_superconductor(db_session, "LaH6")
    result = search_superconductors(
        db_session,
        "elements_exact_search",
        elements=["La", "H"],
        limit=1,
        offset=1,
    )
    assert result.total == 2
    assert result.page == 2
    assert result.page_size == 1
    assert result.has_prev is True
    assert result.has_next is False
    assert len(result.items) == 1
