"""add condition-aware superconducting data model

Revision ID: 20260821_0008
Revises: 20260821_0007
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0008"
down_revision = "20260821_0007"
branch_labels = None
depends_on = None


_BUSINESS_TABLES = (
    "papers",
    "superconductors",
    "superconductor_records",
    "superconductors_structures",
)


def _require_empty_business_tables() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    populated = []
    for table_name in _BUSINESS_TABLES:
        if not inspector.has_table(table_name):
            continue
        if bind.execute(sa.text(f"SELECT 1 FROM `{table_name}` LIMIT 1")).first():
            populated.append(table_name)
    if populated:
        names = ", ".join(populated)
        raise RuntimeError(
            "20260821_0008 仅支持全新空业务库；检测到已有数据表: "
            f"{names}。本迁移不会回填、转换或删除现有数据。"
        )


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def upgrade() -> None:
    _require_empty_business_tables()

    op.add_column(
        "superconductors",
        sa.Column("composition_key", sa.String(length=255), nullable=False),
    )
    op.add_column(
        "superconductors",
        sa.Column("isotope_signature", sa.String(length=255), nullable=True),
    )
    op.create_unique_constraint(
        "uq_superconductors_composition_key",
        "superconductors",
        ["composition_key"],
    )
    op.create_index(
        "ix_superconductors_isotope_signature",
        "superconductors",
        ["isotope_signature"],
    )

    op.drop_table("superconductors_structures")
    op.drop_table("superconductor_records")

    op.create_table(
        "material_states",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column(
            "superconductor_id",
            sa.Integer(),
            sa.ForeignKey("superconductors.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("phase_label", sa.String(length=255), nullable=True),
        sa.Column("pressure_value_gpa", sa.Numeric(14, 6), nullable=True),
        sa.Column("pressure_min_gpa", sa.Numeric(14, 6), nullable=True),
        sa.Column("pressure_max_gpa", sa.Numeric(14, 6), nullable=True),
        sa.Column("pressure_raw", sa.String(length=255), nullable=True),
        sa.Column("pressure_unit_raw", sa.String(length=50), nullable=True),
        sa.Column("temperature_value_k", sa.Numeric(14, 6), nullable=True),
        sa.Column("temperature_raw", sa.String(length=255), nullable=True),
        sa.Column("temperature_unit_raw", sa.String(length=50), nullable=True),
        sa.Column("magnetic_field_t", sa.Numeric(14, 6), nullable=True),
        sa.Column(
            "state_kind",
            sa.String(length=20),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_material_states_paper_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "state_kind IN ('theoretical', 'experimental', 'mixed', 'unknown')",
            name="ck_material_states_kind",
        ),
        sa.CheckConstraint(
            """
            (pressure_min_gpa IS NULL AND pressure_max_gpa IS NULL)
            OR
            (
                pressure_min_gpa IS NOT NULL
                AND pressure_max_gpa IS NOT NULL
                AND pressure_min_gpa <= pressure_max_gpa
            )
            """,
            name="ck_material_states_pressure_range",
        ),
        sa.CheckConstraint(
            """
            (pressure_value_gpa IS NULL OR pressure_value_gpa >= 0)
            AND (pressure_min_gpa IS NULL OR pressure_min_gpa >= 0)
            AND (temperature_value_k IS NULL OR temperature_value_k >= 0)
            AND (magnetic_field_t IS NULL OR magnetic_field_t >= 0)
            """,
            name="ck_material_states_nonnegative",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_material_states_identity_revision",
        ),
    )
    op.create_index(
        "ix_material_states_paper_revision",
        "material_states",
        ["paper_id", "paper_revision"],
    )
    op.create_index(
        "ix_material_states_material_pressure",
        "material_states",
        ["superconductor_id", "pressure_value_gpa"],
    )
    op.create_index(
        "ix_material_states_paper_material_phase",
        "material_states",
        ["paper_id", "superconductor_id", "phase_label"],
    )

    op.create_table(
        "structure_models",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("parent_structure_id", sa.BigInteger(), nullable=True),
        sa.Column("space_group_symbol", sa.String(length=100), nullable=True),
        sa.Column("space_group_number", sa.SmallInteger(), nullable=True),
        sa.Column("structure_format", sa.String(length=20), nullable=False),
        sa.Column("structure_text", sa.Text().with_variant(sa.Text(length=2**32 - 1), "mysql"), nullable=False),
        sa.Column("structure_hash", sa.String(length=64), nullable=False),
        sa.Column("cell_parameters", sa.JSON(), nullable=True),
        sa.Column("volume_angstrom3", sa.Numeric(20, 8), nullable=True),
        sa.Column("atom_count", sa.Integer(), nullable=True),
        sa.Column("geometry_method", sa.String(length=100), nullable=True),
        sa.Column("nuclear_treatment", sa.String(length=32), nullable=False),
        sa.Column("exchange_correlation", sa.String(length=100), nullable=True),
        sa.Column("calculation_code", sa.String(length=100), nullable=True),
        sa.Column("method_parameters", sa.JSON(), nullable=True),
        sa.Column("source_locator", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            [
                "material_states.id",
                "material_states.paper_id",
                "material_states.paper_revision",
            ],
            name="fk_structure_models_state_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "space_group_number IS NULL OR space_group_number BETWEEN 1 AND 230",
            name="ck_structure_models_space_group",
        ),
        sa.CheckConstraint(
            "atom_count IS NULL OR atom_count >= 0",
            name="ck_structure_models_atom_count",
        ),
        sa.CheckConstraint(
            "volume_angstrom3 IS NULL OR volume_angstrom3 >= 0",
            name="ck_structure_models_volume",
        ),
        sa.CheckConstraint(
            """
            nuclear_treatment IN (
                'classical_static', 'harmonic', 'quasi_harmonic',
                'anharmonic_classical', 'anharmonic_quantum',
                'experimental', 'unknown'
            )
            """,
            name="ck_structure_models_nuclear_treatment",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_structure_models_identity_revision",
        ),
        sa.UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_structure_models_state_revision",
        ),
    )
    op.create_foreign_key(
        "fk_structure_models_parent_revision",
        "structure_models",
        "structure_models",
        ["parent_structure_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_structure_models_state",
        "structure_models",
        ["material_state_id"],
    )
    op.create_index(
        "ix_structure_models_hash",
        "structure_models",
        ["structure_hash"],
    )
    op.create_index(
        "ix_structure_models_paper_revision",
        "structure_models",
        ["paper_id", "paper_revision"],
    )

    context_columns = (
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("structure_id", sa.BigInteger(), nullable=True),
    )

    op.create_table(
        "calculation_contexts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        *context_columns,
        sa.Column("missing_structure_reason", sa.Text(), nullable=True),
        sa.Column("electronic_method", sa.String(length=100), nullable=True),
        sa.Column("exchange_correlation", sa.String(length=100), nullable=True),
        sa.Column("pseudopotential_type", sa.String(length=100), nullable=True),
        sa.Column("pseudopotential_name", sa.String(length=255), nullable=True),
        sa.Column("spin_orbit_coupling", sa.Boolean(), nullable=True),
        sa.Column("phonon_method", sa.String(length=100), nullable=True),
        sa.Column("phonon_nuclear_treatment", sa.String(length=32), nullable=False),
        sa.Column("epc_method", sa.String(length=100), nullable=True),
        sa.Column("mu_star", sa.Numeric(12, 8), nullable=True),
        sa.Column("lambda_ep", sa.Numeric(20, 8), nullable=True),
        sa.Column("omega_log_k", sa.Numeric(20, 8), nullable=True),
        sa.Column("k_grid", sa.String(length=100), nullable=True),
        sa.Column("q_grid", sa.String(length=100), nullable=True),
        sa.Column("energy_cutoff_value", sa.Numeric(20, 8), nullable=True),
        sa.Column("energy_cutoff_unit", sa.String(length=50), nullable=True),
        sa.Column("calculation_code", sa.String(length=100), nullable=True),
        sa.Column("parameters_json", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            [
                "material_states.id",
                "material_states.paper_id",
                "material_states.paper_revision",
            ],
            name="fk_calculation_contexts_state_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_calculation_contexts_structure_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            """
            (structure_id IS NOT NULL AND missing_structure_reason IS NULL)
            OR
            (
                structure_id IS NULL
                AND missing_structure_reason IS NOT NULL
                AND CHAR_LENGTH(TRIM(missing_structure_reason)) > 0
            )
            """,
            name="ck_calculation_contexts_structure",
        ),
        sa.CheckConstraint(
            """
            phonon_nuclear_treatment IN (
                'classical_static', 'harmonic', 'quasi_harmonic',
                'anharmonic_classical', 'anharmonic_quantum',
                'experimental', 'unknown'
            )
            """,
            name="ck_calculation_contexts_nuclear_treatment",
        ),
        sa.CheckConstraint(
            """
            (mu_star IS NULL OR mu_star >= 0)
            AND (lambda_ep IS NULL OR lambda_ep >= 0)
            AND (omega_log_k IS NULL OR omega_log_k >= 0)
            AND (energy_cutoff_value IS NULL OR energy_cutoff_value >= 0)
            """,
            name="ck_calculation_contexts_nonnegative",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_calculation_contexts_identity_revision",
        ),
        sa.UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_calculation_contexts_state_revision",
        ),
    )
    op.create_index(
        "ix_calculation_contexts_paper_revision",
        "calculation_contexts",
        ["paper_id", "paper_revision"],
    )
    op.create_index(
        "ix_calculation_contexts_state",
        "calculation_contexts",
        ["material_state_id"],
    )

    op.create_table(
        "experimental_contexts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("structure_id", sa.BigInteger(), nullable=True),
        sa.Column("sample_label", sa.String(length=255), nullable=True),
        sa.Column("sample_preparation", sa.Text(), nullable=True),
        sa.Column("measurement_method", sa.String(length=100), nullable=True),
        sa.Column("tc_criterion", sa.String(length=64), nullable=False),
        sa.Column("applied_field_t", sa.Numeric(14, 6), nullable=True),
        sa.Column("pressure_uncertainty_gpa", sa.Numeric(14, 6), nullable=True),
        sa.Column("parameters_json", sa.JSON(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            [
                "material_states.id",
                "material_states.paper_id",
                "material_states.paper_revision",
            ],
            name="fk_experimental_contexts_state_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_experimental_contexts_structure_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            """
            tc_criterion IN (
                'resistance_onset', 'resistance_midpoint', 'zero_resistance',
                'magnetic_susceptibility', 'specific_heat',
                'author_reported', 'unknown'
            )
            """,
            name="ck_experimental_contexts_criterion",
        ),
        sa.CheckConstraint(
            """
            (applied_field_t IS NULL OR applied_field_t >= 0)
            AND (
                pressure_uncertainty_gpa IS NULL
                OR pressure_uncertainty_gpa >= 0
            )
            """,
            name="ck_experimental_contexts_nonnegative",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_experimental_contexts_identity_revision",
        ),
        sa.UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_experimental_contexts_state_revision",
        ),
    )
    op.create_index(
        "ix_experimental_contexts_paper_revision",
        "experimental_contexts",
        ["paper_id", "paper_revision"],
    )
    op.create_index(
        "ix_experimental_contexts_state",
        "experimental_contexts",
        ["material_state_id"],
    )

    op.create_table(
        "tc_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("calculation_context_id", sa.BigInteger(), nullable=True),
        sa.Column("experimental_context_id", sa.BigInteger(), nullable=True),
        sa.Column("result_kind", sa.String(length=16), nullable=False),
        sa.Column("tc_method", sa.String(length=64), nullable=False),
        sa.Column("tc_value_k", sa.Numeric(20, 8), nullable=True),
        sa.Column("tc_min_k", sa.Numeric(20, 8), nullable=True),
        sa.Column("tc_max_k", sa.Numeric(20, 8), nullable=True),
        sa.Column("uncertainty_k", sa.Numeric(20, 8), nullable=True),
        sa.Column("value_raw", sa.String(length=255), nullable=False),
        sa.Column("unit_raw", sa.String(length=50), nullable=False),
        sa.Column("source_locator", sa.String(length=500), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "is_representative",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "representative_marker",
            sa.Integer(),
            sa.Computed(
                "CASE WHEN is_representative THEN 1 ELSE NULL END",
                persisted=True,
            ),
            nullable=True,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            [
                "material_states.id",
                "material_states.paper_id",
                "material_states.paper_revision",
            ],
            name="fk_tc_results_state_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "calculation_context_id",
                "material_state_id",
                "paper_id",
                "paper_revision",
            ],
            [
                "calculation_contexts.id",
                "calculation_contexts.material_state_id",
                "calculation_contexts.paper_id",
                "calculation_contexts.paper_revision",
            ],
            name="fk_tc_results_calculation_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "experimental_context_id",
                "material_state_id",
                "paper_id",
                "paper_revision",
            ],
            [
                "experimental_contexts.id",
                "experimental_contexts.material_state_id",
                "experimental_contexts.paper_id",
                "experimental_contexts.paper_revision",
            ],
            name="fk_tc_results_experimental_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "result_kind IN ('theoretical', 'experimental')",
            name="ck_tc_results_kind",
        ),
        sa.CheckConstraint(
            """
            tc_method IN (
                'experimental', 'anisotropic_eliashberg',
                'isotropic_eliashberg', 'allen_dynes',
                'mcmillan', 'unknown'
            )
            """,
            name="ck_tc_results_method",
        ),
        sa.CheckConstraint(
            """
            (
                result_kind = 'theoretical'
                AND calculation_context_id IS NOT NULL
                AND experimental_context_id IS NULL
            )
            OR
            (
                result_kind = 'experimental'
                AND calculation_context_id IS NULL
                AND experimental_context_id IS NOT NULL
                AND tc_method = 'experimental'
            )
            """,
            name="ck_tc_results_context_kind",
        ),
        sa.CheckConstraint(
            """
            tc_value_k IS NOT NULL
            OR (tc_min_k IS NOT NULL AND tc_max_k IS NOT NULL)
            """,
            name="ck_tc_results_value",
        ),
        sa.CheckConstraint(
            """
            (tc_min_k IS NULL AND tc_max_k IS NULL)
            OR
            (
                tc_min_k IS NOT NULL
                AND tc_max_k IS NOT NULL
                AND tc_min_k <= tc_max_k
            )
            """,
            name="ck_tc_results_range",
        ),
        sa.CheckConstraint(
            """
            (tc_value_k IS NULL OR tc_value_k >= 0)
            AND (tc_min_k IS NULL OR tc_min_k >= 0)
            AND (uncertainty_k IS NULL OR uncertainty_k >= 0)
            """,
            name="ck_tc_results_nonnegative",
        ),
        sa.UniqueConstraint(
            "paper_id",
            "paper_revision",
            "source_fingerprint",
            name="uq_tc_results_source",
        ),
        sa.UniqueConstraint(
            "paper_id",
            "material_state_id",
            "tc_method",
            "representative_marker",
            name="uq_tc_results_representative",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_tc_results_identity_revision",
        ),
    )
    op.create_index(
        "ix_tc_results_paper_revision",
        "tc_results",
        ["paper_id", "paper_revision"],
    )
    op.create_index(
        "ix_tc_results_state_method",
        "tc_results",
        ["material_state_id", "tc_method"],
    )
    op.create_index(
        "ix_tc_results_method_value",
        "tc_results",
        ["tc_method", "tc_value_k"],
    )

    op.create_table(
        "property_definitions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("canonical_unit", sa.String(length=50), nullable=True),
        sa.Column("value_kind", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        *_timestamps(),
        sa.UniqueConstraint("code", name="uq_property_definitions_code"),
        sa.CheckConstraint(
            "value_kind IN ('number', 'range', 'text', 'boolean')",
            name="ck_property_definitions_value_kind",
        ),
        sa.CheckConstraint(
            """
            LOWER(code) NOT IN (
                'tc', 'critical_temperature', 'experimental',
                'anisotropic_eliashberg', 'isotropic_eliashberg',
                'allen_dynes', 'mcmillan'
            )
            """,
            name="ck_property_definitions_non_tc",
        ),
    )

    op.create_table(
        "superconductor_properties",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("structure_id", sa.BigInteger(), nullable=True),
        sa.Column("calculation_context_id", sa.BigInteger(), nullable=True),
        sa.Column(
            "property_definition_id",
            sa.Integer(),
            sa.ForeignKey("property_definitions.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("material_raw", sa.String(length=255), nullable=True),
        sa.Column("name_raw", sa.String(length=255), nullable=False),
        sa.Column("value_raw", sa.Text(), nullable=False),
        sa.Column("unit_raw", sa.String(length=100), nullable=True),
        sa.Column("value_number", sa.Numeric(30, 12), nullable=True),
        sa.Column("value_min", sa.Numeric(30, 12), nullable=True),
        sa.Column("value_max", sa.Numeric(30, 12), nullable=True),
        sa.Column("canonical_unit", sa.String(length=50), nullable=True),
        sa.Column("condition_note", sa.Text(), nullable=True),
        sa.Column("source_fingerprint", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            [
                "material_states.id",
                "material_states.paper_id",
                "material_states.paper_revision",
            ],
            name="fk_superconductor_properties_state_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_superconductor_properties_structure_revision",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "calculation_context_id",
                "material_state_id",
                "paper_id",
                "paper_revision",
            ],
            [
                "calculation_contexts.id",
                "calculation_contexts.material_state_id",
                "calculation_contexts.paper_id",
                "calculation_contexts.paper_revision",
            ],
            name="fk_superconductor_properties_calculation_revision",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            """
            value_number IS NOT NULL
            OR (value_min IS NOT NULL AND value_max IS NOT NULL)
            OR CHAR_LENGTH(TRIM(value_raw)) > 0
            """,
            name="ck_superconductor_properties_value",
        ),
        sa.CheckConstraint(
            """
            (value_min IS NULL AND value_max IS NULL)
            OR
            (
                value_min IS NOT NULL
                AND value_max IS NOT NULL
                AND value_min <= value_max
            )
            """,
            name="ck_superconductor_properties_range",
        ),
        sa.UniqueConstraint(
            "paper_id",
            "paper_revision",
            "source_fingerprint",
            name="uq_superconductor_properties_source",
        ),
        sa.UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_superconductor_properties_identity_revision",
        ),
    )
    op.create_index(
        "ix_superconductor_properties_paper_revision",
        "superconductor_properties",
        ["paper_id", "paper_revision"],
    )
    op.create_index(
        "ix_superconductor_properties_definition",
        "superconductor_properties",
        ["property_definition_id"],
    )
    op.create_index(
        "ix_superconductor_properties_state",
        "superconductor_properties",
        ["material_state_id"],
    )

    link_tables = (
        (
            "tc_result_evidences",
            "tc_result_id",
            "tc_results",
            "uq_tc_result_evidences",
            "fk_tc_result_evidences_result",
        ),
        (
            "structure_model_evidences",
            "structure_id",
            "structure_models",
            "uq_structure_model_evidences",
            "fk_structure_model_evidences_structure",
        ),
        (
            "superconductor_property_evidences",
            "superconductor_property_id",
            "superconductor_properties",
            "uq_superconductor_property_evidences",
            "fk_superconductor_property_evidences_property",
        ),
    )
    for table_name, entity_column, entity_table, unique_name, entity_fk_name in link_tables:
        op.create_table(
            table_name,
            sa.Column(entity_column, sa.BigInteger(), nullable=False),
            sa.Column("paper_evidence_id", sa.Integer(), nullable=False),
            sa.Column("paper_id", sa.Integer(), nullable=False),
            sa.Column("paper_revision", sa.Integer(), nullable=False),
            sa.Column(
                "evidence_role",
                sa.String(length=32),
                nullable=False,
                server_default="primary",
            ),
            sa.ForeignKeyConstraint(
                [entity_column, "paper_id", "paper_revision"],
                [
                    f"{entity_table}.id",
                    f"{entity_table}.paper_id",
                    f"{entity_table}.paper_revision",
                ],
                name=entity_fk_name,
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["paper_evidence_id", "paper_id", "paper_revision"],
                [
                    "paper_evidences.id",
                    "paper_evidences.paper_id",
                    "paper_evidences.paper_revision",
                ],
                name=f"fk_{table_name}_evidence",
                ondelete="CASCADE",
            ),
            sa.UniqueConstraint(
                entity_column,
                "paper_evidence_id",
                name=unique_name,
            ),
        )
        op.create_index(
            f"ix_{table_name}_evidence",
            table_name,
            ["paper_evidence_id"],
        )


def _create_legacy_tables() -> None:
    op.create_table(
        "superconductor_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "superconductor_id",
            sa.Integer(),
            sa.ForeignKey("superconductors.id"),
            nullable=False,
        ),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id")),
        sa.Column("source_label", sa.String(length=255), nullable=False),
        sa.Column("pressure_gpa", sa.Float(), nullable=False),
        sa.Column("space_group_symbol", sa.String(length=100)),
        sa.Column("space_group_number", sa.Integer()),
        sa.Column("crystal_structure", sa.String(length=255)),
        sa.Column("thermodynamically_stable", sa.Boolean()),
        sa.Column("dynamically_stable", sa.Boolean()),
        sa.Column("energy_above_hull", sa.Float()),
        sa.Column("mcmillan_tc", sa.Float()),
        sa.Column("allen_dynes_tc", sa.Float()),
        sa.Column("isotropic_eliashberg_tc", sa.Float()),
        sa.Column("anisotropic_eliashberg_tc", sa.Float()),
        sa.Column("experimental_tc", sa.Float()),
        sa.Column("lambda_value", sa.Float()),
        sa.Column("omega_log", sa.Float()),
        sa.Column("n_ef_total", sa.Float()),
        sa.Column("element_n_ef", sa.JSON()),
        sa.Column("pseudopotential_type", sa.String(length=100)),
        sa.Column("pseudopotential_name", sa.String(length=255)),
        sa.Column("exchange_correlation_functional", sa.String(length=100)),
        sa.Column("calculation_code", sa.String(length=100)),
        sa.Column("k_grid", sa.String(length=100)),
        sa.Column("q_grid", sa.String(length=100)),
        sa.Column("energy_cutoff_value", sa.Float()),
        sa.Column("energy_cutoff_unit", sa.String(length=50)),
        sa.Column("show_in_chart", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("s_factor", sa.Float()),
        sa.Column("method", sa.String(length=255)),
        sa.Column("note", sa.Text()),
        sa.Column("article_type", sa.String(length=10)),
        sa.Column("superconductor_type", sa.String(length=10)),
        *_timestamps(),
    )
    for name, columns in (
        ("ix_superconductor_records_paper_id", ["paper_id"]),
        ("ix_superconductor_records_pressure_gpa", ["pressure_gpa"]),
        ("ix_superconductor_records_show_in_chart", ["show_in_chart"]),
        ("ix_superconductor_records_source_label", ["source_label"]),
        ("ix_superconductor_records_superconductor_id", ["superconductor_id"]),
    ):
        op.create_index(name, "superconductor_records", columns)

    op.create_table(
        "superconductors_structures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "superconductor_id",
            sa.Integer(),
            sa.ForeignKey("superconductors.id"),
            nullable=False,
        ),
        sa.Column("pressure_gpa", sa.Float(), nullable=False),
        sa.Column("space_group_symbol", sa.String(length=100)),
        sa.Column("space_group_number", sa.Integer()),
        sa.Column("structure_format", sa.String(length=20), nullable=False),
        sa.Column("structure_text", sa.Text(), nullable=False),
        sa.Column("structure_hash", sa.String(length=64), nullable=False),
        sa.Column("atom_count", sa.Integer()),
        sa.Column("elements_list", sa.JSON()),
        sa.Column("cell_parameters", sa.JSON()),
        sa.Column("volume", sa.Float()),
        sa.Column("review_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_label", sa.String(length=255)),
        sa.Column("created_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        *_timestamps(),
    )


def downgrade() -> None:
    for table_name in (
        "superconductor_property_evidences",
        "structure_model_evidences",
        "tc_result_evidences",
        "superconductor_properties",
        "property_definitions",
        "tc_results",
        "experimental_contexts",
        "calculation_contexts",
    ):
        op.drop_table(table_name)
    op.drop_constraint(
        "fk_structure_models_parent_revision",
        "structure_models",
        type_="foreignkey",
    )
    op.drop_table("structure_models")
    op.drop_table("material_states")

    _create_legacy_tables()

    op.drop_index(
        "ix_superconductors_isotope_signature",
        table_name="superconductors",
    )
    op.drop_constraint(
        "uq_superconductors_composition_key",
        "superconductors",
        type_="unique",
    )
    op.drop_column("superconductors", "isotope_signature")
    op.drop_column("superconductors", "composition_key")
