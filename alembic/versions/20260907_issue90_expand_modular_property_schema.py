"""Issue #90 Expand：建立模块化物性、定义版本和迁移映射表。"""

from alembic import op
import sqlalchemy as sa
import hashlib
import json
from pathlib import Path

revision = "issue90_expand_modular_property_schema"
down_revision = "networked_news_discovery"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "property_modules",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("module_key", sa.String(96), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("module_code", sa.String(64), nullable=False),
        sa.Column("definition_key", sa.String(255), nullable=False, server_default="module.property"),
        sa.Column("definition_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["material_state_id"], ["material_states.id"], name="fk_property_modules_state", ondelete="RESTRICT"),
        sa.UniqueConstraint("module_key", name="uq_property_modules_key"),
        sa.UniqueConstraint("material_state_id", "module_code", name="uq_property_modules_state_code"),
        sa.CheckConstraint("module_code IN ('superconductive_properties','dynamical_properties','thermodynamical_properties','electronic_properties')", name="ck_property_modules_code"),
    )
    op.create_index("ix_property_modules_state", "property_modules", ["material_state_id"])
    op.create_table(
        "form_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("definition_key", sa.String(255), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False), sa.Column("module_code", sa.String(64), nullable=False),
        sa.Column("record_type", sa.String(64)), sa.Column("method_code", sa.String(64)), sa.Column("property_code", sa.String(100)),
        sa.Column("core_schema", sa.JSON(), nullable=False), sa.Column("json_schema", sa.JSON(), nullable=False), sa.Column("ui_schema", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"), sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer()), sa.Column("published_by", sa.Integer()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("published_at", sa.DateTime()),
        sa.UniqueConstraint("definition_key", "version", name="uq_form_definitions_key_version"),
        sa.CheckConstraint("target_kind IN ('property_module','property_record')", name="ck_form_definitions_target"),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_form_definitions_status"),
    )
    op.create_index("ix_form_definitions_lookup", "form_definitions", ["definition_key", "status"])
    op.create_table(
        "property_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("record_key", sa.String(96), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("material_state_id", sa.BigInteger(), nullable=False), sa.Column("module_id", sa.BigInteger(), nullable=False),
        sa.Column("record_type", sa.String(64), nullable=False), sa.Column("property_code", sa.String(100), nullable=False), sa.Column("custom_property_key", sa.String(96)), sa.Column("definition_id", sa.Integer(), nullable=False), sa.Column("definition_key", sa.String(255), nullable=False), sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("name_raw", sa.String(255), nullable=False), sa.Column("value_kind", sa.String(20), nullable=False), sa.Column("value_raw", sa.Text(), nullable=False), sa.Column("value_number", sa.Numeric(30, 12)), sa.Column("value_min", sa.Numeric(30, 12)), sa.Column("value_max", sa.Numeric(30, 12)), sa.Column("value_text", sa.Text()), sa.Column("value_boolean", sa.Boolean()), sa.Column("uncertainty", sa.Numeric(30, 12)), sa.Column("unit_raw", sa.String(100)), sa.Column("canonical_unit", sa.String(50)), sa.Column("method_code", sa.String(100)), sa.Column("method_raw", sa.String(255)), sa.Column("criterion_code", sa.String(64)), sa.Column("criterion_raw", sa.String(255)), sa.Column("is_representative", sa.Boolean(), nullable=False, server_default="0"), sa.Column("structure_key", sa.String(96)), sa.Column("payload_json", sa.JSON(), nullable=False), sa.Column("source_fingerprint", sa.String(64), nullable=False), sa.Column("record_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["module_id"], ["property_modules.id"], name="fk_property_records_module", ondelete="RESTRICT"), sa.ForeignKeyConstraint(["definition_id"], ["form_definitions.id"], name="fk_property_records_definition", ondelete="RESTRICT"),
        sa.UniqueConstraint("module_id", "record_key", name="uq_property_records_module_key"), sa.UniqueConstraint("paper_id", "paper_revision", "source_fingerprint", name="uq_property_records_source"),
        sa.CheckConstraint("record_type IN ('predicted_tc','measured_tc','property')", name="ck_property_records_type"), sa.CheckConstraint("value_kind IN ('number','range','text','boolean')", name="ck_property_records_value_kind"), sa.CheckConstraint("(value_min IS NULL AND value_max IS NULL) OR (value_min IS NOT NULL AND value_max IS NOT NULL AND value_min <= value_max)", name="ck_property_records_range"),
    )
    op.create_index("ix_property_records_state_type_method", "property_records", ["material_state_id", "record_type", "method_code"])
    op.create_table("property_record_evidences", sa.Column("record_id", sa.BigInteger(), primary_key=True), sa.Column("paper_evidence_id", sa.Integer(), primary_key=True), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("field_path", sa.String(255), nullable=False, server_default=""), sa.Column("evidence_role", sa.String(32), nullable=False, server_default="primary"), sa.ForeignKeyConstraint(["record_id"], ["property_records.id"], ondelete="CASCADE"), sa.ForeignKeyConstraint(["paper_evidence_id"], ["paper_evidences.id"], ondelete="CASCADE"), sa.UniqueConstraint("record_id", "paper_evidence_id", name="uq_property_record_evidences"))
    op.create_table("property_record_definition_events", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("record_id", sa.BigInteger(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("record_key", sa.String(96), nullable=False), sa.Column("operation", sa.String(20), nullable=False), sa.Column("actor_user_id", sa.Integer()), sa.Column("from_definition_key", sa.String(255), nullable=False), sa.Column("from_definition_version", sa.Integer(), nullable=False), sa.Column("to_definition_key", sa.String(255), nullable=False), sa.Column("to_definition_version", sa.Integer(), nullable=False), sa.Column("before_snapshot", sa.JSON(), nullable=False), sa.Column("after_snapshot", sa.JSON(), nullable=False), sa.Column("request_checksum", sa.String(64), nullable=False), sa.Column("previous_event_id", sa.BigInteger()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["record_id"], ["property_records.id"], ondelete="RESTRICT"))
    op.create_table("property_definition_promotion_events", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("operation_id", sa.String(64), nullable=False), sa.Column("actor_user_id", sa.Integer(), nullable=False), sa.Column("source_paper_id", sa.Integer(), nullable=False), sa.Column("source_paper_revision", sa.Integer(), nullable=False), sa.Column("source_record_key", sa.String(96), nullable=False), sa.Column("source_snapshot", sa.JSON(), nullable=False), sa.Column("target_definition_key", sa.String(255), nullable=False), sa.Column("target_definition_version", sa.Integer(), nullable=False), sa.Column("target_checksum", sa.String(64), nullable=False), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"), sa.UniqueConstraint("operation_id", name="uq_property_promotion_operation"), sa.UniqueConstraint("source_paper_id", "source_paper_revision", "source_record_key", name="uq_property_promotion_source"))
    op.create_table("issue90_property_migration_map", sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("source_table", sa.String(64), nullable=False), sa.Column("source_id", sa.BigInteger(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("target_table", sa.String(64), nullable=False), sa.Column("target_id", sa.BigInteger()), sa.Column("target_record_key", sa.String(96)), sa.Column("field_map", sa.JSON(), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="copied"), sa.Column("error_message", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.UniqueConstraint("source_table", "source_id", "paper_id", "paper_revision", "target_table", name="uq_issue90_migration_source"))
    # 影子材料表避免在停写前破坏旧表的全局唯一键；Read switch 时再重连
    # MaterialState，Observe 通过后由 Contract 阶段处理退役。
    op.create_table("issue90_legacy_chemical_systems", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("source_id", sa.Integer(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("system_key", sa.String(255), nullable=False), sa.Column("elements_list", sa.JSON(), nullable=False), sa.Column("element_count", sa.Integer(), nullable=False), sa.UniqueConstraint("paper_id", "paper_revision", "system_key", name="uq_issue90_shadow_system"))
    op.create_table("issue90_legacy_superconductors", sa.Column("id", sa.BigInteger(), primary_key=True), sa.Column("source_id", sa.Integer(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("chemical_system_id", sa.BigInteger(), nullable=False), sa.Column("chemical_formula", sa.String(255), nullable=False), sa.Column("formula_normalized", sa.String(255), nullable=False), sa.Column("composition_key", sa.String(255), nullable=False), sa.Column("isotope_signature", sa.String(255)), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("elements_list", sa.JSON(), nullable=False), sa.Column("composition", sa.JSON(), nullable=False), sa.Column("element_ratio", sa.JSON(), nullable=False), sa.UniqueConstraint("paper_id", "paper_revision", "composition_key", name="uq_issue90_shadow_superconductor"))
    seed = Path(__file__).parents[2] / "backend" / "data" / "form_definitions.v1.json"
    rows = json.loads(seed.read_text(encoding="utf-8"))
    for row in rows:
        content = {key: row.get(key) for key in ("definition_key", "version", "target_kind", "module_code", "record_type", "method_code", "property_code", "core_schema", "json_schema", "ui_schema")}
        row["checksum"] = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    op.bulk_insert(sa.table("form_definitions", *[sa.column(name) for name in ("definition_key", "version", "target_kind", "module_code", "record_type", "method_code", "property_code", "core_schema", "json_schema", "ui_schema", "status", "checksum")]), rows)


def downgrade() -> None:
    for table in ("issue90_legacy_superconductors", "issue90_legacy_chemical_systems", "issue90_property_migration_map", "property_definition_promotion_events", "property_record_definition_events", "property_record_evidences", "property_records", "form_definitions", "property_modules"):
        op.drop_table(table)
