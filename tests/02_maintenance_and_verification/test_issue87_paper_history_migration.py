"""#87：文献处理历史迁移契约。"""

import importlib.util
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_PATH = REPO_ROOT / "alembic/versions/20260903_0002_paper_history_events.py"
FRESH_MYSQL_DATABASE_URL = os.environ.get("FRESH_MYSQL_DATABASE_URL")


def _config(database_url: str | None = None) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
    return config


def _migration_module():
    spec = importlib.util.spec_from_file_location("issue87_paper_history", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _drop_all_tables(engine) -> None:
    inspector = inspect(engine)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table_name in inspector.get_table_names():
            connection.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def test_paper_history_migration_is_the_only_next_revision():
    assert MIGRATION_PATH.is_file(), "#87 必须提供文献处理历史迁移"
    migration = _migration_module()
    assert migration.revision == "paper_history_events"
    assert migration.down_revision == "experimental_tc_context"

    script = ScriptDirectory.from_config(_config())
    # 后续 Feature 可能继续以 #87 为父迁移；这里验证 #87 是单一主链上的
    # 正确节点，不把测试绑定到当前仓库未来的最新 head 名称。
    assert script.get_revision("networked_news_discovery").down_revision == "paper_history_events"
    source = MIGRATION_PATH.read_text(encoding="utf-8")
    assert '"ix_paper_history_events_paper_revision"' in source


@pytest.mark.skipif(
    not FRESH_MYSQL_DATABASE_URL,
    reason="仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 迁移验收",
)
def test_paper_history_migration_preserves_reviews_and_backfills_uploads():
    database_name = make_url(FRESH_MYSQL_DATABASE_URL).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"
    engine = create_engine(FRESH_MYSQL_DATABASE_URL, future=True)
    config = _config(FRESH_MYSQL_DATABASE_URL)
    try:
        _drop_all_tables(engine)
        command.upgrade(config, "experimental_tc_context")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO users "
                "(id, email, username, password_hash, real_name, role, is_approved, "
                "is_email_verified, username_change_allowed, account_status) VALUES "
                "(1, 'author@example.test', 'author', 'hash', 'Author', 'user', 1, 1, 1, 'active'), "
                "(2, 'reviewer@example.test', 'reviewer', 'hash', 'Reviewer', 'admin', 1, 1, 1, 'active')"
            ))
            connection.execute(text(
                "INSERT INTO papers "
                "(id, doi, title, authors, year, uploaded_by_user_id, review_status, content_revision, created_at) VALUES "
                "(11, '10.1000/known-uploader', 'Known uploader', JSON_ARRAY('Author'), 2024, 1, 'pending', 1, '2026-09-03 10:00:00'), "
                "(12, '10.1000/unknown-uploader', 'Unknown uploader', JSON_ARRAY('Importer'), 2023, NULL, 'pending', 1, '2026-09-03 10:30:00')"
            ))
            connection.execute(text(
                "INSERT INTO paper_review_events "
                "(paper_id, paper_revision, reviewer_user_id, status, review_comment, reviewed_at, request_id, source) "
                "VALUES (11, 1, 2, 'approved', '证据充分', '2026-09-03 12:00:00', 'backfill-upload-paper-11', 'single')"
            ))

        command.upgrade(config, "head")

        with engine.connect() as connection:
            table_names = set(inspect(connection).get_table_names())
            assert "paper_history_events" in table_names
            assert "paper_review_events" not in table_names
            events = connection.execute(text(
                "SELECT paper_id, event_type, actor_user_id, actor_username_snapshot, "
                "review_status, review_comment, paper_revision, operation_id "
                "FROM paper_history_events ORDER BY paper_id, occurred_at, id"
            )).mappings().all()

        assert [(event["paper_id"], event["event_type"]) for event in events] == [
            (11, "uploaded"),
            (11, "reviewed"),
            (12, "uploaded"),
        ]
        reviewed = events[1]
        assert reviewed["actor_user_id"] == 2
        assert reviewed["actor_username_snapshot"] == "reviewer"
        assert reviewed["review_status"] == "approved"
        assert reviewed["review_comment"] == "证据充分"
        assert reviewed["paper_revision"] == 1
        assert reviewed["operation_id"] == "backfill-upload-paper-11"

        known_upload, unknown_upload = events[0], events[2]
        assert known_upload["actor_user_id"] == 1
        assert known_upload["actor_username_snapshot"] == "author"
        assert unknown_upload["actor_user_id"] is None
        assert unknown_upload["actor_username_snapshot"] is None
        assert known_upload["operation_id"] is None
        assert unknown_upload["operation_id"] is None
        assert not any(event["event_type"] == "modified" for event in events)
    finally:
        _drop_all_tables(engine)
        engine.dispose()
