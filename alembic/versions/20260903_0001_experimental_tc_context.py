"""enforce tc method driven contexts

Revision ID: experimental_tc_context
Revises: paper_citation_graph
Create Date: 2026-09-03

Issue #84：Tc 方法而不是 result_kind 决定实验与理论上下文的关联。
"""

from alembic import op
from sqlalchemy import text


revision = "experimental_tc_context"
down_revision = "paper_citation_graph"
branch_labels = None
depends_on = None


METHOD_DRIVEN_CONTEXT_CHECK = """
(
    tc_method = 'experimental'
    AND result_kind = 'experimental'
    AND calculation_context_id IS NULL
    AND experimental_context_id IS NOT NULL
)
OR
(
    tc_method <> 'experimental'
    AND result_kind = 'theoretical'
    AND calculation_context_id IS NOT NULL
    AND experimental_context_id IS NULL
)
"""

LEGACY_CONTEXT_CHECK = """
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
"""


def upgrade() -> None:
    connection = op.get_bind()
    missing_experimental_context = connection.execute(text(
        "SELECT id FROM tc_results "
        "WHERE tc_method = 'experimental' AND experimental_context_id IS NULL "
        "ORDER BY id"
    )).scalars().all()
    if missing_experimental_context:
        ids = ", ".join(str(item) for item in missing_experimental_context)
        raise RuntimeError(
            "无法迁移实验 Tc：以下 tc_results 缺少 experimental_context_id：" + ids
        )

    op.drop_constraint("ck_tc_results_context_kind", "tc_results", type_="check")
    connection.execute(text(
        "UPDATE tc_results "
        "SET result_kind = 'experimental', calculation_context_id = NULL "
        "WHERE tc_method = 'experimental'"
    ))
    connection.execute(text(
        "DELETE calculation_contexts FROM calculation_contexts "
        "LEFT JOIN tc_results ON tc_results.calculation_context_id = calculation_contexts.id "
        "LEFT JOIN superconductor_properties "
        "ON superconductor_properties.calculation_context_id = calculation_contexts.id "
        "WHERE tc_results.id IS NULL AND superconductor_properties.id IS NULL"
    ))
    op.create_check_constraint(
        "ck_tc_results_context_kind",
        "tc_results",
        METHOD_DRIVEN_CONTEXT_CHECK,
    )


def downgrade() -> None:
    op.drop_constraint("ck_tc_results_context_kind", "tc_results", type_="check")
    op.create_check_constraint(
        "ck_tc_results_context_kind",
        "tc_results",
        LEGACY_CONTEXT_CHECK,
    )
