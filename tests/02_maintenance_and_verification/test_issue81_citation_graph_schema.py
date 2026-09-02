"""Issue #81：论文引用事实与图谱里程碑的 Schema 契约。"""

from pathlib import Path

from backend import models  # noqa: F401
from backend.database import Base


ROOT = Path(__file__).resolve().parents[2]
MIGRATION = ROOT / "alembic/versions/20260902_0004_paper_citation_graph.py"


def _foreign_key(table, columns):
    return next(
        constraint for constraint in table.foreign_key_constraints
        if tuple(column.name for column in constraint.columns) == tuple(columns)
    )


def test_reference_tables_are_versioned_and_keep_raw_records():
    papers = Base.metadata.tables["papers"]
    extractions = Base.metadata.tables["paper_reference_extractions"]
    references = Base.metadata.tables["paper_references"]
    marks = Base.metadata.tables["paper_graph_marks"]

    assert papers.c.year.nullable is False
    assert set(extractions.primary_key.columns.keys()) == {"paper_id", "paper_revision"}
    source_fk = _foreign_key(references, ("paper_id", "paper_revision"))
    assert source_fk.ondelete == "RESTRICT"
    assert {element.target_fullname for element in source_fk.elements} == {
        "papers.id", "papers.content_revision",
    }
    assert references.c.raw_citation.nullable is False
    assert {"paper_id", "paper_revision", "reference_index"} <= set(
        next(
            constraint for constraint in references.constraints
            if constraint.name == "uq_paper_references_source_index"
        ).columns.keys()
    )
    cited_fk = _foreign_key(references, ("cited_paper_id",))
    assert cited_fk.ondelete == "RESTRICT"
    assert set(marks.primary_key.columns.keys()) == {"paper_id", "mark_type"}


def test_citation_graph_migration_contains_integrity_guards():
    source = MIGRATION.read_text(encoding="utf-8")

    assert "paper_reference_extractions" in source
    assert "paper_references" in source
    assert "paper_graph_marks" in source
    assert "uq_paper_references_source_index" in source
    assert "ck_paper_references_match_consistency" in source
    assert 'ondelete="RESTRICT"' in source
    assert 'SELECT COUNT(*) FROM papers WHERE year IS NULL' in source
    assert 'nullable=False' in source
