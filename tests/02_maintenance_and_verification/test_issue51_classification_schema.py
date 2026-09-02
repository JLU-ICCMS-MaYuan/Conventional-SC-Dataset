from sqlalchemy import CheckConstraint, UniqueConstraint

from backend import models  # noqa: F401
from backend.database import Base


def _constraint_names(table, kind):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, kind)
    }


def test_material_state_classification_tables_exist():
    expected = {
        "material_families",
        "material_family_aliases",
        "paper_material_families",
        "structure_families",
        "structure_family_aliases",
        "material_state_structure_families",
    }

    assert expected <= set(Base.metadata.tables)
    assert {
        "classification_proposals",
        "classification_evidences",
        "classification_audit_events",
    }.isdisjoint(Base.metadata.tables)


def test_papers_hold_material_families_while_states_keep_other_dimensions():
    states = Base.metadata.tables["material_states"]
    paper_families = Base.metadata.tables["paper_material_families"]

    assert "material_family_id" not in states.c
    assert "element_count" in states.c
    assert "material_dimensionality" in states.c
    assert {"paper_id", "paper_revision", "material_family_id"} <= set(paper_families.c.keys())
    assert set(paper_families.primary_key.columns.keys()) == {
        "paper_id", "paper_revision", "material_family_id",
    }
    assert "ck_material_states_element_count" in _constraint_names(states, CheckConstraint)
    assert "ck_material_states_dimensionality" in _constraint_names(states, CheckConstraint)


def test_structure_family_relation_has_one_primary_marker_per_state():
    relation = Base.metadata.tables["material_state_structure_families"]

    assert relation.c.primary_marker.computed is not None
    assert "uq_material_state_structure_primary" in _constraint_names(
        relation, UniqueConstraint
    )


def test_catalog_aliases_are_deterministically_unique():
    material_aliases = Base.metadata.tables["material_family_aliases"]
    structure_aliases = Base.metadata.tables["structure_family_aliases"]

    assert "uq_material_family_alias_normalized" in _constraint_names(
        material_aliases, UniqueConstraint
    )
    assert "uq_structure_family_alias_normalized" in _constraint_names(
        structure_aliases, UniqueConstraint
    )


def test_final_paper_schema_does_not_store_referenced_materials():
    assert "referenced_materials" not in Base.metadata.tables["papers"].c


def test_review_event_stores_internal_classification_snapshot():
    assert "classification_snapshot" in Base.metadata.tables["paper_review_events"].c
