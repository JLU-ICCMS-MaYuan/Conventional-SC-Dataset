from backend import models  # noqa: F401
from backend.database import Base
from sqlalchemy import Boolean, DateTime, Float, Integer, JSON, String, Text


EXPECTED_TABLES = {
    "periodic_table_elements",
    "chemical_systems",
    "superconductors",
    "papers",
    "users",
    "superconductor_records",
    "superconductors_structures",
}


def test_dataset_metadata_defines_expected_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_superconductor_records_include_required_redesign_columns():
    columns = Base.metadata.tables["superconductor_records"].columns

    assert "energy_above_hull" in columns
    assert "anisotropic_eliashberg_tc" in columns
    assert "show_in_chart" in columns
    assert "pseudopotential_name" in columns


def test_core_json_columns_are_json_and_required():
    assert isinstance(Base.metadata.tables["chemical_systems"].columns["elements_list"].type, JSON)
    assert Base.metadata.tables["chemical_systems"].columns["elements_list"].nullable is False
    assert isinstance(Base.metadata.tables["superconductors"].columns["composition"].type, JSON)
    assert Base.metadata.tables["superconductors"].columns["composition"].nullable is False
    assert isinstance(Base.metadata.tables["papers"].columns["authors"].type, JSON)
    assert Base.metadata.tables["papers"].columns["authors"].nullable is False
    assert isinstance(Base.metadata.tables["superconductor_records"].columns["element_n_ef"].type, JSON)


def test_key_constraints_and_foreign_keys_are_declared():
    superconductors = Base.metadata.tables["superconductors"]
    papers = Base.metadata.tables["papers"]
    records = Base.metadata.tables["superconductor_records"]

    assert superconductors.columns["formula_normalized"].unique is True
    assert superconductors.columns["formula_normalized"].index is True
    assert {fk.column.table.name for fk in superconductors.columns["chemical_system_id"].foreign_keys} == {"chemical_systems"}

    assert papers.columns["doi"].unique is True
    assert papers.columns["review_status"].default.arg == "pending"
    assert {fk.column.table.name for fk in papers.columns["uploaded_by_user_id"].foreign_keys} == {"users"}
    assert {fk.column.table.name for fk in papers.columns["reviewed_by_user_id"].foreign_keys} == {"users"}

    assert {fk.column.table.name for fk in records.columns["superconductor_id"].foreign_keys} == {"superconductors"}
    assert {fk.column.table.name for fk in records.columns["paper_id"].foreign_keys} == {"papers"}


def test_superconductor_record_column_types_and_nullability():
    records = Base.metadata.tables["superconductor_records"]

    assert records.columns["superconductor_id"].nullable is False
    assert records.columns["paper_id"].nullable is True
    assert records.columns["source_label"].nullable is False
    assert records.columns["pressure_gpa"].nullable is False
    assert records.columns["show_in_chart"].nullable is False
    assert records.columns["show_in_chart"].default.arg is False
    assert isinstance(records.columns["pressure_gpa"].type, Float)
    assert isinstance(records.columns["show_in_chart"].type, Boolean)
    assert isinstance(records.columns["note"].type, Text)


def test_superconductor_records_avoid_nullable_unique_identity_constraint():
    records = Base.metadata.tables["superconductor_records"]

    assert "uq_superconductor_record_identity" not in {
        constraint.name for constraint in records.constraints
    }


def test_superconductors_structures_table_contract():
    structures = Base.metadata.tables["superconductors_structures"]

    assert set(structures.columns.keys()) == {
        "id",
        "superconductor_id",
        "pressure_gpa",
        "space_group_symbol",
        "space_group_number",
        "structure_format",
        "structure_text",
        "structure_hash",
        "atom_count",
        "elements_list",
        "cell_parameters",
        "volume",
        "review_status",
        "is_default",
        "source_type",
        "source_label",
        "created_by_user_id",
        "created_at",
        "updated_at",
    }
    assert structures.columns["superconductor_id"].nullable is False
    assert structures.columns["pressure_gpa"].nullable is False
    assert structures.columns["structure_format"].nullable is False
    assert structures.columns["structure_text"].nullable is False
    assert structures.columns["structure_hash"].nullable is False
    assert structures.columns["review_status"].nullable is False
    assert structures.columns["review_status"].default.arg == "pending"
    assert structures.columns["is_default"].nullable is False
    assert structures.columns["is_default"].default.arg is False
    assert structures.columns["source_type"].nullable is False
    assert isinstance(structures.columns["pressure_gpa"].type, Float)
    assert isinstance(structures.columns["space_group_symbol"].type, String)
    assert isinstance(structures.columns["space_group_number"].type, Integer)
    assert isinstance(structures.columns["structure_text"].type, Text)
    assert isinstance(structures.columns["structure_hash"].type, String)
    assert isinstance(structures.columns["atom_count"].type, Integer)
    assert isinstance(structures.columns["elements_list"].type, JSON)
    assert isinstance(structures.columns["cell_parameters"].type, JSON)
    assert isinstance(structures.columns["volume"].type, Float)
    assert isinstance(structures.columns["is_default"].type, Boolean)
    assert isinstance(structures.columns["created_at"].type, DateTime)
    assert isinstance(structures.columns["updated_at"].type, DateTime)


def test_superconductors_structures_foreign_keys_are_declared():
    structures = Base.metadata.tables["superconductors_structures"]

    assert {fk.column.table.name for fk in structures.columns["superconductor_id"].foreign_keys} == {"superconductors"}
    assert {fk.column.table.name for fk in structures.columns["created_by_user_id"].foreign_keys} == {"users"}


def test_superconductors_structures_identity_index_is_declared():
    structures = Base.metadata.tables["superconductors_structures"]
    indexes = {index.name: index for index in structures.indexes}

    assert "ix_superconductors_structures_identity" in indexes
    assert indexes["ix_superconductors_structures_identity"].unique is False
    assert [column.name for column in indexes["ix_superconductors_structures_identity"].columns] == [
        "superconductor_id",
        "space_group_symbol",
        "space_group_number",
        "pressure_gpa",
    ]
