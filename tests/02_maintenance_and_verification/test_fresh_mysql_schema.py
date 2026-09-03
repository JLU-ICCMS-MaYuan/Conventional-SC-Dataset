import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_TABLES = {
    "material_states",
    "paper_chunks",
    "paper_evidences",
    "paper_files",
    "property_definitions",
    "structure_models",
    "superconductor_properties",
    "tc_results",
    "profile_change_audit_events",
    "admin_applications",
    "user_governance_audit_events",
}


def _config(database_url=None):
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    if database_url:
        config.set_main_option("sqlalchemy.url", database_url)
        # alembic/env.py 从运行环境读取主库地址，不能只修改 Config。
        os.environ["DATABASE_URL"] = database_url
        os.environ["RAG_DATABASE_URL"] = database_url
    return config


def test_alembic_has_one_ordered_head():
    script = ScriptDirectory.from_config(_config())

    # 新迁移会正常成为 head；这里验证迁移链保持单头且 #84 正确接在既有链上。
    assert len(script.get_heads()) == 1
    assert script.get_revision("experimental_tc_context").down_revision == "paper_citation_graph"
    assert script.get_revision("revision_cascade_chain").down_revision == "add_kg_title"
    assert script.get_revision("add_kg_title").down_revision == "20260831_0066"
    assert script.get_revision("20260831_0066").down_revision == "20260831_0065"
    assert script.get_revision("20260831_0065").down_revision == "20260831_0064"
    assert script.get_revision("20260831_0064").down_revision == "20260831_0063"
    assert script.get_revision("20260831_0063").down_revision == "20260826_0016"
    assert script.get_revision("20260826_0016").down_revision == "20260826_0015"
    assert script.get_revision("20260826_0015").down_revision == "20260826_0014"
    assert script.get_revision("20260826_0014").down_revision == "20260825_0013"
    assert script.get_revision("20260825_0013").down_revision == "20260825_0012"
    assert script.get_revision("20260825_0012").down_revision == "20260824_0011"
    assert script.get_revision("20260824_0011").down_revision == "20260824_0010"
    assert script.get_revision("20260824_0010").down_revision == "20260824_0009"
    assert script.get_revision("20260824_0009").down_revision == "20260821_0008"
    assert script.get_revision("20260821_0008").down_revision == "20260821_0007"
    assert script.get_revision("20260821_0007").down_revision == "20260821_0006"


def test_initial_revision_creates_chunks_before_multifile_revision_alters_them():
    initial = (REPO_ROOT / "alembic/versions/20260609_0001_initial_mysql_schema.py").read_text()
    multifile = (REPO_ROOT / "alembic/versions/20260820_0005_add_multifile_uploads.py").read_text()

    assert 'op.create_table(\n        "paper_chunks"' in initial
    assert 'op.add_column("paper_chunks"' in multifile


def test_fresh_mysql_upgrade_downgrade_guard_and_constraints():
    database_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
    if not database_url:
        pytest.skip("仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收")

    database_name = make_url(database_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"

    engine = create_engine(database_url, future=True)
    config = _config(database_url)
    try:
        existing = set(inspect(engine).get_table_names())
        assert existing <= {"alembic_version"}, "验收库必须是全新空库"

        command.upgrade(config, "head")
        assert TARGET_TABLES.issubset(inspect(engine).get_table_names())
        assert "key_properties" not in inspect(engine).get_table_names()
        state_columns = {column["name"] for column in inspect(engine).get_columns("material_states")}
        assert {"reported_space_group_symbol", "reported_space_group_number"} <= state_columns
        user_columns = {column["name"] for column in inspect(engine).get_columns("users")}
        assert {"avatar_key", "orcid", "research_interests", "session_version", "account_status"} <= user_columns
        user_uniques = {tuple(item["column_names"]) for item in inspect(engine).get_unique_constraints("users")}
        assert ("orcid",) in user_uniques
        application_uniques = {tuple(item["column_names"]) for item in inspect(engine).get_unique_constraints("admin_applications")}
        assert ("user_id", "pending_guard") in application_uniques
        command.check(config)

        command.downgrade(config, "20260821_0006")
        command.upgrade(config, "head")
        command.downgrade(config, "20260821_0006")

        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO users
                        (id, email, username, password_hash, real_name, role,
                         is_approved, is_email_verified, username_change_allowed)
                    VALUES
                        (1, 'guard@example.test', 'guard_user', 'hash', 'Guard',
                         'user', 0, 0, 0)
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO papers
                        (id, doi, title, authors, year, uploaded_by_user_id, review_status)
                    VALUES
                        (1, '10.0000/guard', 'Guard paper', :authors, 2024, 1, 'pending')
                    """
                ),
                {"authors": json.dumps(["Guard"])},
            )

        with pytest.raises(RuntimeError, match="仅支持全新空业务库"):
            command.upgrade(config, "20260821_0007")

        with engine.begin() as connection:
            connection.execute(text("DELETE FROM papers WHERE id = 1"))
            connection.execute(text("DELETE FROM users WHERE id = 1"))

        command.upgrade(config, "head")
        _seed_constraint_rows(engine)
        _assert_main_file_uniqueness(engine)
        _assert_representative_tc_uniqueness(engine)
        _assert_tc_is_not_a_general_property(engine)
        _assert_chunk_index_is_scoped_to_file(engine)
        _assert_cross_paper_evidence_is_rejected(engine)
        _assert_tc_contexts_are_exclusive(engine)
        _assert_same_pressure_states_and_structures_are_independent(engine)
        _assert_history_event_survives_revision_change(engine)
    finally:
        engine.dispose()


def test_experimental_tc_context_migration_cleans_legacy_rows_and_enforces_method_invariant():
    database_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
    if not database_url:
        pytest.skip("仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收")

    database_name = make_url(database_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"
    engine = create_engine(database_url, future=True)
    config = _config(database_url)
    try:
        _drop_all_tables(engine)
        command.upgrade(config, "paper_citation_graph")
        _seed_constraint_rows(engine)
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO experimental_contexts "
                "(id, paper_id, paper_revision, material_state_id, structure_id, tc_criterion) "
                "VALUES (1, 1, 1, 1, NULL, 'author_reported')"
            ))
            connection.execute(text(
                "INSERT INTO calculation_contexts "
                "(id, paper_id, paper_revision, material_state_id, structure_id, "
                "missing_structure_reason, phonon_nuclear_treatment) "
                "VALUES (2, 1, 1, 1, NULL, 'legacy orphan', 'unknown'), "
                "(3, 1, 1, 1, NULL, 'property context', 'unknown')"
            ))
            connection.execute(text(
                "INSERT INTO property_definitions (id, code, display_name, value_kind, is_active) "
                "VALUES (1, 'test_density', 'test density', 'number', 1)"
            ))
            connection.execute(text(
                "INSERT INTO superconductor_properties "
                "(id, paper_id, paper_revision, material_state_id, calculation_context_id, "
                "property_definition_id, material_raw, name_raw, value_raw, source_fingerprint) "
                "VALUES (1, 1, 1, 1, 3, 1, 'LaH10', 'test density', '1', :fingerprint)"
            ), {"fingerprint": "p" * 64})
            # 模拟约束投入前留下的错误关联；现有理论 Tc 和普通物性仍分别引用上下文 1、3。
            connection.execute(text("ALTER TABLE tc_results DROP CHECK ck_tc_results_context_kind"))
            connection.execute(text(
                "ALTER TABLE tc_results ADD CONSTRAINT ck_tc_results_context_kind CHECK (1 = 1)"
            ))
            connection.execute(text(
                "INSERT INTO tc_results "
                "(id, paper_id, paper_revision, material_state_id, calculation_context_id, "
                "experimental_context_id, result_kind, tc_method, tc_value_k, value_raw, "
                "unit_raw, source_fingerprint, is_representative) "
                "VALUES "
                "(2, 1, 1, 1, 1, 1, 'theoretical', 'experimental', 251, '251 K', 'K', :first, 0), "
                "(3, 1, 1, 1, 2, 1, 'theoretical', 'experimental', 252, '252 K', 'K', :second, 0)"
            ), {"first": "c" * 64, "second": "d" * 64})

        command.upgrade(config, "experimental_tc_context")

        with engine.connect() as connection:
            migrated = connection.execute(text(
                "SELECT id, result_kind, calculation_context_id, experimental_context_id "
                "FROM tc_results WHERE id IN (2, 3) ORDER BY id"
            )).all()
            assert migrated == [(2, "experimental", None, 1), (3, "experimental", None, 1)]
            context_ids = connection.execute(text(
                "SELECT id FROM calculation_contexts ORDER BY id"
            )).scalars().all()
            assert context_ids == [1, 3]

        with pytest.raises(DBAPIError):
            with engine.begin() as connection:
                connection.execute(text(
                    "INSERT INTO tc_results "
                    "(id, paper_id, paper_revision, material_state_id, calculation_context_id, "
                    "experimental_context_id, result_kind, tc_method, tc_value_k, value_raw, "
                    "unit_raw, source_fingerprint, is_representative) "
                    "VALUES (4, 1, 1, 1, 1, 1, 'theoretical', 'experimental', 253, "
                    "'253 K', 'K', :fingerprint, 0)"
                ), {"fingerprint": "e" * 64})
    finally:
        _drop_all_tables(engine)
        engine.dispose()


def _drop_all_tables(engine):
    inspector = inspect(engine)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspector.get_table_names():
            connection.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def _seed_constraint_rows(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO users
                    (id, email, username, password_hash, real_name, role,
                     is_approved, is_email_verified, username_change_allowed)
                VALUES
                    (1, 'schema@example.test', 'schema_user', 'hash', 'Schema',
                     'user', 0, 0, 0)
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO papers
                    (id, doi, title, authors, uploaded_by_user_id, review_status,
                     year, content_revision, approved_revision)
                VALUES
                    (1, '10.0000/schema', 'Schema paper', :authors, 1, 'pending', 2024, 1, NULL)
                """
            ),
            {"authors": json.dumps(["Schema"])},
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
                     pressure_value_gpa, state_kind)
                VALUES (1, 1, 1, 1, 200, 'theoretical')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO calculation_contexts
                    (id, paper_id, paper_revision, material_state_id, structure_id,
                     missing_structure_reason, phonon_nuclear_treatment)
                VALUES (1, 1, 1, 1, NULL, '论文未报告结构', 'unknown')
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
                INSERT INTO tc_results
                    (id, paper_id, paper_revision, material_state_id,
                     calculation_context_id, result_kind, tc_method, tc_value_k,
                     value_raw, unit_raw, source_fingerprint, is_representative)
                VALUES
                    (1, 1, 1, 1, 1, 'theoretical', 'mcmillan', 250,
                     '250 K', 'K', :fingerprint, 1)
                """
            ),
            {"fingerprint": "b" * 64},
        )


def _assert_main_file_uniqueness(engine):
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO paper_files
                        (id, paper_id, paper_revision, role, original_filename,
                         stored_path, sha256, size, sort_order)
                    VALUES
                        (2, 1, 1, 'main', 'second.pdf', '/papers/1/second.pdf',
                         :sha256, 100, 1)
                    """
                ),
                {"sha256": "c" * 64},
            )


def _assert_representative_tc_uniqueness(engine):
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO tc_results
                        (id, paper_id, paper_revision, material_state_id,
                         calculation_context_id, result_kind, tc_method, tc_value_k,
                         value_raw, unit_raw, source_fingerprint, is_representative)
                    VALUES
                        (2, 1, 1, 1, 1, 'theoretical', 'mcmillan', 255,
                         '255 K', 'K', :fingerprint, 1)
                    """
                ),
                {"fingerprint": "d" * 64},
            )


def _assert_tc_is_not_a_general_property(engine):
    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO property_definitions
                        (id, code, display_name, canonical_unit, value_kind)
                    VALUES (1, 'tc', 'Critical temperature', 'K', 'number')
                    """
                )
            )


def _assert_chunk_index_is_scoped_to_file(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO paper_files
                    (id, paper_id, paper_revision, role, original_filename,
                     stored_path, sha256, size, sort_order)
                VALUES
                    (2, 1, 1, 'supplementary', 'supp.pdf', '/papers/1/supp.pdf',
                     :sha256, 80, 1)
                """
            ),
            {"sha256": "e" * 64},
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_chunks
                    (id, paper_id, paper_revision, paper_file_id, chunk_index, content)
                VALUES (1, 1, 1, 1, 0, 'main chunk')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO paper_chunks
                    (id, paper_id, paper_revision, paper_file_id, chunk_index, content)
                VALUES (2, 1, 1, 2, 0, 'supplementary chunk')
                """
            )
        )

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO paper_chunks
                        (id, paper_id, paper_revision, paper_file_id, chunk_index, content)
                    VALUES (3, 1, 1, 1, 0, 'duplicate main chunk index')
                    """
                )
            )


def _assert_cross_paper_evidence_is_rejected(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO papers
                    (id, doi, title, authors, year, uploaded_by_user_id, review_status,
                     content_revision, approved_revision)
                VALUES
                    (2, '10.0000/schema-2', 'Second paper', :authors, 2024, 1,
                     'pending', 1, NULL)
                """
            ),
            {"authors": json.dumps(["Schema Two"])},
        )

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO paper_evidences
                        (id, paper_id, paper_revision, paper_chunk_id,
                         field_path, quote)
                    VALUES (1, 2, 1, 1, 'tc_results[0].tc_value_k', '250 K')
                    """
                )
            )


def _assert_tc_contexts_are_exclusive(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO experimental_contexts
                    (id, paper_id, paper_revision, material_state_id, tc_criterion)
                VALUES (1, 1, 1, 1, 'zero_resistance')
                """
            )
        )

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO tc_results
                        (id, paper_id, paper_revision, material_state_id,
                         calculation_context_id, experimental_context_id,
                         result_kind, tc_method, tc_value_k, value_raw, unit_raw,
                         source_fingerprint, is_representative)
                    VALUES
                        (2, 1, 1, 1, 1, 1, 'theoretical', 'mcmillan', 245,
                         '245 K', 'K', :fingerprint, 0)
                    """
                ),
                {"fingerprint": "f" * 64},
            )


def _assert_same_pressure_states_and_structures_are_independent(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO material_states
                    (id, paper_id, paper_revision, superconductor_id,
                     pressure_value_gpa, state_kind)
                VALUES (2, 1, 1, 1, 200, 'theoretical')
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO structure_models
                    (id, paper_id, paper_revision, material_state_id,
                     structure_format, structure_text, structure_hash,
                     nuclear_treatment)
                VALUES
                    (1, 1, 1, 1, 'cif', 'state one', :hash_one, 'unknown'),
                    (2, 1, 1, 2, 'cif', 'state two', :hash_two, 'unknown')
                """
            ),
            {"hash_one": "1" * 64, "hash_two": "2" * 64},
        )


def _assert_history_event_survives_revision_change(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                """
                INSERT INTO paper_history_events
                    (id, paper_id, paper_revision, event_type, actor_user_id,
                     actor_username_snapshot, review_status)
                VALUES (1, 1, 1, 'reviewed', 1, 'reviewer', 'approved')
                """
            )
        )
        connection.execute(text("DELETE FROM tc_results WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM experimental_contexts WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM calculation_contexts WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM structure_models WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM material_states WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM paper_chunks WHERE paper_id = 1"))
        connection.execute(text("DELETE FROM paper_files WHERE paper_id = 1"))
        connection.execute(
            text(
                """
                UPDATE papers
                SET review_status = 'pending', approved_revision = NULL,
                    content_revision = 2
                WHERE id = 1
                """
            )
        )

        paper_revision = connection.execute(
            text("SELECT content_revision FROM papers WHERE id = 1")
        ).scalar_one()
        event_revision = connection.execute(
            text("SELECT paper_revision FROM paper_history_events WHERE id = 1")
        ).scalar_one()

        assert paper_revision == 2
        assert event_revision == 1

    with pytest.raises(DBAPIError):
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM papers WHERE id = 1"))
