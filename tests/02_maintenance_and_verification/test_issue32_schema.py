from sqlalchemy import CheckConstraint, UniqueConstraint

from backend import models  # noqa: F401
from backend.database import Base


SCIENTIFIC_TABLES = {
    "material_states",
    "structure_models",
    "calculation_contexts",
    "experimental_contexts",
    "tc_results",
    "superconductor_properties",
    "tc_result_evidences",
    "structure_model_evidences",
    "superconductor_property_evidences",
}


def _constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def test_scientific_entities_share_paper_review_without_child_statuses():
    for table_name in SCIENTIFIC_TABLES:
        table = Base.metadata.tables[table_name]
        assert "paper_revision" in table.c
        assert "review_status" not in table.c
        assert "approved" not in table.c


def test_identity_and_state_fields_are_not_duplicated_across_levels():
    superconductors = Base.metadata.tables["superconductors"]
    states = Base.metadata.tables["material_states"]
    structures = Base.metadata.tables["structure_models"]

    assert "isotope_signature" in superconductors.c
    assert "isotope_signature" not in states.c
    assert "phase_label" not in states.c
    assert "phase_label" not in structures.c
    assert "material_state_id" in Base.metadata.tables["calculation_contexts"].c
    assert "ix_material_states_paper_material_space_group" in {
        index.name for index in states.indexes
    }


def test_reported_space_group_is_available_without_fabricating_a_structure_model():
    states = Base.metadata.tables["material_states"]

    assert "reported_space_group_symbol" in states.c
    assert "reported_space_group_number" in states.c
    assert "ck_material_states_reported_space_group" in _constraint_names(
        states, CheckConstraint
    )


def test_tc_results_are_longitudinal_and_have_one_representative_per_method():
    tc_results = Base.metadata.tables["tc_results"]

    assert tc_results.c.representative_marker.computed is not None
    assert "uq_tc_results_representative" in _constraint_names(
        tc_results, UniqueConstraint
    )
    assert "ck_tc_results_context_kind" in _constraint_names(
        tc_results, CheckConstraint
    )
    for forbidden_column in (
        "mcmillan_tc",
        "allen_dynes_tc",
        "isotropic_eliashberg_tc",
        "anisotropic_eliashberg_tc",
        "experimental_tc",
    ):
        assert forbidden_column not in tc_results.c


def test_general_properties_preserve_raw_values_and_exclude_tc():
    definitions = Base.metadata.tables["property_definitions"]
    properties = Base.metadata.tables["superconductor_properties"]

    assert "ck_property_definitions_non_tc" in _constraint_names(
        definitions, CheckConstraint
    )
    for required_raw_column in ("name_raw", "value_raw"):
        assert properties.c[required_raw_column].nullable is False
    for optional_canonical_column in (
        "value_number",
        "value_min",
        "value_max",
        "canonical_unit",
    ):
        assert properties.c[optional_canonical_column].nullable is True
    assert "superconductor_property_evidences" in Base.metadata.tables


def test_cross_paper_automatic_structure_merging_has_no_schema_identity():
    structures = Base.metadata.tables["structure_models"]
    unique_names = _constraint_names(structures, UniqueConstraint)
    index_names = {index.name for index in structures.indexes}

    assert "uq_structure_models_hash" not in unique_names
    assert "ix_structure_models_hash" in index_names
