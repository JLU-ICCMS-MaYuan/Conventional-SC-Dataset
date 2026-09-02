import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
HEAD = "paper_citation_graph"
REMOVED_TABLES = {
    "classification_proposals",
    "classification_evidences",
    "classification_audit_events",
}


def _config(database_url=None):
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def test_issue51_migrations_have_one_ordered_head():
    script = ScriptDirectory.from_config(_config())

    assert script.get_heads() == [HEAD]
    assert script.get_revision(HEAD).down_revision == "paper_superconductor_kind"


def test_fresh_mysql_84_can_upgrade_to_simplified_classification_schema():
    database_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
    if not database_url:
        pytest.skip("仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收")

    database_name = make_url(database_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"

    engine = create_engine(database_url, future=True)
    config = _config(database_url)
    try:
        assert set(inspect(engine).get_table_names()) <= {"alembic_version"}, "验收库必须为空"
        command.upgrade(config, "head")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert not (tables & REMOVED_TABLES)
        assert {
            "material_families",
            "structure_families",
            "material_state_structure_families",
            "paper_material_families",
            "paper_review_events",
            "paper_reference_extractions",
            "paper_references",
            "paper_graph_marks",
        } <= tables

        material_columns = {item["name"] for item in inspector.get_columns("material_families")}
        structure_columns = {item["name"] for item in inspector.get_columns("structure_families")}
        review_columns = {item["name"] for item in inspector.get_columns("paper_review_events")}
        state_columns = {item["name"] for item in inspector.get_columns("material_states")}

        assert not ({"merged_into_id", "is_active"} & material_columns)
        assert not ({"merged_into_id", "is_active"} & structure_columns)
        assert "classification_snapshot" in review_columns
        paper_family_columns = {
            item["name"] for item in inspector.get_columns("paper_material_families")
        }
        assert {"element_count", "material_dimensionality"} <= state_columns
        paper_columns = {item["name"] for item in inspector.get_columns("papers")}
        assert {"material_family_id", "superconductor_kind"}.isdisjoint(state_columns)
        assert "superconductor_kind" in paper_columns
        assert {"paper_id", "paper_revision", "material_family_id"} <= paper_family_columns
        command.check(config)
    finally:
        engine.dispose()
