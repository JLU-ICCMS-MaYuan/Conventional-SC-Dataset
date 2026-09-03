"""Issue #76：科学数据重写端点的行为测试（T022–T026、T035–T039）。

Spec: docs/specs/76-review-scientific-data-editing/spec.md
契约: docs/specs/76-review-scientific-data-editing/contracts/scientific-draft-api.md（C1）

在 FRESH_MYSQL_DATABASE_URL 指向的隔离空库上跑完整迁移到 head，经真实
FastAPI 路由（TestClient + 依赖覆盖）调用 PUT /api/rag/papers/{id}/scientific-draft：

- T022：pending 原地重建，content_revision / review_status 不变。
- T023：删除顺序正确（含 structure_models 自引用），重建后与请求体一致。
- T024：校验规则复用（缺化学式 / 缺家族 / 压强区间 → 400 且带序号）。
- T025：综述论文空 material_states 保存成功。
- T026：跨论文共享目录表行数不变。
- T035：approved 升版（版本递增、已批准标记清空、退回待审核），ck 约束成立。
- T036：升版后血缘表 paper_revision 全部为新版本、行数不变。
- T037：实际重写写入 paper_history_events。
- T038：重建失败整体回滚，论文保持原状。
- T039：rejected 论文 409。
"""
import json
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
import asyncio
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPO_ROOT = Path(__file__).resolve().parents[2]

_fresh_url = os.environ.get("FRESH_MYSQL_DATABASE_URL")
if _fresh_url:
    database_name = make_url(_fresh_url).database or ""
    assert "test" in database_name.lower(), "只允许连接名称含 test 的隔离数据库"
    # backend.rag.config 的 settings.database_url 优先读 RAG_DATABASE_URL
    # （.env 中的该值会盖过 DATABASE_URL），必须一并指向隔离库；
    # backend.security 需要 JWT_SECRET_KEY。三者都须在 import backend 前就位。
    os.environ["DATABASE_URL"] = _fresh_url
    os.environ["RAG_DATABASE_URL"] = _fresh_url
    os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret")

pytestmark = pytest.mark.skipif(
    not _fresh_url, reason="仅在提供 FRESH_MYSQL_DATABASE_URL 时运行隔离 MySQL 验收"
)

from backend.models import User  # noqa: E402

ADMIN_USER = User(
    id=1, email="admin@example.test", username="admin", password_hash="hash",
    role="admin", is_approved=True, is_email_verified=True,
    username_change_allowed=True, account_status="active",
)


def _call_endpoint(payload, paper_id: int = 10):
    """在自建 async engine（同一 event loop）内调用 C1 事务内实现。

    返回 (data, error)。不使用 TestClient：async engine 的连接绑定到创建它的
    event loop，TestClient 每次新建 loop 会触发跨 loop 复用错误。
    """
    from backend.api.rag import _rewrite_paper_scientific_draft_in_tx

    async_url = os.environ["RAG_DATABASE_URL"].replace("mysql+pymysql://", "mysql+asyncmy://")

    async def run():
        engine = create_async_engine(async_url)
        try:
            async with async_sessionmaker(engine, expire_on_commit=False)() as session:
                async with session.begin():
                    try:
                        result = await _rewrite_paper_scientific_draft_in_tx(
                            session, paper_id, payload, ADMIN_USER
                        )
                        return result, None
                    except HTTPException as exc:
                        return None, exc
        finally:
            await engine.dispose()

    return asyncio.run(run())


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


def _seed_paper(engine, *, review_status: str, paper_id: int = 10):
    """插入最小血缘链 + 科学实体图（含结构自引用），供重写与升版验证。"""
    approved_revision = 1 if review_status == "approved" else None
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
                "INSERT INTO papers (id, doi, title, authors, year, uploaded_by_user_id,"
                " review_status, content_revision, approved_revision, paper_type,"
                " research_materials) VALUES"
                " (:id, '10.0000/rewrite', 'Rewrite paper', :authors, 2024, 1,"
                " :status, 1, :approved, 'experimental', :materials)"
            ),
            {
                "id": paper_id,
                "authors": json.dumps(["Author"]),
                "status": review_status,
                "approved": approved_revision,
                "materials": json.dumps(["Sn"]),
            },
        )
        connection.execute(
            text(
                "INSERT INTO chemical_systems (id, system_key, elements_list, element_count)"
                " VALUES (1, 'Sn', :elements, 1)"
            ),
            {"elements": json.dumps(["Sn"])},
        )
        connection.execute(
            text(
                "INSERT INTO superconductors (id, chemical_system_id, chemical_formula,"
                " formula_normalized, composition_key, display_name, elements_list,"
                " composition, element_ratio) VALUES"
                " (1, 1, 'Sn', 'Sn', 'Sn:1', 'Sn', :elements, :composition, :ratio)"
            ),
            {
                "elements": json.dumps(["Sn"]),
                "composition": json.dumps({"Sn": 1}),
                "ratio": json.dumps({"Sn": 1}),
            },
        )
        connection.execute(
            text(
                "INSERT INTO material_families (id, code, name_zh, normalized_name, created_by_user_id)"
                " VALUES (1, 'elemental', '单质超导体', '单质超导体', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO structure_families (id, code, name_zh, normalized_name, created_by_user_id)"
                " VALUES (1, 'clathrate', '笼状结构', '笼状结构', NULL)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO paper_material_families"
                " (paper_id, paper_revision, material_family_id) VALUES (:pid, 1, 1)"
            ),
            {"pid": paper_id},
        )
        connection.execute(
            text(
                "INSERT INTO material_states (id, paper_id, paper_revision, superconductor_id,"
                " material_dimensionality, crystal_system, pressure_value_gpa, state_kind, created_at, updated_at)"
                " VALUES (1, :pid, 1, 1, 'three_dimensional',"
                " 'tetragonal', 0.001, 'experimental', NOW(), NOW())"
            ),
            {"pid": paper_id},
        )
        connection.execute(
            text(
                "INSERT INTO experimental_contexts (id, paper_id, paper_revision,"
                " material_state_id, structure_id, tc_criterion) VALUES"
                " (1, :pid, 1, 1, NULL, 'resistance_onset')"
            ),
            {"pid": paper_id},
        )
        connection.execute(
            text(
                "INSERT INTO tc_results (id, paper_id, paper_revision, material_state_id,"
                " experimental_context_id, result_kind, tc_method, tc_value_k, value_raw,"
                " unit_raw, source_fingerprint, is_representative) VALUES"
                " (1, :pid, 1, 1, 1, 'experimental', 'experimental', 3.78, '3.78', 'K',"
                " :fp, 1)"
            ),
            {"pid": paper_id, "fp": "f" * 64},
        )
        connection.execute(
            text(
                "INSERT INTO property_definitions (id, code, display_name, value_kind, is_active)"
                " VALUES (1, 'threshold_current', 'threshold current', 'number', 1)"
            )
        )
        connection.execute(
            text(
                "INSERT INTO superconductor_properties (id, paper_id, paper_revision,"
                " material_state_id, property_definition_id, material_raw, name_raw, value_raw,"
                " unit_raw, source_fingerprint) VALUES"
                " (1, :pid, 1, 1, 1, 'Sn', 'threshold current', '0.28', 'A', :fp)"
            ),
            {"pid": paper_id, "fp": "g" * 64},
        )
        # 两条结构：一条带自引用（parent），验证删除顺序先置空再删
        connection.execute(
            text(
                "INSERT INTO structure_models (id, paper_id, paper_revision, material_state_id,"
                " parent_structure_id, structure_format, structure_text, structure_hash,"
                " nuclear_treatment, created_at, updated_at) VALUES"
                " (1, :pid, 1, 1, NULL, 'cif', 'data_Sn_parent', :hash1, 'unknown', NOW(), NOW()),"
                " (2, :pid, 1, 1, 1, 'cif', 'data_Sn_child', :hash2, 'unknown', NOW(), NOW())"
            ),
            {"pid": paper_id, "hash1": "h1" * 32, "hash2": "h2" * 32},
        )
        connection.execute(
            text(
                "INSERT INTO material_state_structure_families (material_state_id,"
                " structure_family_id, is_primary) VALUES (1, 1, 1)"
            )
        )
        # 血缘链（T036 级联验证）
        connection.execute(
            text(
                "INSERT INTO paper_files (id, paper_id, paper_revision, role,"
                " original_filename, stored_path, sha256, size, sort_order) VALUES"
                " (1, :pid, 1, 'main', 'paper.pdf', '/papers/10/paper.pdf', :sha, 100, 0)"
            ),
            {"pid": paper_id, "sha": "a" * 64},
        )
        connection.execute(
            text(
                "INSERT INTO paper_chunks (id, paper_id, paper_revision, paper_file_id,"
                " chunk_index, content, created_at) VALUES"
                " (1, :pid, 1, 1, 0, 'chunk content', NOW())"
            ),
            {"pid": paper_id},
        )
        connection.execute(
            text(
                "INSERT INTO paper_evidences (id, paper_id, paper_revision, paper_chunk_id,"
                " field_path, quote) VALUES (1, :pid, 1, 1, 'paper.summary', 'quote')"
            ),
            {"pid": paper_id},
        )


def _count(engine, table):
    with engine.connect() as connection:
        return connection.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()


def _revisions(engine, table):
    with engine.connect() as connection:
        rows = connection.execute(
            text(f"SELECT paper_revision FROM {table} ORDER BY id")
        ).fetchall()
        return [row[0] for row in rows]


@pytest.fixture(scope="module")
def migrated_engine():
    database_url = _fresh_url
    engine = create_engine(database_url, future=True)
    _drop_all(engine)
    command.upgrade(_config(database_url), "head")
    yield engine
    _drop_all(engine)
    engine.dispose()


def _clear_data(engine):
    """每个测试前清空业务数据（保留 alembic_version），保证 seed 幂等。"""
    inspector = inspect(engine)
    with engine.begin() as connection:
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        for table in inspector.get_table_names():
            if table != "alembic_version":
                connection.execute(text(f"DELETE FROM `{table}`"))
        connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))


@pytest.fixture(autouse=True)
def clean_data(migrated_engine):
    """每个测试前清空业务数据，保证 seed 幂等。"""
    _clear_data(migrated_engine)
    yield


def _rewrite_payload(states=None, paper_type="experimental"):
    return {
        "paper_type": paper_type,
        "superconductor_kind": "conventional",
        "material_families": [
            {"id": 1, "name": "单质超导体", "status": "confirmed"}
        ],
        "material_states": states if states is not None else [
            {
                "material": "Sn",
                "structure_families": [],
                "element_count": 1,
                "material_dimensionality": "three_dimensional",
                "crystal_system": "tetragonal",
                "pressure_value_gpa": 0.001,
                "pressure_min_gpa": None,
                "pressure_max_gpa": None,
                "pressure_raw": None,
                "pressure_unit_raw": None,
                "reported_space_group_symbol": None,
                "reported_space_group_number": None,
                "state_kind": "experimental",
                "note": None,
                "calculation_context": None,
                "experimental_context": None,
                "tc_results": [
                    {
                        "result_kind": "experimental", "tc_method": "experimental",
                        "tc_value_k": 3.78, "value_raw": "3.78", "unit_raw": "K",
                        "is_representative": True,
                    }
                ],
                "properties": [
                    {"name": "threshold current", "value_raw": "0.28", "unit": "A"}
                ],
            }
        ],
        "structure_candidates": [],
    }


def test_pending_rewrite_keeps_revision_and_status(migrated_engine):
    """T022：pending 原地重建，版本号与状态不变。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="pending")

    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error
    data = data
    assert data["data"]["content_revision"] == 1
    assert data["data"]["review_status"] == "pending"
    assert data["data"]["revision_bumped"] is False
    assert data["data"]["material_state_count"] == 1

    with engine.connect() as connection:
        paper = connection.execute(
            text("SELECT content_revision, approved_revision, review_status FROM papers WHERE id = 10")
        ).one()
        assert tuple(paper) == (1, None, "pending")
        assert _count(engine, "tc_results") == 1
        assert _count(engine, "superconductor_properties") == 1


def test_rewrite_deletes_in_dependency_order_and_rebuilds(migrated_engine):
    """T023：删除顺序正确（含 structure_models 自引用），重建后与请求体一致。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="pending")

    payload = _rewrite_payload(states=[
        {
            "material": "Pb",
            "structure_families": [],
            "element_count": 1,
            "material_dimensionality": "three_dimensional",
            "crystal_system": "cubic",
            "pressure_value_gpa": 0.0,
            "state_kind": "experimental",
            "tc_results": [],
            "properties": [],
        }
    ])
    data, error = _call_endpoint(payload)
    assert error is None, error

    with engine.connect() as connection:
        # 自引用结构被先置空再删，无残留
        assert _count(engine, "structure_models") == 0
        assert _count(engine, "material_states") == 1
        state = connection.execute(
            text("SELECT superconductor_id, crystal_system FROM material_states WHERE paper_id = 10")
        ).one()
        # Pb 是既有共享目录外的新超导体：重建后应新建 superconductor 记录
        superconductor = connection.execute(
            text("SELECT id, chemical_formula FROM superconductors WHERE chemical_formula = 'Pb'")
        ).one()
        assert state[0] == superconductor[0]
        assert state[1] == "cubic"


def test_rewrite_reuses_validation_rules(migrated_engine):
    """T024：校验规则复用——缺化学式 / 缺论文级家族 / 压强区间 → 400。"""
    _seed_paper(migrated_engine, review_status="pending")

    missing_material = _rewrite_payload(states=[{
        "material": "",
        "structure_families": [], "element_count": 1, "material_dimensionality": "three_dimensional",
        "crystal_system": "tetragonal", "state_kind": "experimental",
        "tc_results": [], "properties": [],
    }])
    data, error = _call_endpoint(missing_material)
    assert error is not None and error.status_code == 400
    detail = error.detail
    assert detail["code"] == "state_material_required"
    assert "第 1 个材料状态" in detail["message"]

    missing_family = _rewrite_payload(states=[{
        "material": "Sn",
        "structure_families": [], "element_count": 1, "material_dimensionality": "three_dimensional",
        "crystal_system": "tetragonal", "state_kind": "experimental",
        "tc_results": [], "properties": [],
    }])
    missing_family["material_families"] = []
    data, error = _call_endpoint(missing_family)
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "material_family_required"

    bad_pressure = _rewrite_payload(states=[{
        "material": "Sn",
        "structure_families": [], "element_count": 1, "material_dimensionality": "three_dimensional",
        "crystal_system": "tetragonal", "state_kind": "experimental",
        "pressure_min_gpa": 10, "pressure_max_gpa": 5,
        "tc_results": [], "properties": [],
    }])
    data, error = _call_endpoint(bad_pressure)
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "invalid_pressure_range"


def test_rewrite_rejects_experimental_tc_calculation_context_without_partial_write(migrated_engine):
    """#84：管理员重写在删除旧科学数据之前必须拒绝实验 Tc 的计算参数。"""
    _seed_paper(migrated_engine, review_status="pending")
    payload = _rewrite_payload()
    payload["material_states"][0]["tc_results"][0]["calculation_context"] = {"lambda_ep": 1.2}

    data, error = _call_endpoint(payload)

    assert data is None
    assert error is not None and error.status_code == 400
    assert error.detail["code"] == "experimental_tc_calculation_context_forbidden"
    assert "第 1 个材料状态的第 1 条 Tc" in error.detail["message"]
    assert _count(migrated_engine, "tc_results") == 1


def test_review_paper_can_save_without_material_states(migrated_engine):
    """T025：综述论文空 material_states 保存成功。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="pending")
    with engine.begin() as connection:
        connection.execute(text("UPDATE papers SET paper_type = 'review' WHERE id = 10"))

    data, error = _call_endpoint(_rewrite_payload(states=[], paper_type="review"))
    assert error is None, error
    assert data["data"]["material_state_count"] == 0
    assert _count(engine, "material_states") == 0


def test_rewrite_does_not_touch_shared_catalogs(migrated_engine):
    """T026：跨论文共享目录表行数不变。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="pending")
    before = {
        table: _count(engine, table)
        for table in ("superconductors", "material_families", "structure_families", "property_definitions")
    }

    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error

    for table, count in before.items():
        assert _count(engine, table) == count, f"{table} 行数不应变化"


def test_approved_rewrite_bumps_revision_and_withdraws(migrated_engine):
    """T035：approved 升版——版本递增、已批准标记清空、退回待审核。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="approved")

    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error
    data = data
    assert data["data"]["content_revision"] == 2
    assert data["data"]["review_status"] == "pending"
    assert data["data"]["revision_bumped"] is True

    with engine.connect() as connection:
        paper = connection.execute(
            text("SELECT content_revision, approved_revision, review_status FROM papers WHERE id = 10")
        ).one()
        assert tuple(paper) == (2, None, "pending")


def test_bump_cascades_revision_to_lineage_tables(migrated_engine):
    """T036：升版后血缘表 paper_revision 全部为新版本、行数不变。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="approved")
    before = {
        table: _count(engine, table)
        for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states")
    }

    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error

    for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states"):
        assert _revisions(engine, table) == [2], f"{table} 未级联到新版本"
        assert _count(engine, table) == before[table], f"{table} 行数不应变化"


def test_approved_rewrite_reextracts_references_for_new_revision(migrated_engine, monkeypatch):
    """升版不继承旧引用，必须把新 GROBID 结果写入新版本。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="approved")
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO paper_reference_extractions"
                " (paper_id, paper_revision, status, parser_name)"
                " VALUES (10, 1, 'succeeded', 'grobid')"
            )
        )
        connection.execute(
            text(
                "INSERT INTO paper_references"
                " (paper_id, paper_revision, reference_index, raw_citation,"
                "  title, normalized_title, match_status)"
                " VALUES (10, 1, 0, 'old citation', 'Old paper', 'old paper', 'unmatched')"
            )
        )

    from backend.services import citation_graph

    parsed_paths = []

    def fake_extract(pdf_path):
        parsed_paths.append(pdf_path)
        return {
            "status": "succeeded",
            "parser_name": "grobid",
            "parser_version": "test",
            "error_message": None,
            "references": [
                {
                    "reference_index": 0,
                    "raw_citation": "new citation",
                    "title": "New paper",
                    "year": 2021,
                }
            ],
        }

    monkeypatch.setattr(citation_graph, "extract_references_from_pdf", fake_extract)
    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error
    assert data["data"]["content_revision"] == 2
    assert parsed_paths == [Path("/papers/10/paper.pdf")]

    with engine.connect() as connection:
        extraction = connection.execute(
            text(
                "SELECT paper_revision, status, parser_version"
                " FROM paper_reference_extractions WHERE paper_id = 10"
            )
        ).one()
        assert tuple(extraction) == (2, "succeeded", "test")
        references = connection.execute(
            text(
                "SELECT paper_revision, raw_citation"
                " FROM paper_references WHERE paper_id = 10 ORDER BY reference_index"
            )
        ).fetchall()
        assert [tuple(row) for row in references] == [(2, "new citation")]


def test_bump_writes_modified_history_event(migrated_engine):
    """T037：升版写入一条 modified 处理历史。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="approved")
    assert _count(engine, "paper_history_events") == 0

    data, error = _call_endpoint(_rewrite_payload())
    assert error is None, error

    assert _count(engine, "paper_history_events") == 1
    with engine.connect() as connection:
        event = connection.execute(
            text(
                "SELECT paper_revision, event_type, review_status, review_comment "
                "FROM paper_history_events WHERE paper_id = 10"
            )
        ).one()
        assert tuple(event) == (2, "modified", None, None)


def test_replaying_saved_scientific_draft_does_not_write_history(migrated_engine):
    """#87：语义相同的科学数据保存不重建，也不追加 modified 事件。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="pending")
    payload = _rewrite_payload()
    payload["history_operation_id"] = "scientific-first-save"

    first, error = _call_endpoint(payload)
    assert error is None, error
    assert first["data"]["unchanged"] is False
    assert _count(engine, "paper_history_events") == 1

    payload["history_operation_id"] = "scientific-same-save"
    second, error = _call_endpoint(payload)
    assert error is None, error
    assert second["data"]["unchanged"] is True
    assert second["data"]["content_revision"] == 1
    assert second["data"]["review_status"] == "pending"
    assert _count(engine, "paper_history_events") == 1


def test_failed_rewrite_rolls_back_everything(migrated_engine):
    """T038：重建失败整体回滚——版本、状态、科学数据与血缘数据全部保持原状。"""
    engine = migrated_engine
    _seed_paper(engine, review_status="approved")
    before_lineage = {
        table: _revisions(engine, table)
        for table in ("paper_files", "paper_chunks", "paper_evidences", "material_states")
    }

    # 非法材料维度会在 _resolve_draft_classifications 抛 400 → 事务回滚
    bad_payload = _rewrite_payload(states=[{
        "material": "Sn",
        "structure_families": [], "element_count": 1, "material_dimensionality": "not_a_dimension",
        "crystal_system": "tetragonal", "state_kind": "experimental",
        "tc_results": [], "properties": [],
    }])
    data, error = _call_endpoint(bad_payload)
    assert error is not None and error.status_code == 400

    with engine.connect() as connection:
        paper = connection.execute(
            text("SELECT content_revision, approved_revision, review_status FROM papers WHERE id = 10")
        ).one()
        assert tuple(paper) == (1, 1, "approved"), "论文版本与状态应保持原状"
    for table, revisions in before_lineage.items():
        assert _revisions(engine, table) == revisions, f"{table} 版本应回滚"
    assert _count(engine, "material_states") == 1
    assert _count(engine, "tc_results") == 1
    assert _count(engine, "paper_history_events") == 0


def test_rejected_paper_returns_409(migrated_engine):
    """T039：rejected 论文调用端点返回 409 paper_status_not_editable。"""
    _seed_paper(migrated_engine, review_status="rejected")

    data, error = _call_endpoint(_rewrite_payload())
    assert error is not None and error.status_code == 409
    assert error.detail["code"] == "paper_status_not_editable"
