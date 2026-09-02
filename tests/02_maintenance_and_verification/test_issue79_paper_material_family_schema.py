"""Issue #79：论文级多 Material family 数据模型与迁移契约。"""

from pathlib import Path

from backend.database import Base
from backend import models  # noqa: F401


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = REPO_ROOT / "alembic/versions/20260902_0002_paper_material_families.py"


def test_material_family_belongs_to_versioned_paper_not_material_state():
    states = Base.metadata.tables["material_states"]
    links = Base.metadata.tables["paper_material_families"]

    assert "material_family_id" not in states.c
    assert set(links.primary_key.columns.keys()) == {
        "paper_id",
        "paper_revision",
        "material_family_id",
    }
    foreign_keys = {
        tuple(column.name for column in constraint.columns): constraint
        for constraint in links.foreign_key_constraints
    }
    paper_fk = foreign_keys[("paper_id", "paper_revision")]
    assert paper_fk.onupdate == "CASCADE"
    assert {element.target_fullname for element in paper_fk.elements} == {
        "papers.id",
        "papers.content_revision",
    }


def test_migration_deduplicates_all_legacy_families_and_removes_state_column():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "SELECT DISTINCT paper_id, paper_revision, material_family_id" in source
    assert 'op.drop_column("material_states", "material_family_id")' in source
    assert 'op.create_table(\n        "paper_material_families"' in source


def test_downgrade_refuses_lossy_multi_family_conversion():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "HAVING COUNT(*) > 1" in source
    assert "旧状态级单值模型无法无损恢复" in source
    assert "raise RuntimeError" in source
