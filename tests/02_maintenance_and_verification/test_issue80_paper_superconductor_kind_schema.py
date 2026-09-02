"""Issue #80：论文级 Superconductor type 的 Python 模型与迁移契约。"""

from pathlib import Path

from backend.database import Base
from backend import models  # noqa: F401


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION = REPO_ROOT / "alembic/versions/20260902_0003_paper_superconductor_kind.py"


def test_superconductor_kind_belongs_to_paper_not_material_state():
    papers = Base.metadata.tables["papers"]
    states = Base.metadata.tables["material_states"]

    assert "superconductor_kind" in papers.c
    assert papers.c.superconductor_kind.server_default.arg == "unknown"
    assert "superconductor_kind" not in states.c


def test_migration_aggregates_by_revision_and_turns_conflicts_into_unknown():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "GROUP BY paper_id, paper_revision" in source
    assert "COUNT(DISTINCT CASE WHEN superconductor_kind IN" in source
    assert "ELSE 'unknown'" in source
    assert 'op.drop_column("material_states", "superconductor_kind")' in source
