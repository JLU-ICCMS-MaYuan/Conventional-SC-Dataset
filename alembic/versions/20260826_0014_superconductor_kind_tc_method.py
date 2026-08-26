"""add material_states.superconductor_kind and tc_results.tc_method_custom

Revision ID: 20260826_0014
Revises: 20260825_0013
Create Date: 2026-08-26
"""

from alembic import op
import sqlalchemy as sa


revision = "20260826_0014"
down_revision = "20260825_0013"
branch_labels = None
depends_on = None


OLD_TC_METHOD_CHECK = (
    "tc_method IN ('experimental', 'anisotropic_eliashberg', "
    "'isotropic_eliashberg', 'allen_dynes', 'mcmillan', 'unknown')"
)
NEW_TC_METHOD_CHECK = (
    "tc_method IN ('experimental', 'mcmillan', 'allen_dynes', "
    "'isotropic_eliashberg', 'anisotropic_eliashberg', 'scdft', 'other', 'unknown')"
)


def upgrade() -> None:
    op.add_column(
        "material_states",
        sa.Column(
            "superconductor_kind",
            sa.String(32),
            server_default="unknown",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_material_states_superconductor_kind",
        "material_states",
        "superconductor_kind IN ('conventional', 'unconventional', 'unknown')",
    )

    op.add_column(
        "tc_results",
        sa.Column("tc_method_custom", sa.String(128), nullable=True),
    )
    op.drop_constraint("ck_tc_results_method", "tc_results", type_="check")
    op.create_check_constraint(
        "ck_tc_results_method",
        "tc_results",
        NEW_TC_METHOD_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint("ck_tc_results_method", "tc_results", type_="check")
    op.create_check_constraint(
        "ck_tc_results_method",
        "tc_results",
        OLD_TC_METHOD_CHECK,
    )
    op.drop_column("tc_results", "tc_method_custom")

    op.drop_constraint(
        "ck_material_states_superconductor_kind", "material_states", type_="check"
    )
    op.drop_column("material_states", "superconductor_kind")
