"""move Material family ownership from material states to papers

Revision ID: paper_material_families
Revises: fill_elemental_name_en
Create Date: 2026-09-02

Issue #79：一篇论文可以关联多个 Material family。升级时把同一论文各材料状态的
family 去重汇总到版本化关联表，再删除状态级外键。降级仅在每篇论文至多一个 family
时可无损执行；多 family 数据无法由旧模型表达，因此显式拒绝。
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


revision = "paper_material_families"
down_revision = "fill_elemental_name_en"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_material_families",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_family_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_material_families_paper_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["material_family_id"],
            ["material_families.id"],
            name="fk_paper_material_families_material_family",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "paper_id",
            "paper_revision",
            "material_family_id",
            name="pk_paper_material_families",
        ),
    )
    op.create_index(
        "ix_paper_material_families_material_family",
        "paper_material_families",
        ["material_family_id"],
    )

    connection = op.get_bind()
    connection.execute(text(
        "INSERT INTO paper_material_families "
        "(paper_id, paper_revision, material_family_id) "
        "SELECT DISTINCT paper_id, paper_revision, material_family_id "
        "FROM material_states WHERE material_family_id IS NOT NULL"
    ))

    op.drop_constraint(
        "fk_material_states_material_family",
        "material_states",
        type_="foreignkey",
    )
    op.drop_index("ix_material_states_material_family", table_name="material_states")
    op.drop_column("material_states", "material_family_id")


def downgrade() -> None:
    connection = op.get_bind()
    multiple = connection.execute(text(
        "SELECT COUNT(*) FROM ("
        "SELECT paper_id, paper_revision FROM paper_material_families "
        "GROUP BY paper_id, paper_revision HAVING COUNT(*) > 1"
        ") AS papers_with_multiple_families"
    )).scalar()
    if multiple:
        raise RuntimeError(
            f"存在 {multiple} 篇论文关联多个 Material family；"
            "旧状态级单值模型无法无损恢复，已拒绝降级。"
        )

    op.add_column(
        "material_states",
        sa.Column("material_family_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_material_states_material_family",
        "material_states",
        "material_families",
        ["material_family_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_material_states_material_family",
        "material_states",
        ["material_family_id"],
    )
    connection.execute(text(
        "UPDATE material_states SET material_family_id = ("
        "SELECT pmf.material_family_id FROM paper_material_families AS pmf "
        "WHERE pmf.paper_id = material_states.paper_id "
        "AND pmf.paper_revision = material_states.paper_revision"
        ")"
    ))
    op.drop_table("paper_material_families")
