"""relax material_states pressure range to allow one-sided intervals

Revision ID: 20260826_0016
Revises: 20260826_0015
Create Date: 2026-08-26
"""

from alembic import op


revision = "20260826_0016"
down_revision = "20260826_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "ck_material_states_pressure_range", "material_states", type_="check"
    )
    op.create_check_constraint(
        "ck_material_states_pressure_range",
        "material_states",
        "pressure_min_gpa IS NULL OR pressure_max_gpa IS NULL "
        "OR pressure_min_gpa <= pressure_max_gpa",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_material_states_pressure_range", "material_states", type_="check"
    )
    op.create_check_constraint(
        "ck_material_states_pressure_range",
        "material_states",
        "(pressure_min_gpa IS NULL AND pressure_max_gpa IS NULL) "
        "OR (pressure_min_gpa IS NOT NULL AND pressure_max_gpa IS NOT NULL "
        "AND pressure_min_gpa <= pressure_max_gpa)",
    )
