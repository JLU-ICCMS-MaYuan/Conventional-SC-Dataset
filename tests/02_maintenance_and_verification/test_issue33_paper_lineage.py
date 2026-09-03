from sqlalchemy import CheckConstraint, ForeignKeyConstraint, UniqueConstraint

from backend import models  # noqa: F401
from backend.database import Base


def _constraint_names(table, constraint_type):
    return {
        constraint.name
        for constraint in table.constraints
        if isinstance(constraint, constraint_type)
    }


def _foreign_key_shapes(table):
    return {
        (
            tuple(element.parent.name for element in constraint.elements),
            tuple(element.column.table.name for element in constraint.elements),
            tuple(element.column.name for element in constraint.elements),
            constraint.ondelete,
        )
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    }


def test_paper_lineage_keeps_five_separate_tables():
    assert {
        "papers",
        "paper_files",
        "paper_chunks",
        "paper_evidences",
        "paper_history_events",
    }.issubset(Base.metadata.tables)


def test_paper_file_is_the_only_file_path_source_and_limits_main_role():
    papers = Base.metadata.tables["papers"]
    files = Base.metadata.tables["paper_files"]

    assert "source_file_path" not in papers.c
    assert files.c.stored_path.nullable is False
    assert files.c.main_marker.computed is not None
    assert {
        "uq_paper_files_order",
        "uq_paper_files_path",
        "uq_paper_files_main",
        "uq_paper_files_identity_revision",
    }.issubset(_constraint_names(files, UniqueConstraint))
    assert "ck_paper_files_role" in _constraint_names(files, CheckConstraint)


def test_chunks_are_unique_per_file_and_bound_to_one_paper_revision():
    chunks = Base.metadata.tables["paper_chunks"]

    assert chunks.c.paper_file_id.nullable is False
    assert "uq_paper_chunks_file_index" in _constraint_names(
        chunks, UniqueConstraint
    )
    shapes = _foreign_key_shapes(chunks)
    assert (
        ("paper_file_id", "paper_id", "paper_revision"),
        ("paper_files", "paper_files", "paper_files"),
        ("id", "paper_id", "paper_revision"),
        "RESTRICT",
    ) in shapes


def test_evidence_has_one_direct_same_revision_chunk_anchor():
    evidences = Base.metadata.tables["paper_evidences"]

    assert set(evidences.c.keys()) == {
        "id",
        "paper_id",
        "paper_revision",
        "paper_chunk_id",
        "field_path",
        "section",
        "page_start",
        "page_end",
        "quote",
        "created_at",
    }
    assert evidences.c.paper_chunk_id.nullable is False
    shapes = _foreign_key_shapes(evidences)
    assert (
        ("paper_chunk_id", "paper_id", "paper_revision"),
        ("paper_chunks", "paper_chunks", "paper_chunks"),
        ("id", "paper_id", "paper_revision"),
        "RESTRICT",
    ) in shapes


def test_history_event_records_revision_and_restricts_paper_deletion():
    events = Base.metadata.tables["paper_history_events"]
    shapes = _foreign_key_shapes(events)

    assert events.c.paper_revision.nullable is False
    assert "ck_paper_history_events_revision" in _constraint_names(
        events, CheckConstraint
    )
    assert (
        ("paper_id",),
        ("papers",),
        ("id",),
        "RESTRICT",
    ) in shapes
