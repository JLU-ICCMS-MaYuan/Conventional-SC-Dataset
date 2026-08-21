from sqlalchemy import JSON

from backend import models  # noqa: F401
from backend.database import Base


EXPECTED_TABLES = {
    "calculation_contexts",
    "chemical_systems",
    "experimental_contexts",
    "material_states",
    "paper_chunks",
    "paper_evidences",
    "paper_files",
    "paper_review_events",
    "papers",
    "periodic_table_elements",
    "property_definitions",
    "structure_model_evidences",
    "structure_models",
    "superconductor_properties",
    "superconductor_property_evidences",
    "superconductors",
    "tc_result_evidences",
    "tc_results",
    "username_change_audit_events",
    "users",
}


def test_dataset_metadata_defines_fresh_target_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_legacy_scientific_tables_are_not_in_target_metadata():
    assert {
        "key_properties",
        "superconductor_records",
        "superconductors_structures",
    }.isdisjoint(Base.metadata.tables)


def test_core_json_columns_are_json_and_required():
    chemical_systems = Base.metadata.tables["chemical_systems"]
    superconductors = Base.metadata.tables["superconductors"]
    papers = Base.metadata.tables["papers"]

    assert isinstance(chemical_systems.c.elements_list.type, JSON)
    assert chemical_systems.c.elements_list.nullable is False
    assert isinstance(superconductors.c.composition.type, JSON)
    assert superconductors.c.composition.nullable is False
    assert isinstance(papers.c.authors.type, JSON)


def test_paper_approval_is_bound_to_current_content_revision():
    papers = Base.metadata.tables["papers"]
    constraint_names = {constraint.name for constraint in papers.constraints}
    index_names = {index.name for index in papers.indexes}

    assert papers.c.content_revision.nullable is False
    assert papers.c.approved_revision.nullable is True
    assert "ck_papers_review_revision" in constraint_names
    assert "uq_papers_id_content_revision" in constraint_names
    assert "ix_papers_public_revision" in index_names
    assert "source_file_path" not in papers.c
