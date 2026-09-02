"""move Superconductor type ownership from material states to papers

Revision ID: paper_superconductor_kind
Revises: paper_material_families
Create Date: 2026-09-02

Issue #80：每篇论文 revision 只有一个 Superconductor type。升级时按论文版本
汇总旧状态级值；只有一个非 unknown 值时保留，常规和非常规同时出现时写 unknown，
避免依赖状态行顺序而悄悄篡改历史分类。
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "paper_superconductor_kind"
down_revision = "paper_material_families"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "papers",
        sa.Column(
            "superconductor_kind",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_check_constraint(
        "ck_papers_superconductor_kind",
        "papers",
        "superconductor_kind IN ('conventional', 'unconventional', 'unknown')",
    )
    connection = op.get_bind()
    connection.execute(text(
        "UPDATE papers AS p "
        "LEFT JOIN ("
        "SELECT paper_id, paper_revision, "
        "CASE WHEN COUNT(DISTINCT CASE WHEN superconductor_kind IN "
        "('conventional', 'unconventional') THEN superconductor_kind END) = 1 "
        "THEN MAX(CASE WHEN superconductor_kind IN "
        "('conventional', 'unconventional') THEN superconductor_kind END) "
        "ELSE 'unknown' END AS superconductor_kind "
        "FROM material_states GROUP BY paper_id, paper_revision"
        ") AS legacy ON legacy.paper_id = p.id "
        "AND legacy.paper_revision = p.content_revision "
        "SET p.superconductor_kind = COALESCE(legacy.superconductor_kind, 'unknown')"
    ))
    op.drop_constraint(
        "ck_material_states_superconductor_kind",
        "material_states",
        type_="check",
    )
    op.drop_column("material_states", "superconductor_kind")


def downgrade() -> None:
    op.add_column(
        "material_states",
        sa.Column(
            "superconductor_kind",
            sa.String(length=32),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_check_constraint(
        "ck_material_states_superconductor_kind",
        "material_states",
        "superconductor_kind IN ('conventional', 'unconventional', 'unknown')",
    )
    connection = op.get_bind()
    connection.execute(text(
        "UPDATE material_states AS ms JOIN papers AS p "
        "ON p.id = ms.paper_id AND p.content_revision = ms.paper_revision "
        "SET ms.superconductor_kind = p.superconductor_kind"
    ))
    op.drop_constraint("ck_papers_superconductor_kind", "papers", type_="check")
    op.drop_column("papers", "superconductor_kind")
