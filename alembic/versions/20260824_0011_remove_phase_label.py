"""Remove the ambiguous material-state phase label.

Revision ID: 20260824_0011
Revises: 20260824_0010
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0011"
down_revision = "20260824_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index(
        "ix_material_states_paper_material_phase",
        table_name="material_states",
    )
    op.drop_column("material_states", "phase_label")
    op.create_index(
        "ix_material_states_paper_material_space_group",
        "material_states",
        [
            "paper_id",
            "superconductor_id",
            "reported_space_group_symbol",
            "reported_space_group_number",
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_material_states_paper_material_space_group",
        table_name="material_states",
    )
    op.add_column("material_states", sa.Column("phase_label", sa.String(length=255), nullable=True))
    op.create_index(
        "ix_material_states_paper_material_phase",
        "material_states",
        ["paper_id", "superconductor_id", "phase_label"],
    )
