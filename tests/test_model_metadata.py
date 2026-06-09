from backend import models  # noqa: F401
from backend.database import Base


EXPECTED_TABLES = {
    "periodic_table_elements",
    "chemical_systems",
    "superconductors",
    "papers",
    "users",
    "superconductor_records",
}


def test_dataset_metadata_defines_only_six_tables():
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_superconductor_records_include_required_redesign_columns():
    columns = Base.metadata.tables["superconductor_records"].columns

    assert "energy_above_hull" in columns
    assert "anisotropic_eliashberg_tc" in columns
    assert "show_in_chart" in columns
    assert "pseudopotential_name" in columns
