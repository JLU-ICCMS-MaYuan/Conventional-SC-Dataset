"""Issue #90 Expand: create the target schema without changing legacy reads."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from alembic import op
import sqlalchemy as sa

revision = "issue90_expand_v1"
down_revision = "networked_news_discovery"
branch_labels = None
depends_on = None


def _replace_fk(
    name: str,
    table: str,
    referred_table: str,
    local_columns: list[str],
    remote_columns: list[str],
    *,
    ondelete: str = "RESTRICT",
    onupdate: str | None = None,
) -> None:
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(
        name,
        table,
        referred_table,
        local_columns,
        remote_columns,
        ondelete=ondelete,
        onupdate=onupdate,
    )


def _prepare_legacy_revision_chain() -> None:
    for table, constraint in (
        ("structure_models", "fk_structure_models_state_revision"),
        ("calculation_contexts", "fk_calculation_contexts_state_revision"),
        ("experimental_contexts", "fk_experimental_contexts_state_revision"),
        ("tc_results", "fk_tc_results_state_revision"),
        ("superconductor_properties", "fk_superconductor_properties_state_revision"),
    ):
        _replace_fk(
            constraint,
            table,
            "material_states",
            ["material_state_id", "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
            onupdate="CASCADE",
        )

    for name, table, referred_table, local_column in (
        ("fk_structure_models_parent_revision", "structure_models", "structure_models", "parent_structure_id"),
        ("fk_calculation_contexts_structure_revision", "calculation_contexts", "structure_models", "structure_id"),
        ("fk_experimental_contexts_structure_revision", "experimental_contexts", "structure_models", "structure_id"),
        ("fk_tc_results_calculation_revision", "tc_results", "calculation_contexts", "calculation_context_id"),
        ("fk_tc_results_experimental_revision", "tc_results", "experimental_contexts", "experimental_context_id"),
        ("fk_superconductor_properties_structure_revision", "superconductor_properties", "structure_models", "structure_id"),
        ("fk_superconductor_properties_calculation_revision", "superconductor_properties", "calculation_contexts", "calculation_context_id"),
    ):
        _replace_fk(name, table, referred_table, [local_column], ["id"])

    for table, entity_column, entity_table in (
        ("tc_result_evidences", "tc_result_id", "tc_results"),
        ("structure_model_evidences", "structure_id", "structure_models"),
        ("superconductor_property_evidences", "superconductor_property_id", "superconductor_properties"),
    ):
        _replace_fk(
            f"fk_{table}_{'result' if table == 'tc_result_evidences' else 'structure' if table == 'structure_model_evidences' else 'property'}",
            table,
            entity_table,
            [entity_column, "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
            ondelete="CASCADE",
            onupdate="CASCADE",
        )
        _replace_fk(
            f"fk_{table}_evidence",
            table,
            "paper_evidences",
            ["paper_evidence_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _restore_legacy_revision_chain() -> None:
    for table, entity_column, entity_table in (
        ("tc_result_evidences", "tc_result_id", "tc_results"),
        ("structure_model_evidences", "structure_id", "structure_models"),
        ("superconductor_property_evidences", "superconductor_property_id", "superconductor_properties"),
    ):
        entity_suffix = (
            "result"
            if table == "tc_result_evidences"
            else "structure"
            if table == "structure_model_evidences"
            else "property"
        )
        _replace_fk(
            f"fk_{table}_{entity_suffix}",
            table,
            entity_table,
            [entity_column, "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
            ondelete="CASCADE",
        )
        _replace_fk(
            f"fk_{table}_evidence",
            table,
            "paper_evidences",
            ["paper_evidence_id", "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
            ondelete="CASCADE",
        )

    composite_links = (
        (
            "fk_structure_models_parent_revision",
            "structure_models",
            "structure_models",
            ["parent_structure_id", "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
        ),
        (
            "fk_calculation_contexts_structure_revision",
            "calculation_contexts",
            "structure_models",
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
        (
            "fk_experimental_contexts_structure_revision",
            "experimental_contexts",
            "structure_models",
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
        (
            "fk_tc_results_calculation_revision",
            "tc_results",
            "calculation_contexts",
            ["calculation_context_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
        (
            "fk_tc_results_experimental_revision",
            "tc_results",
            "experimental_contexts",
            ["experimental_context_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
        (
            "fk_superconductor_properties_structure_revision",
            "superconductor_properties",
            "structure_models",
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
        (
            "fk_superconductor_properties_calculation_revision",
            "superconductor_properties",
            "calculation_contexts",
            ["calculation_context_id", "material_state_id", "paper_id", "paper_revision"],
            ["id", "material_state_id", "paper_id", "paper_revision"],
        ),
    )
    for name, table, referred_table, local_columns, remote_columns in composite_links:
        _replace_fk(name, table, referred_table, local_columns, remote_columns)

    for table, constraint in (
        ("structure_models", "fk_structure_models_state_revision"),
        ("calculation_contexts", "fk_calculation_contexts_state_revision"),
        ("experimental_contexts", "fk_experimental_contexts_state_revision"),
        ("tc_results", "fk_tc_results_state_revision"),
        ("superconductor_properties", "fk_superconductor_properties_state_revision"),
    ):
        _replace_fk(
            constraint,
            table,
            "material_states",
            ["material_state_id", "paper_id", "paper_revision"],
            ["id", "paper_id", "paper_revision"],
        )


def _seed_definitions() -> None:
    path = Path(__file__).parents[2] / "backend" / "data" / "form_definitions.v1.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    keys = ("definition_key", "version", "target_kind", "module_code", "record_type", "method_code", "property_code", "core_schema", "json_schema", "ui_schema")
    for row in rows:
        content = {key: row.get(key) for key in keys}
        row["checksum"] = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    column_types = {
        "version": sa.Integer(), "core_schema": sa.JSON(), "json_schema": sa.JSON(),
        "ui_schema": sa.JSON(),
    }
    columns = keys + ("status", "checksum")
    op.bulk_insert(sa.table("form_definitions", *[sa.column(name, column_types.get(name, sa.String())) for name in columns]), rows)


def upgrade() -> None:
    _prepare_legacy_revision_chain()
    op.add_column("material_states", sa.Column("state_key", sa.String(96), nullable=True))
    op.execute("UPDATE material_states SET state_key = CONCAT('legacy-state-', id) WHERE state_key IS NULL")
    op.alter_column("material_states", "state_key", existing_type=sa.String(96), nullable=False)
    op.create_unique_constraint("uq_material_states_paper_state_key", "material_states", ["paper_id", "paper_revision", "state_key"])

    op.create_table(
        "issue90_chemical_systems",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("system_key", sa.String(255), nullable=False), sa.Column("elements_list", sa.JSON(), nullable=False),
        sa.Column("element_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["paper_id", "paper_revision"], ["papers.id", "papers.content_revision"], name="fk_i90_system_paper_rev", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.UniqueConstraint("id", "paper_id", "paper_revision", name="uq_i90_system_identity_rev"),
        sa.UniqueConstraint("paper_id", "paper_revision", "system_key", name="uq_i90_system_scope"),
    )
    op.create_index("ix_i90_system_key", "issue90_chemical_systems", ["system_key"])
    op.create_table(
        "issue90_superconductors",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("chemical_system_id", sa.Integer(), nullable=False), sa.Column("chemical_formula", sa.String(255), nullable=False),
        sa.Column("formula_normalized", sa.String(255), nullable=False), sa.Column("composition_key", sa.String(255), nullable=False),
        sa.Column("isotope_signature", sa.String(255)), sa.Column("display_name", sa.String(255), nullable=False),
        sa.Column("elements_list", sa.JSON(), nullable=False), sa.Column("composition", sa.JSON(), nullable=False),
        sa.Column("element_ratio", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["chemical_system_id", "paper_id", "paper_revision"], ["issue90_chemical_systems.id", "issue90_chemical_systems.paper_id", "issue90_chemical_systems.paper_revision"], name="fk_i90_sc_system_rev", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.UniqueConstraint("id", "paper_id", "paper_revision", name="uq_i90_sc_identity_rev"),
        sa.UniqueConstraint("paper_id", "paper_revision", "composition_key", name="uq_i90_sc_scope"),
    )
    op.create_index("ix_i90_sc_formula", "issue90_superconductors", ["formula_normalized"])

    op.create_table(
        "form_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("definition_key", sa.String(255), nullable=False), sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("target_kind", sa.String(32), nullable=False), sa.Column("module_code", sa.String(64), nullable=False),
        sa.Column("record_type", sa.String(64)), sa.Column("method_code", sa.String(64)), sa.Column("property_code", sa.String(100)),
        sa.Column("core_schema", sa.JSON(), nullable=False), sa.Column("json_schema", sa.JSON(), nullable=False), sa.Column("ui_schema", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"), sa.Column("checksum", sa.String(64), nullable=False),
        sa.Column("created_by", sa.Integer()), sa.Column("published_by", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("published_at", sa.DateTime()),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name="fk_i90_definition_creator", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["published_by"], ["users.id"], name="fk_i90_definition_publisher", ondelete="RESTRICT"),
        sa.UniqueConstraint("definition_key", "version", name="uq_form_definitions_key_version"),
        sa.CheckConstraint("version >= 1", name="ck_form_definitions_version"),
        sa.CheckConstraint("target_kind IN ('property_module','property_record')", name="ck_form_definitions_target"),
        sa.CheckConstraint("status IN ('draft','published','retired')", name="ck_form_definitions_status"),
    )
    op.create_index("ix_form_definitions_lookup", "form_definitions", ["definition_key", "status"])
    op.create_index("ix_form_definitions_module", "form_definitions", ["module_code", "target_kind", "status"])

    op.create_table(
        "property_modules",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("module_key", sa.String(96), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False), sa.Column("module_code", sa.String(64), nullable=False),
        sa.Column("definition_key", sa.String(255), nullable=False), sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"), sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["material_state_id", "paper_id", "paper_revision"], ["material_states.id", "material_states.paper_id", "material_states.paper_revision"], name="fk_property_modules_state_revision", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.UniqueConstraint("id", "material_state_id", "paper_id", "paper_revision", name="uq_property_modules_identity_rev"),
        sa.UniqueConstraint("material_state_id", "module_key", name="uq_property_modules_state_key"), sa.UniqueConstraint("material_state_id", "module_code", name="uq_property_modules_state_code"),
        sa.CheckConstraint("module_code IN ('superconductive_properties','dynamical_properties','thermodynamical_properties','electronic_properties')", name="ck_property_modules_code"),
        sa.CheckConstraint("display_order >= 0", name="ck_property_modules_order"),
    )
    op.create_index("ix_property_modules_state", "property_modules", ["material_state_id"])

    op.create_table(
        "property_records",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("record_key", sa.String(96), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False), sa.Column("module_id", sa.BigInteger(), nullable=False),
        sa.Column("record_type", sa.String(64), nullable=False), sa.Column("property_code", sa.String(100), nullable=False),
        sa.Column("custom_property_key", sa.String(96)), sa.Column("definition_id", sa.Integer(), nullable=False),
        sa.Column("definition_key", sa.String(255), nullable=False), sa.Column("definition_version", sa.Integer(), nullable=False),
        sa.Column("name_raw", sa.String(255), nullable=False), sa.Column("value_kind", sa.String(20), nullable=False),
        sa.Column("value_raw", sa.Text(), nullable=False), sa.Column("value_number", sa.Numeric(30, 12)),
        sa.Column("value_min", sa.Numeric(30, 12)), sa.Column("value_max", sa.Numeric(30, 12)), sa.Column("value_text", sa.Text()),
        sa.Column("value_boolean", sa.Boolean()), sa.Column("uncertainty", sa.Numeric(30, 12)),
        sa.Column("unit_raw", sa.String(100)), sa.Column("canonical_unit", sa.String(50)),
        sa.Column("method_code", sa.String(100)), sa.Column("method_raw", sa.String(255)),
        sa.Column("criterion_code", sa.String(64)), sa.Column("criterion_raw", sa.String(255)),
        sa.Column("is_representative", sa.Boolean(), nullable=False, server_default="0"), sa.Column("structure_key", sa.String(96)),
        sa.Column("payload_json", sa.JSON(), nullable=False), sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("record_checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["module_id", "material_state_id", "paper_id", "paper_revision"], ["property_modules.id", "property_modules.material_state_id", "property_modules.paper_id", "property_modules.paper_revision"], name="fk_property_records_module_revision", ondelete="RESTRICT", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["definition_id"], ["form_definitions.id"], name="fk_property_records_definition", ondelete="RESTRICT"),
        sa.UniqueConstraint("id", "paper_id", "paper_revision", name="uq_property_records_identity_rev"),
        sa.UniqueConstraint("module_id", "record_key", name="uq_property_records_module_key"),
        sa.UniqueConstraint("paper_id", "paper_revision", "source_fingerprint", name="uq_property_records_source"),
        sa.CheckConstraint("record_type IN ('predicted_tc','measured_tc','property')", name="ck_property_records_type"),
        sa.CheckConstraint("value_kind IN ('number','range','text','boolean')", name="ck_property_records_value_kind"),
        sa.CheckConstraint("(value_min IS NULL AND value_max IS NULL) OR (value_min IS NOT NULL AND value_max IS NOT NULL AND value_min <= value_max)", name="ck_property_records_range"),
        sa.CheckConstraint("uncertainty IS NULL OR uncertainty >= 0", name="ck_property_records_uncertainty"),
        sa.CheckConstraint("(value_kind <> 'number' OR value_number IS NOT NULL) AND (value_kind <> 'range' OR (value_min IS NOT NULL AND value_max IS NOT NULL)) AND (value_kind <> 'text' OR value_text IS NOT NULL) AND (value_kind <> 'boolean' OR value_boolean IS NOT NULL)", name="ck_property_records_value_shape"),
        sa.CheckConstraint("(record_type NOT IN ('predicted_tc','measured_tc')) OR (property_code = 'tc' AND method_code IS NOT NULL)", name="ck_property_records_tc_identity"),
        sa.CheckConstraint("(property_code = 'custom' AND record_type = 'property' AND custom_property_key IS NOT NULL) OR (property_code <> 'custom' AND custom_property_key IS NULL)", name="ck_property_records_custom_identity"),
        sa.CheckConstraint("(record_type <> 'predicted_tc' OR (JSON_EXTRACT(payload_json, '$.calculation_conditions') IS NOT NULL AND JSON_EXTRACT(payload_json, '$.experimental_conditions') IS NULL)) AND (record_type <> 'measured_tc' OR (JSON_EXTRACT(payload_json, '$.experimental_conditions') IS NOT NULL AND JSON_EXTRACT(payload_json, '$.calculation_conditions') IS NULL))", name="ck_property_records_condition_type"),
    )
    op.create_index("ix_property_records_state_type_method", "property_records", ["material_state_id", "record_type", "method_code"])
    op.create_index("ix_property_records_tc_value", "property_records", ["property_code", "value_number"])

    op.create_table(
        "property_record_evidences",
        sa.Column("record_id", sa.BigInteger(), primary_key=True), sa.Column("paper_evidence_id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("field_path", sa.String(255), nullable=False, server_default=""), sa.Column("evidence_role", sa.String(32), nullable=False, server_default="primary"),
        sa.ForeignKeyConstraint(["record_id", "paper_id", "paper_revision"], ["property_records.id", "property_records.paper_id", "property_records.paper_revision"], name="fk_property_record_evidences_record", ondelete="CASCADE", onupdate="CASCADE"),
        sa.ForeignKeyConstraint(["paper_evidence_id"], ["paper_evidences.id"], name="fk_property_record_evidences_evidence", ondelete="CASCADE"),
        sa.UniqueConstraint("record_id", "paper_evidence_id", name="uq_property_record_evidences"),
    )
    op.create_table(
        "property_record_definition_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("record_id", sa.BigInteger(), nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False), sa.Column("record_key", sa.String(96), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False), sa.Column("actor_user_id", sa.Integer()),
        sa.Column("from_definition_key", sa.String(255), nullable=False), sa.Column("from_definition_version", sa.Integer(), nullable=False),
        sa.Column("to_definition_key", sa.String(255), nullable=False), sa.Column("to_definition_version", sa.Integer(), nullable=False),
        sa.Column("before_snapshot", sa.JSON(), nullable=False), sa.Column("after_snapshot", sa.JSON(), nullable=False),
        sa.Column("request_checksum", sa.String(64), nullable=False), sa.Column("previous_event_id", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["record_id"], ["property_records.id"], name="fk_i90_event_record", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_i90_event_actor", ondelete="RESTRICT"),
    )
    op.create_index("ix_property_record_definition_events_record", "property_record_definition_events", ["record_id", "created_at"])
    op.create_table(
        "property_definition_promotion_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("operation_id", sa.String(64), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False), sa.Column("source_paper_id", sa.Integer(), nullable=False),
        sa.Column("source_paper_revision", sa.Integer(), nullable=False), sa.Column("source_record_key", sa.String(96), nullable=False),
        sa.Column("source_snapshot", sa.JSON(), nullable=False), sa.Column("target_definition_key", sa.String(255), nullable=False),
        sa.Column("target_definition_version", sa.Integer(), nullable=False), sa.Column("target_checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], name="fk_i90_promotion_actor", ondelete="RESTRICT"),
        sa.UniqueConstraint("operation_id", name="uq_property_promotion_operation"),
        sa.UniqueConstraint("source_paper_id", "source_paper_revision", "source_record_key", name="uq_property_promotion_source"),
    )
    op.create_index("ix_property_promotion_target", "property_definition_promotion_events", ["target_definition_key"])

    op.create_table(
        "issue90_property_migration_map",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("source_table", sa.String(64), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("target_table", sa.String(64), nullable=False), sa.Column("target_id", sa.BigInteger()), sa.Column("target_record_key", sa.String(96)),
        sa.Column("source_checksum", sa.String(64), nullable=False), sa.Column("target_checksum", sa.String(64)),
        sa.Column("field_map", sa.JSON(), nullable=False), sa.Column("status", sa.String(20), nullable=False, server_default="copied"),
        sa.Column("error_message", sa.Text()), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_table", "source_id", "paper_id", "paper_revision", "target_table", name="uq_issue90_migration_source"),
        sa.CheckConstraint("status IN ('copied','reconciled','archived','error')", name="ck_issue90_migration_status"),
    )
    op.create_table(
        "issue90_migration_anomalies",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True), sa.Column("source_table", sa.String(64), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False), sa.Column("paper_id", sa.Integer(), nullable=False), sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(64), nullable=False), sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"), sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_table", "source_id", "paper_id", "paper_revision", "code", name="uq_issue90_anomaly"),
    )
    op.create_table(
        "issue90_migration_checkpoint",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("phase", sa.String(20), nullable=False),
        sa.Column("writes_blocked", sa.Boolean(), nullable=False, server_default="0"), sa.Column("reads_target", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("writes_target", sa.Boolean(), nullable=False, server_default="0"), sa.Column("reconciled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("observed", sa.Boolean(), nullable=False, server_default="0"), sa.Column("checkpoint_json", sa.JSON(), nullable=False),
        sa.Column("error_json", sa.JSON(), nullable=False), sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("phase IN ('expand','copy','reconcile','read_switch','write_switch','observe','contract')", name="ck_issue90_checkpoint_phase"),
    )
    op.bulk_insert(sa.table(
        "issue90_migration_checkpoint",
        sa.column("id", sa.Integer()), sa.column("phase", sa.String()),
        sa.column("writes_blocked", sa.Boolean()), sa.column("reads_target", sa.Boolean()),
        sa.column("writes_target", sa.Boolean()), sa.column("reconciled", sa.Boolean()),
        sa.column("observed", sa.Boolean()), sa.column("checkpoint_json", sa.JSON()),
        sa.column("error_json", sa.JSON()),
    ), [{"id": 1, "phase": "expand", "writes_blocked": False, "reads_target": False, "writes_target": False, "reconciled": False, "observed": False, "checkpoint_json": {}, "error_json": []}])
    _seed_definitions()


def downgrade() -> None:
    for table in ("issue90_migration_checkpoint", "issue90_migration_anomalies", "issue90_property_migration_map", "property_definition_promotion_events", "property_record_definition_events", "property_record_evidences", "property_records", "property_modules", "form_definitions", "issue90_superconductors", "issue90_chemical_systems"):
        op.drop_table(table)
    op.drop_constraint("uq_material_states_paper_state_key", "material_states", type_="unique")
    op.drop_column("material_states", "state_key")
    _restore_legacy_revision_chain()
