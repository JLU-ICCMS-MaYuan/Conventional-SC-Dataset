"""add superconductors structures

Revision ID: 20260610_0002
Revises: 20260609_0001
Create Date: 2026-06-10
"""
from alembic import op
import sqlalchemy as sa


revision = "20260610_0002"
down_revision = "20260609_0001"
branch_labels = None
depends_on = None


def _timestamps():
    return (
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
    )


def upgrade():
    op.create_table(
        "superconductors_structures",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("superconductor_id", sa.Integer(), sa.ForeignKey("superconductors.id"), nullable=False),
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
    op.create_index("ix_superconductors_structures_superconductor_id", "superconductors_structures", ["superconductor_id"])
    op.create_index("ix_superconductors_structures_pressure_gpa", "superconductors_structures", ["pressure_gpa"])
    op.create_index("ix_superconductors_structures_space_group_symbol", "superconductors_structures", ["space_group_symbol"])
    op.create_index("ix_superconductors_structures_space_group_number", "superconductors_structures", ["space_group_number"])
    op.create_index("ix_superconductors_structures_structure_format", "superconductors_structures", ["structure_format"])
    op.create_index("ix_superconductors_structures_structure_hash", "superconductors_structures", ["structure_hash"])
    op.create_index("ix_superconductors_structures_review_status", "superconductors_structures", ["review_status"])
    op.create_index("ix_superconductors_structures_is_default", "superconductors_structures", ["is_default"])
    op.create_index("ix_superconductors_structures_source_type", "superconductors_structures", ["source_type"])
    op.create_index("ix_superconductors_structures_created_by_user_id", "superconductors_structures", ["created_by_user_id"])
    op.create_index(
        "ix_superconductors_structures_identity",
        "superconductors_structures",
        ["superconductor_id", "space_group_symbol", "space_group_number", "pressure_gpa"],
    )


def downgrade():
    op.drop_table("superconductors_structures")
