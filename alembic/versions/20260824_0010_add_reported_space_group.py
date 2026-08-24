"""add reported space group to material states

Revision ID: 20260824_0010
Revises: 20260824_0009
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0010"
down_revision = "20260824_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_states",
        sa.Column("reported_space_group_symbol", sa.String(100), nullable=True),
    )
    op.add_column(
        "material_states",
        sa.Column("reported_space_group_number", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_material_states_reported_space_group",
        "material_states",
        "reported_space_group_number IS NULL OR reported_space_group_number BETWEEN 1 AND 230",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_material_states_reported_space_group",
        "material_states",
        type_="check",
    )
    op.drop_column("material_states", "reported_space_group_number")
    op.drop_column("material_states", "reported_space_group_symbol")
