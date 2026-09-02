"""Issue #76：外键级联链迁移的运行时验证（T005–T008）。

Spec: docs/specs/76-review-scientific-data-editing/spec.md（FR-013、FR-014、FR-018）
数据模型: docs/specs/76-review-scientific-data-editing/data-model.md（外键迁移）

在 FRESH_MYSQL_DATABASE_URL 指向的隔离空库上跑完整迁移到 head，再验证：

- T005：单条 UPDATE papers 三字段使 4 张血缘子表的 paper_revision 全部级联更新且行数不变。
- T006：事务内升版后抛异常回滚，主表与全部子表一同回到原值，无中间态残留。
- T007：删除两条直连外键后完整性不放松（非法 chunk、删除被引用 paper、删除被引用 file 均被拒）。
- T008：四条 CASCADE 外键的 UPDATE_RULE/DELETE_RULE 符合目标，两条直连已不存在。

注意：MySQL 的多 CASCADE 冲突在建表期不报错、仅在级联更新时抛 1452，
因此必须靠本模块的运行时测试（T005）确认结构正确，元数据核对（T008）不足以证明。
"""
import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

REPO_ROOT = Path(__file__).resolve().parents[2]

CASCADE_FKS = {
    "fk_paper_files_paper_revision": "paper_files",
    "fk_paper_chunks_file_revision": "paper_chunks",
    "fk_paper_evidences_chunk_revision": "paper_evidences",
    "fk_material_states_paper_revision": "material_states",
}
REMOVED_DIRECT_FKS = {"fk_paper_chunks_paper_revision", "fk_paper_evidences_paper_revision"}


def _config(database_url):
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _database_url():
    database_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
    if not database_url:
        pytest.skip("仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收")
    database_name = make_url(database_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"
    return database_url


def _seed_lineage(engine):
    """插入一条最小血缘链：approved 论文 revision=1 + files + chunks + evidences + material_states。"""
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users
                    (id, email, username, password_hash, real_name, role,
                     is_approved, is_email_verified, username_change_allowed)
                VALUES
                    (1, 'cascade@example.test', 'cascade_user', 'hash', 'Cascade',
                     'user', 0, 0, 0)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO papers
                    (id, doi, title, authors, uploaded_by_user_id, review_status,
                     content_revision, approved_revision)
                VALUES
                    (1, '10.0000/cascade', 'Cascade paper', :authors, 1,
                     'approved', 1, 1)
                """
            ),
            {"authors": json.dumps(["Cascade"])},
        )
        connection.execute(
            text(
                """
                INSERT INTO chemical_systems
                    (id, system_key, elements_list, element_count)
                VALUES (1, 'H-La', :elements, 2)
                """
            ),
            {"elements": json.dumps(["H", "La"])},
        )
        connection.execute(
            text(
                """
                INSERT INTO superconductors
                    (id, chemical_system_id, chemical_formula, formula_normalized,
                     composition_key, isotope_signature, display_name, elements_list,
                     composition, element_ratio)
                VALUES
                    (1, 1, 'LaH10', 'H10La', 'H:10|La:1', NULL, 'LaH10',
                     :elements, :composition, :ratio)
                """
            ),
            {
                "elements": json.dumps(["H", "La"]),
                "composition": json.dumps({"H": 10, "La": 1}),
                "ratio": json.dumps({"H": 10, "La": 1}),
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO material_states
                    (id, paper_id, paper_revision, superconductor_id,
                     pressure_value_gpa, state_kind, created_at, updated_at)
                VALUES (1, 1, 1, 1, 200, 'theoretical', NOW(), NOW())
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_files
                    (id, paper_id, paper_revision, role, original_filename,
                     stored_path, sha256, size, sort_order)
                VALUES
                    (1, 1, 1, 'main', 'paper.pdf', '/papers/1/paper.pdf',
                     :sha256, 100, 0)
                """
            ),
            {"sha256": "a" * 64},
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_chunks
                    (id, paper_id, paper_revision, paper_file_id, chunk_index,
                     content, created_at)
                VALUES (1, 1, 1, 1, 0, 'chunk content', NOW())
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_evidences
                    (id, paper_id, paper_revision, paper_chunk_id,
                     field_path, quote)
                VALUES (1, 1, 1, 1, 'paper.summary', 'evidence quote')
                """
            )
        )


def _revisions_of(engine, table):
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT paper_revision FROM {table} ORDER BY id")
        ).fetchall()
        return [row[0] for row in rows]


def _drop_all(engine):
    inspector = inspect(engine)
    with engine.begin() as connection:
        # 表间有外键依赖，任意顺序 DROP 会被 FK 拒绝，先关检查再删
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspector.get_table_names():
            connection.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture
def migrated_engine():
    database_url = _database_url()
    engine = create_engine(database_url, future=True)
    config = _config(database_url)
    # setup 先清理：上次运行若在 upgrade 中途失败会残留表，导致本库不再为空
    _drop_all(engine)
    command.upgrade(config, "head")
    yield engine
    _drop_all(engine)
    engine.dispose()


def test_single_update_cascades_revision_to_all_lineage_tables(migrated_engine):
    """T005：单条 UPDATE 三个版本字段使 4 张子表 revision 全部变为 2 且行数不变。"""
    engine = migrated_engine
    _seed_lineage(engine)

    with engine.begin() as connection:
        result = connection.execute(
            text(
                """
                UPDATE papers
                SET content_revision = 2, approved_revision = NULL, review_status = 'pending'
                WHERE id = 1
                """
            )
        )
        assert result.rowcount == 1

    for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states"):
        assert _revisions_of(engine, table) == [2], f"{table} 的 paper_revision 未级联更新"
    # 行数不变（迁移而非分叉）
    for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states"):
        with engine.connect() as connection:
            count = connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            assert count == 1, f"{table} 行数应为 1，实际 {count}"


def test_revision_update_rolls_back_with_lineage(migrated_engine):
    """T006：事务内升版后抛异常回滚，主表与全部子表一同回到原值。"""
    engine = migrated_engine
    _seed_lineage(engine)

    with pytest.raises(RuntimeError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    UPDATE papers
                    SET content_revision = 2, approved_revision = NULL, review_status = 'pending'
                    WHERE id = 1
                    """
                )
            )
            raise RuntimeError("模拟重建失败")

    with engine.connect() as connection:
        paper = connection.execute(
            text("SELECT content_revision, approved_revision, review_status FROM papers WHERE id = 1")
        ).one()
        assert tuple(paper) == (1, 1, "approved"), f"论文版本字段未回滚: {tuple(paper)}"
    for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states"):
        assert _revisions_of(engine, table) == [1], f"{table} 未随主表回滚"


def test_integrity_holds_without_direct_fks(migrated_engine):
    """T007：删除直连外键后完整性不放松。"""
    engine = migrated_engine
    _seed_lineage(engine)

    # 插入 paper_id 不存在的 chunk：经 fk_paper_chunks_file_revision 被拒
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO paper_chunks
                        (id, paper_id, paper_revision, paper_file_id, chunk_index,
                         content, created_at)
                    VALUES (2, 999, 1, 1, 1, 'orphan', NOW())
                    """
                )
            )

    # 删除仍被引用的 paper：ON DELETE RESTRICT 经 files 层传递
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM papers WHERE id = 1"))

    # 删除仍被 chunk 引用的 file：fk_paper_chunks_file_revision 的 RESTRICT
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM paper_files WHERE id = 1"))


def test_fk_rules_match_target_structure(migrated_engine):
    """T008：四条 CASCADE 外键的 UPDATE/DELETE 规则正确，两条直连已删除。"""
    engine = migrated_engine
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                """
                SELECT CONSTRAINT_NAME, TABLE_NAME, UPDATE_RULE, DELETE_RULE
                FROM information_schema.REFERENTIAL_CONSTRAINTS
                WHERE CONSTRAINT_SCHEMA = DATABASE()
                """
            )
        ).fetchall()

    rules = {row[0]: (row[1], row[2], row[3]) for row in rows}
    for name, table in CASCADE_FKS.items():
        assert name in rules, f"缺少外键 {name}"
        assert rules[name] == (table, "CASCADE", "RESTRICT"), f"{name} 规则不符: {rules.get(name)}"
    for name in REMOVED_DIRECT_FKS:
        assert name not in rules, f"冗余直连外键 {name} 应已删除"
