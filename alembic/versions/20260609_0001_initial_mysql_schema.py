"""initial mysql schema

Revision ID: 20260609_0001
Revises:
Create Date: 2026-06-09
"""
from alembic import op
import sqlalchemy as sa


revision = "20260609_0001"
down_revision = None
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def upgrade():
    op.create_table(
        "periodic_table_elements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("atomic_number", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=8), nullable=False),
        sa.Column("english_name", sa.String(length=100), nullable=False),
        sa.Column("chinese_name", sa.String(length=100)),
        sa.Column("atomic_mass", sa.Float()),
        sa.Column("period_number", sa.Integer()),
        sa.Column("group_number", sa.Integer()),
        sa.Column("category", sa.String(length=100)),
        *_timestamps(),
        sa.UniqueConstraint("atomic_number", name="uq_periodic_table_elements_atomic_number"),
        sa.UniqueConstraint("symbol", name="uq_periodic_table_elements_symbol"),
    )
    op.create_index("ix_periodic_table_elements_atomic_number", "periodic_table_elements", ["atomic_number"])
    op.create_index("ix_periodic_table_elements_symbol", "periodic_table_elements", ["symbol"])

    op.create_table(
        "chemical_systems",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("system_key", sa.String(length=255), nullable=False),
        sa.Column("elements_list", sa.JSON(), nullable=False),
        sa.Column("element_count", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("system_key", name="uq_chemical_systems_system_key"),
    )
    op.create_index("ix_chemical_systems_system_key", "chemical_systems", ["system_key"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("real_name", sa.String(length=100), nullable=False),
        sa.Column("affiliation", sa.String(length=255)),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column("is_approved", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("is_email_verified", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("verification_code", sa.String(length=16)),
        sa.Column("verification_expires", sa.DateTime(timezone=True)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("approved_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        *_timestamps(),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )
    op.create_index("ix_users_email", "users", ["email"])
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "superconductors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chemical_system_id", sa.Integer(), sa.ForeignKey("chemical_systems.id"), nullable=False),
        sa.Column("chemical_formula", sa.String(length=255), nullable=False),
        sa.Column("formula_normalized", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("elements_list", sa.JSON(), nullable=False),
        sa.Column("composition", sa.JSON(), nullable=False),
        sa.Column("element_ratio", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("formula_normalized", name="uq_superconductors_formula_normalized"),
    )
    op.create_index("ix_superconductors_chemical_system_id", "superconductors", ["chemical_system_id"])
    op.create_index("ix_superconductors_formula_normalized", "superconductors", ["formula_normalized"])

    op.create_table(
        "papers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("doi", sa.String(length=255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("journal", sa.String(length=255)),
        sa.Column("volume", sa.String(length=100)),
        sa.Column("pages", sa.String(length=100)),
        sa.Column("year", sa.Integer()),
        sa.Column("abstract", sa.Text()),
        sa.Column("authors", sa.JSON(), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reviewed_by_user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("review_status", sa.String(length=50), nullable=False, server_default="pending"),
        sa.Column("reviewed_at", sa.DateTime(timezone=True)),
        sa.Column("review_comment", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint("doi", name="uq_papers_doi"),
    )
    op.create_index("ix_papers_doi", "papers", ["doi"])
    op.create_index("ix_papers_review_status", "papers", ["review_status"])
    op.create_index("ix_papers_reviewed_by_user_id", "papers", ["reviewed_by_user_id"])
    op.create_index("ix_papers_uploaded_by_user_id", "papers", ["uploaded_by_user_id"])
    op.create_index("ix_papers_year", "papers", ["year"])

    op.create_table(
        "superconductor_records",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("superconductor_id", sa.Integer(), sa.ForeignKey("superconductors.id"), nullable=False),
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
        *_timestamps(),
    )
    op.create_index("ix_superconductor_records_paper_id", "superconductor_records", ["paper_id"])
    op.create_index("ix_superconductor_records_pressure_gpa", "superconductor_records", ["pressure_gpa"])
    op.create_index("ix_superconductor_records_show_in_chart", "superconductor_records", ["show_in_chart"])
    op.create_index("ix_superconductor_records_source_label", "superconductor_records", ["source_label"])
    op.create_index("ix_superconductor_records_superconductor_id", "superconductor_records", ["superconductor_id"])


def downgrade():
    op.drop_index("ix_superconductor_records_superconductor_id", table_name="superconductor_records")
    op.drop_index("ix_superconductor_records_source_label", table_name="superconductor_records")
    op.drop_index("ix_superconductor_records_show_in_chart", table_name="superconductor_records")
    op.drop_index("ix_superconductor_records_pressure_gpa", table_name="superconductor_records")
    op.drop_index("ix_superconductor_records_paper_id", table_name="superconductor_records")
    op.drop_table("superconductor_records")

    op.drop_index("ix_papers_year", table_name="papers")
    op.drop_index("ix_papers_uploaded_by_user_id", table_name="papers")
    op.drop_index("ix_papers_reviewed_by_user_id", table_name="papers")
    op.drop_index("ix_papers_review_status", table_name="papers")
    op.drop_index("ix_papers_doi", table_name="papers")
    op.drop_table("papers")

    op.drop_index("ix_superconductors_formula_normalized", table_name="superconductors")
    op.drop_index("ix_superconductors_chemical_system_id", table_name="superconductors")
    op.drop_table("superconductors")

    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.drop_index("ix_chemical_systems_system_key", table_name="chemical_systems")
    op.drop_table("chemical_systems")

    op.drop_index("ix_periodic_table_elements_symbol", table_name="periodic_table_elements")
    op.drop_index("ix_periodic_table_elements_atomic_number", table_name="periodic_table_elements")
    op.drop_table("periodic_table_elements")
