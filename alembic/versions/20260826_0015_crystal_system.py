"""add material_states.crystal_system

Revision ID: 20260826_0015
Revises: 20260826_0014
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0015"
down_revision = "20260826_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "material_states",
        sa.Column(
            "crystal_system",
            sa.String(32),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_material_states_crystal_system",
        "material_states",
        "crystal_system IN ('triclinic', 'monoclinic', 'orthorhombic', "
        "'tetragonal', 'trigonal', 'hexagonal', 'cubic', 'unknown')",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_material_states_crystal_system", "material_states", type_="check"
    )
    op.drop_column("material_states", "crystal_system")
