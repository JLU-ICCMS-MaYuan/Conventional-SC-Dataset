"""Issue #90 在真实隔离 MySQL 上的分阶段迁移与恢复验收。

测试始终创建并删除名称以 ``scwiki_issue90_test_`` 开头的临时数据库。连接来源按
优先级为显式 ``ISSUE90_MYSQL_TEST_URL``，或本项目 ``.env`` 中可识别的本地 3307
MySQL；两者均不会直接清空 URL 指向的现有数据库。
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import importlib
import os
from pathlib import Path
import re
from typing import Any, Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy import MetaData, create_engine, inspect, select, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.pool import NullPool


REPO_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PREFIX = "scwiki_issue90_test_"
BASE_REVISION = "networked_news_discovery"
EXPAND_REVISION = "issue90_expand_v1"
COPY_REVISION = "issue90_copy_v1"
CONTRACT_REVISION = "issue90_contract_v1"

# 导入迁移服务时 backend.database 需要显式配置；专项测试本身始终把真实连接传给服务。
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/scwiki-issue90-migration-import.db")
os.environ.setdefault("JWT_SECRET_KEY", "issue90-test-only")


@dataclass(frozen=True)
class MySQLTestDatabase:
    url: URL
    engine: Engine


def _mysql_server_url() -> URL | None:
    explicit = os.environ.get("ISSUE90_MYSQL_TEST_URL")
    if explicit:
        url = make_url(explicit)
        if not url.drivername.startswith("mysql+"):
            raise AssertionError("ISSUE90_MYSQL_TEST_URL 必须使用显式 MySQL 驱动")
        return url

    values = dotenv_values(REPO_ROOT / ".env")
    configured = values.get("DATABASE_URL")
    if not configured:
        return None
    url = make_url(str(configured))
    if (
        not url.drivername.startswith("mysql+")
        or url.host not in {"127.0.0.1", "localhost"}
        or url.port != 3307
    ):
        return None

    mysql_socket = REPO_ROOT / ".local/run/mysql.sock"
    if mysql_socket.is_socket():
        return URL.create(
            drivername=url.drivername,
            username="root",
            host=url.host,
            port=url.port,
            query={"unix_socket": str(mysql_socket)},
        )
    return url


def _assert_generated_database_name(name: str) -> None:
    assert name.startswith(DATABASE_PREFIX)
    assert re.fullmatch(r"[a-z0-9_]+", name)


@contextmanager
def _database_environment(url: URL) -> Iterator[None]:
    previous = {
        key: os.environ.get(key)
        for key in ("DATABASE_URL", "RAG_DATABASE_URL")
    }
    rendered = url.render_as_string(hide_password=False).replace("%2F", "/")
    os.environ["DATABASE_URL"] = rendered
    os.environ["RAG_DATABASE_URL"] = rendered
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _alembic_config(url: URL) -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    rendered = url.render_as_string(hide_password=False).replace("%2F", "/")
    config.set_main_option("sqlalchemy.url", rendered.replace("%", "%%"))
    return config


def _upgrade(url: URL, revision: str) -> None:
    with _database_environment(url):
        command.upgrade(_alembic_config(url), revision)


def _drop_all_tables(engine: Engine) -> None:
    table_names = inspect(engine).get_table_names()
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table_name in table_names:
            assert re.fullmatch(r"[a-zA-Z0-9_]+", table_name)
            connection.execute(text(f"DROP TABLE IF EXISTS `{table_name}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(scope="module")
def issue90_mysql() -> Iterator[MySQLTestDatabase]:
    server_url = _mysql_server_url()
    if server_url is None:
        pytest.skip(
            "需要 ISSUE90_MYSQL_TEST_URL，或可识别的项目本地 127.0.0.1:3307 MySQL"
        )

    database_name = f"{DATABASE_PREFIX}{os.getpid()}_{uuid4().hex[:10]}"
    _assert_generated_database_name(database_name)
    admin_url = server_url.set(database="mysql")
    admin_engine = create_engine(admin_url, future=True, poolclass=NullPool)
    try:
        with admin_engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(
                    f"CREATE DATABASE `{database_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
    except OperationalError as exc:
        admin_engine.dispose()
        pytest.skip(f"无法创建隔离 Issue #90 MySQL 数据库: {exc.orig}")

    database_url = server_url.set(database=database_name)
    engine = create_engine(database_url, future=True, poolclass=NullPool)
    try:
        yield MySQLTestDatabase(url=database_url, engine=engine)
    finally:
        engine.dispose()
        _assert_generated_database_name(database_name)
        with admin_engine.connect() as connection:
            connection.execution_options(isolation_level="AUTOCOMMIT").execute(
                text(f"DROP DATABASE IF EXISTS `{database_name}`")
            )
        admin_engine.dispose()


def _insert(connection, metadata: MetaData, table_name: str, **values: Any) -> None:
    table = metadata.tables[table_name]
    unknown = set(values) - set(table.c.keys())
    assert not unknown, f"{table_name} fixture 使用了不存在的列: {sorted(unknown)}"
    connection.execute(table.insert().values(**values))


def _seed_legacy_graph(engine: Engine) -> None:
    metadata = MetaData()
    metadata.reflect(bind=engine)
    with engine.begin() as connection:
        _insert(
            connection,
            metadata,
            "users",
            id=1,
            email="issue90@example.test",
            username="issue90_reviewer",
            password_hash="test",
            real_name="Issue 90",
            role="admin",
            is_approved=True,
            is_email_verified=True,
            username_change_allowed=True,
            account_status="active",
        )
        for paper_id in (1, 2):
            _insert(
                connection,
                metadata,
                "papers",
                id=paper_id,
                doi=f"10.9000/issue90-{paper_id}",
                title=f"Issue 90 paper {paper_id}",
                authors=["Test Author"],
                year=2026,
                uploaded_by_user_id=1,
                review_status="approved",
                content_revision=1,
                approved_revision=1,
                superconductor_kind="conventional",
            )

        _insert(
            connection,
            metadata,
            "chemical_systems",
            id=10,
            system_key="H-La",
            elements_list=["H", "La"],
            element_count=2,
        )
        _insert(
            connection,
            metadata,
            "superconductors",
            id=10,
            chemical_system_id=10,
            chemical_formula="LaH10",
            formula_normalized="LaH10",
            composition_key="H:10|La:1",
            display_name="LaH10",
            elements_list=["H", "La"],
            composition={"H": 10, "La": 1},
            element_ratio={"H": 10 / 11, "La": 1 / 11},
        )
        for paper_id, state_id, pressure in ((1, 101, 170), (2, 201, 180)):
            _insert(
                connection,
                metadata,
                "material_states",
                id=state_id,
                paper_id=paper_id,
                paper_revision=1,
                superconductor_id=10,
                element_count=2,
                material_dimensionality="three_dimensional",
                pressure_value_gpa=pressure,
                state_kind="mixed" if paper_id == 2 else "theoretical",
                crystal_system="cubic",
            )
            _insert(
                connection,
                metadata,
                "paper_files",
                id=paper_id,
                paper_id=paper_id,
                paper_revision=1,
                role="main",
                original_filename=f"paper-{paper_id}.pdf",
                stored_path=f"papers/{paper_id}/paper.pdf",
                sha256=f"{paper_id}" * 64,
                size=1024,
                media_type="application/pdf",
                sort_order=0,
            )
            _insert(
                connection,
                metadata,
                "paper_chunks",
                id=paper_id,
                paper_id=paper_id,
                paper_revision=1,
                paper_file_id=paper_id,
                chunk_index=0,
                section_name="Results",
                content=f"LaH10 evidence for paper {paper_id}",
                page_start=1,
                page_end=1,
            )
            _insert(
                connection,
                metadata,
                "paper_evidences",
                id=paper_id,
                paper_id=paper_id,
                paper_revision=1,
                paper_chunk_id=paper_id,
                field_path="material_states[0].tc_results[0]",
                section="Results",
                page_start=1,
                page_end=1,
                quote=f"LaH10 Tc evidence {paper_id}",
            )

        for paper_id, state_id, context_id, tc_id, tc_value in (
            (1, 101, 1001, 10001, 250),
            (2, 201, 2001, 20001, 240),
        ):
            _insert(
                connection,
                metadata,
                "calculation_contexts",
                id=context_id,
                paper_id=paper_id,
                paper_revision=1,
                material_state_id=state_id,
                missing_structure_reason="论文未提供结构文件",
                phonon_nuclear_treatment="harmonic",
                electronic_method="DFT",
                exchange_correlation="PBE",
                lambda_ep=2.2 + paper_id / 10,
                omega_log_k=1100 + paper_id,
                mu_star=0.1,
                k_grid="24x24x24",
                q_grid="6x6x6",
                calculation_code="Quantum ESPRESSO",
            )
            _insert(
                connection,
                metadata,
                "tc_results",
                id=tc_id,
                paper_id=paper_id,
                paper_revision=1,
                material_state_id=state_id,
                calculation_context_id=context_id,
                result_kind="theoretical",
                tc_method="allen_dynes",
                tc_value_k=tc_value,
                value_raw=str(tc_value),
                unit_raw="K",
                source_fingerprint=f"tc-{paper_id}".ljust(64, "0"),
                is_representative=True,
            )
            _insert(
                connection,
                metadata,
                "tc_result_evidences",
                tc_result_id=tc_id,
                paper_evidence_id=paper_id,
                paper_id=paper_id,
                paper_revision=1,
                evidence_role="primary",
            )

        _insert(
            connection,
            metadata,
            "experimental_contexts",
            id=2002,
            paper_id=2,
            paper_revision=1,
            material_state_id=201,
            tc_criterion="resistance_onset",
            measurement_method="four_probe",
            sample_label="LaH10-B",
        )
        _insert(
            connection,
            metadata,
            "tc_results",
            id=20002,
            paper_id=2,
            paper_revision=1,
            material_state_id=201,
            experimental_context_id=2002,
            result_kind="experimental",
            tc_method="experimental",
            tc_value_k=232,
            value_raw="232",
            unit_raw="K",
            source_fingerprint="tc-exp-2".ljust(64, "0"),
            is_representative=True,
        )
        _insert(
            connection,
            metadata,
            "tc_result_evidences",
            tc_result_id=20002,
            paper_evidence_id=2,
            paper_id=2,
            paper_revision=1,
            evidence_role="primary",
        )

        _insert(
            connection,
            metadata,
            "property_definitions",
            id=90,
            code="density_of_states_issue90",
            display_name="density of states",
            canonical_unit="states/eV",
            value_kind="number",
            is_active=True,
        )
        for paper_id, state_id, property_id, value in (
            (1, 101, 10001, 3.1),
            (2, 201, 20001, 3.2),
        ):
            _insert(
                connection,
                metadata,
                "superconductor_properties",
                id=property_id,
                paper_id=paper_id,
                paper_revision=1,
                material_state_id=state_id,
                property_definition_id=90,
                material_raw="LaH10",
                name_raw="density of states",
                value_raw=str(value),
                unit_raw="states/eV",
                value_number=value,
                canonical_unit="states/eV",
                source_fingerprint=f"property-{paper_id}".ljust(64, "0"),
            )
            _insert(
                connection,
                metadata,
                "superconductor_property_evidences",
                superconductor_property_id=property_id,
                paper_evidence_id=paper_id,
                paper_id=paper_id,
                paper_revision=1,
                evidence_role="primary",
            )


@pytest.fixture
def legacy_mysql(issue90_mysql: MySQLTestDatabase) -> MySQLTestDatabase:
    _drop_all_tables(issue90_mysql.engine)
    _upgrade(issue90_mysql.url, BASE_REVISION)
    _seed_legacy_graph(issue90_mysql.engine)
    return issue90_mysql


def _migration_script():
    return importlib.import_module("backend.scripts.migrate_issue90_properties")


def _migration_service():
    return importlib.import_module("backend.services.issue90_migration")


def _rows(engine: Engine, table_name: str) -> list[dict[str, Any]]:
    metadata = MetaData()
    metadata.reflect(bind=engine, only=[table_name])
    table = metadata.tables[table_name]
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(select(table)).mappings()]


def _advance_and_persist(connection, service, checkpoint, target, **flags):
    checkpoint = service.advance(checkpoint, target, **flags)
    service.persist_checkpoint(connection, checkpoint)
    return checkpoint


def test_copy_splits_shared_material_and_is_idempotent(
    legacy_mysql: MySQLTestDatabase,
) -> None:
    _upgrade(legacy_mysql.url, EXPAND_REVISION)
    migration = _migration_script()

    with legacy_mysql.engine.begin() as connection:
        dry_run = migration.run_migration(connection, "copy", dry_run=True)
    assert dry_run["copied"] == 5
    assert _rows(legacy_mysql.engine, "property_records") == []
    assert _rows(legacy_mysql.engine, "issue90_property_migration_map") == []

    with legacy_mysql.engine.begin() as connection:
        first = migration.run_migration(connection, "copy")
        clean = migration.run_migration(connection, "reconcile")
        second = migration.run_migration(connection, "copy")

    assert first["copied"] == 5
    assert first["errors"] == []
    assert clean["checked"] == 5
    assert clean["errors"] == []
    assert second["copied"] == 0
    assert second["updated"] == 0
    assert second["deleted"] == 0
    assert second["errors"] == []

    shadow_materials = _rows(legacy_mysql.engine, "issue90_superconductors")
    assert len(shadow_materials) == 2
    assert {row["paper_id"] for row in shadow_materials} == {1, 2}
    assert len({row["id"] for row in shadow_materials}) == 2
    material_mappings = [
        row
        for row in _rows(legacy_mysql.engine, "issue90_property_migration_map")
        if row["source_table"] == "superconductors"
    ]
    assert {(row["source_id"], row["paper_id"]) for row in material_mappings} == {
        (10, 1),
        (10, 2),
    }
    assert {row["target_id"] for row in material_mappings} == {
        row["id"] for row in shadow_materials
    }

    records = _rows(legacy_mysql.engine, "property_records")
    assert len(records) == 5
    predicted = next(row for row in records if row["record_key"] == "legacy-tc-10001")
    assert float(predicted["value_number"]) == 250
    assert predicted["payload_json"]["calculation_conditions"]["k_grid"] == "24x24x24"
    assert float(
        predicted["payload_json"]["parameters"]["mu_star"]["value_number"]
    ) == pytest.approx(0.1)

    evidence_links = _rows(legacy_mysql.engine, "property_record_evidences")
    assert len(evidence_links) == 5
    assert {(row["paper_id"], row["paper_revision"]) for row in evidence_links} == {
        (1, 1),
        (2, 1),
    }


def test_reconcile_detects_core_payload_and_evidence_drift(
    legacy_mysql: MySQLTestDatabase,
) -> None:
    _upgrade(legacy_mysql.url, EXPAND_REVISION)
    migration = _migration_script()
    with legacy_mysql.engine.begin() as connection:
        migration.run_migration(connection, "copy")
        connection.execute(
            text(
                "UPDATE property_records SET value_number = 999, "
                "payload_json = JSON_SET(payload_json, '$.parameters.mu_star', 0.9) "
                "WHERE record_key = 'legacy-tc-10001'"
            )
        )
        connection.execute(
            text(
                "DELETE FROM property_record_evidences "
                "WHERE record_id = (SELECT id FROM property_records "
                "WHERE record_key = 'legacy-tc-10001')"
            )
        )
        report = migration.run_migration(connection, "reconcile")

    assert report["errors"]
    serialized = repr(report["errors"])
    assert "value_number" in serialized
    assert "payload.parameters.mu_star" in serialized
    assert "evidence" in serialized.lower()
    mapping = next(
        row
        for row in _rows(legacy_mysql.engine, "issue90_property_migration_map")
        if row["source_table"] == "tc_results" and row["source_id"] == 10001
    )
    assert mapping["status"] == "error"
    assert mapping["error_message"]


def test_final_sync_applies_updates_deletes_and_revision_changes(
    legacy_mysql: MySQLTestDatabase,
) -> None:
    _upgrade(legacy_mysql.url, EXPAND_REVISION)
    migration = _migration_script()
    with legacy_mysql.engine.begin() as connection:
        migration.run_migration(connection, "copy")
        connection.execute(
            text("UPDATE tc_results SET tc_value_k = 255, value_raw = '255' WHERE id = 10001")
        )
        connection.execute(text("DELETE FROM superconductor_properties WHERE id = 10001"))
        connection.execute(
            text(
                "UPDATE papers SET content_revision = 2, approved_revision = 2 "
                "WHERE id = 2"
            )
        )
        connection.execute(
            text(
                "INSERT INTO superconductor_properties "
                "(id, paper_id, paper_revision, material_state_id, property_definition_id, "
                "material_raw, name_raw, value_raw, unit_raw, value_number, canonical_unit, "
                "source_fingerprint) VALUES "
                "(20002, 2, 2, 201, 90, 'LaH10', 'density of states', '3.4', "
                "'states/eV', 3.4, 'states/eV', :fingerprint)"
            ),
            {"fingerprint": "property-2-revision-2".ljust(64, "0")},
        )
        report = migration.run_migration(connection, "final-sync")
        reconciled = migration.run_migration(connection, "reconcile")

    assert report["updated"] >= 1
    assert report["deleted"] >= 1
    assert report["copied"] >= 1
    assert report["errors"] == []
    assert reconciled["errors"] == []

    records = _rows(legacy_mysql.engine, "property_records")
    updated = next(row for row in records if row["record_key"] == "legacy-tc-10001")
    assert float(updated["value_number"]) == 255
    assert not any(row["record_key"] == "legacy-property-10001" for row in records)
    assert not any(row["paper_id"] == 2 and row["paper_revision"] == 1 for row in records)
    assert any(row["record_key"] == "legacy-property-20002" for row in records)


def test_checkpoint_order_persistence_and_pre_write_recovery(
    legacy_mysql: MySQLTestDatabase,
) -> None:
    _upgrade(legacy_mysql.url, EXPAND_REVISION)
    service = _migration_service()
    with legacy_mysql.engine.begin() as connection:
        checkpoint = service.load_checkpoint(connection)
        assert checkpoint.phase == service.MigrationPhase.EXPAND
        with pytest.raises(service.MigrationBlocked):
            service.advance(checkpoint, service.MigrationPhase.READ_SWITCH)

        checkpoint = _advance_and_persist(
            connection, service, checkpoint, service.MigrationPhase.COPY
        )
        checkpoint = _advance_and_persist(
            connection,
            service,
            checkpoint,
            service.MigrationPhase.RECONCILE,
            reconcile_ok=True,
        )
        checkpoint = _advance_and_persist(
            connection, service, checkpoint, service.MigrationPhase.READ_SWITCH
        )
        loaded = service.load_checkpoint(connection)
        assert loaded.phase == service.MigrationPhase.READ_SWITCH
        assert loaded.writes_blocked is True
        assert loaded.reads_target is True

        recovered = service.recover(
            connection, target=service.MigrationPhase.RECONCILE
        )
        assert recovered.phase == service.MigrationPhase.RECONCILE
        assert recovered.reconciled is True
        assert recovered.writes_blocked is False
        assert recovered.reads_target is False
        assert recovered.writes_target is False
        assert service.load_checkpoint(connection) == recovered

        checkpoint = _advance_and_persist(
            connection, service, recovered, service.MigrationPhase.READ_SWITCH
        )
        checkpoint = _advance_and_persist(
            connection, service, checkpoint, service.MigrationPhase.WRITE_SWITCH
        )
        with pytest.raises(service.MigrationBlocked):
            service.recover(connection, target=service.MigrationPhase.RECONCILE)


def test_contract_requires_confirmation_and_observed_checkpoint(
    legacy_mysql: MySQLTestDatabase,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _upgrade(legacy_mysql.url, COPY_REVISION)
    migration = _migration_script()
    service = _migration_service()
    with legacy_mysql.engine.begin() as connection:
        migration.run_migration(connection, "copy")

    monkeypatch.delenv("ISSUE90_CONTRACT_CONFIRMED", raising=False)
    with pytest.raises(RuntimeError, match="ISSUE90_CONTRACT_CONFIRMED"):
        _upgrade(legacy_mysql.url, CONTRACT_REVISION)

    assert "tc_results" in inspect(legacy_mysql.engine).get_table_names()
    with legacy_mysql.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == COPY_REVISION

    with legacy_mysql.engine.begin() as connection:
        checkpoint = service.load_checkpoint(connection)
        for target, flags in (
            (service.MigrationPhase.RECONCILE, {"reconcile_ok": True}),
            (service.MigrationPhase.READ_SWITCH, {}),
            (service.MigrationPhase.WRITE_SWITCH, {}),
            (service.MigrationPhase.OBSERVE, {"observe_ok": True}),
        ):
            checkpoint = _advance_and_persist(
                connection, service, checkpoint, target, **flags
            )

    monkeypatch.setenv("ISSUE90_CONTRACT_CONFIRMED", "1")
    _upgrade(legacy_mysql.url, CONTRACT_REVISION)

    tables = set(inspect(legacy_mysql.engine).get_table_names())
    assert {
        "tc_results",
        "superconductor_properties",
        "calculation_contexts",
        "experimental_contexts",
    }.isdisjoint(tables)
    assert {
        "property_modules",
        "property_records",
        "form_definitions",
        "issue90_property_migration_map",
    } <= tables
    with legacy_mysql.engine.connect() as connection:
        assert connection.scalar(text("SELECT version_num FROM alembic_version")) == CONTRACT_REVISION
