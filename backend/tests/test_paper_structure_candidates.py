"""Issue #76：论文结构补传端点测试（T031，契约 C2）。

Spec: docs/specs/76-review-scientific-data-editing/spec.md（FR-009、FR-010）
契约: docs/specs/76-review-scientific-data-editing/contracts/scientific-draft-api.md（C2）

在 FRESH_MYSQL_DATABASE_URL 指向的隔离空库上验证：

- 合法 CIF 产出候选且不写入 structure_models。
- 非法文件 400 且不写库。
- 材料状态下标越界 400。
"""
import asyncio
import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[2]

_fresh_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
if _fresh_url:
    database_name = make_url(_fresh_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"
    os.environ["DATABASE_URL"] = _fresh_url
    os.environ["RAG_DATABASE_URL"] = _fresh_url
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

pytestmark = pytest.mark.skipif(
    not _fresh_url, reason="仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收"
)

CIF = b"""data_si
_cell_length_a 5.4307
_cell_length_b 5.4307
_cell_length_c 5.4307
_cell_angle_alpha 90
_cell_angle_beta 90
_cell_angle_gamma 90
loop_
_atom_site_label
_atom_site_type_symbol
_atom_site_fract_x
_atom_site_fract_y
_atom_site_fract_z
Si1 Si 0 0 0
Si2 Si 0.25 0.25 0.25
"""

BROKEN_CIF = b"data_broken\n_cell_length_a nope\n"


def _config(database_url):
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def _drop_all(engine):
    inspector = inspect(engine)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspector.get_table_names():
            connection.execute(text(f"DROP TABLE IF EXISTS `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


def _seed_paper(engine):
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, username, password_hash, real_name, role,"
                " is_approved, is_email_verified, username_change_allowed) VALUES"
                " (1, 'admin@example.test', 'admin', 'hash', 'Admin', 'admin', 1, 1, 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO papers (id, doi, title, authors, uploaded_by_user_id,"
                " review_status, content_revision, approved_revision, paper_type,"
                " research_materials) VALUES"
                " (10, '10.0000/structure', 'Structure paper', :authors, 1,"
                " 'pending', 1, NULL, 'experimental', :materials)"
            ),
            {"authors": json.dumps(["Author"]), "materials": json.dumps(["Si"])},
        )
        connection.execute(
            text(
                "INSERT INTO chemical_systems (id, system_key, elements_list, element_count)"
                " VALUES (1, 'Si', :elements, 1)"
            ),
            {"elements": json.dumps(["Si"])},
        )
        connection.execute(
            text(
                "INSERT INTO superconductors (id, chemical_system_id, chemical_formula,"
                " formula_normalized, composition_key, display_name, elements_list,"
                " composition, element_ratio) VALUES"
                " (1, 1, 'Si', 'Si', 'Si:1', 'Si', :elements, :composition, :ratio)"
            ),
            {
                "elements": json.dumps(["Si"]),
                "composition": json.dumps({"Si": 1}),
                "ratio": json.dumps({"Si": 1}),
            },
        )
        connection.execute(
            text(
                "INSERT INTO material_states (id, paper_id, paper_revision, superconductor_id,"
                " material_dimensionality, superconductor_kind, crystal_system, state_kind,"
                " created_at, updated_at) VALUES"
                " (1, 10, 1, 1, 'three_dimensional', 'unknown', 'cubic', 'theoretical', NOW(), NOW())"
            )
        )


def _call(filename, raw, index=0):
    from backend.api.rag import _build_paper_structure_candidate

    async_url = os.environ["RAG_DATABASE_URL"].replace("mysql+pymysql://", "mysql+asyncmy://")

    async def run():
        engine = create_async_engine(async_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                try:
                    result = await _build_paper_structure_candidate(
                        session, 10, index, filename, raw
                    )
                    return result, None
                except HTTPException as exc:
                    return None, exc
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _clear_data(engine):
    inspector = inspect(engine)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspector.get_table_names():
            if table != "alembic_version":
                connection.execute(text(f"DELETE FROM `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(scope="module")
def migrated_engine():
    engine = create_engine(_fresh_url, future=True)
    _drop_all(engine)
    command.upgrade(_config(_fresh_url), "head")
    yield engine
    _drop_all(engine)
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_data(migrated_engine):
    _clear_data(migrated_engine)
    yield


def test_valid_cif_produces_candidate_without_writing_structure(migrated_engine):
    """T031-1：合法 CIF 产出候选，且不写入 structure_models。"""
    _seed_paper(migrated_engine)

    data, error = _call("test.cif", CIF)
    assert error is None, error
    body = data["data"]
    assert body["status"] == "valid"
    assert body["structure_format"] == "cif"
    assert body["material_state_index"] == 0
    assert body["validation"]["ase_valid"] is True
    assert body["candidate_id"]

    with migrated_engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM structure_models")).scalar()
        assert count == 0, "C2 只产出候选，不得写库"


def test_invalid_file_returns_400_without_writing(migrated_engine):
    """T031-2：非法结构文件 400 且不写库。"""
    _seed_paper(migrated_engine)

    data, error = _call("broken.cif", BROKEN_CIF)
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "structure_validation_failed"

    with migrated_engine.connect() as connection:
        count = connection.execute(text("SELECT COUNT(*) FROM structure_models")).scalar()
        assert count == 0


def test_out_of_range_state_index_returns_400(migrated_engine):
    """T031-3：材料状态下标越界 400。"""
    _seed_paper(migrated_engine)

    data, error = _call("test.cif", CIF, index=5)
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "invalid_material_state_index"


def _call_representations(structure_id=1):
    from backend.api.rag import _structure_representations

    async_url = os.environ["RAG_DATABASE_URL"].replace("mysql+pymysql://", "mysql+asyncmy://")

    async def run():
        engine = create_async_engine(async_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                try:
                    result = await _structure_representations(session, 10, structure_id)
                    return result, None
                except HTTPException as exc:
                    return None, exc
        finally:
            await engine.dispose()

    return asyncio.run(run())


def _seed_structure(engine):
    """在既有 seed 基础上追加一条已落库结构（惯用胞 CIF）。"""
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO structure_models (id, paper_id, paper_revision, material_state_id,"
                " parent_structure_id, structure_format, structure_text, structure_hash,"
                " nuclear_treatment, created_at, updated_at) VALUES"
                " (1, 10, 1, 1, NULL, 'cif', :text, :hash, 'unknown', NOW(), NOW())"
            ),
            {
                "text": CIF.decode("utf-8"),
                "hash": "rep-hash-1",
            },
        )


def test_structure_representations_returns_full_cell_and_format_set(migrated_engine):
    """T004（#78）：表示端点返回 primitive/conventional × cif/poscar 完整表示。"""
    _seed_paper(migrated_engine)
    _seed_structure(migrated_engine)

    data, error = _call_representations(1)
    assert error is None, error
    body = data["data"]
    assert body["structure_id"] == 1
    reps = body["representations"]
    for cell in ("conventional", "primitive"):
        assert cell in reps, f"缺少 {cell} 表示"
        for fmt in ("cif", "poscar"):
            assert fmt in reps[cell], f"缺少 {cell}/{fmt}"
            assert reps[cell][fmt].get("text"), f"{cell}/{fmt} 文本为空"
    assert body["validation"]["atom_count"] == 2


def test_structure_representations_not_found_or_failed(migrated_engine):
    """T005（#78）：结构不存在 404；内容为空生成失败 400。"""
    _seed_paper(migrated_engine)
    _seed_structure(migrated_engine)

    data, error = _call_representations(999)
    assert error is not None and error.status_code == 404
    assert error.detail["code"] == "structure_not_found"

    with migrated_engine.begin() as connection:
        connection.execute(text("UPDATE structure_models SET structure_text = '' WHERE id = 1"))
    data, error = _call_representations(1)
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "structure_representation_failed"
