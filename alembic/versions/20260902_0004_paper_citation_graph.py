"""add citation facts and paper graph marks

Revision ID: paper_citation_graph
Revises: paper_superconductor_kind
Create Date: 2026-09-02

Issue #81：引用的原始记录、解析状态和管理员里程碑均以 MySQL 为唯一事实来源。
图查询仅投影当前已审核版本，不能从 Neo4j 自由文本关系反向补造这些记录。
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql
from sqlalchemy import text


revision = "paper_citation_graph"
down_revision = "paper_superconductor_kind"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    missing_years = connection.execute(
        text("SELECT COUNT(*) FROM papers WHERE year IS NULL")
    ).scalar_one()
    if missing_years:
        raise RuntimeError(
            f"无法启用引用图谱：papers.year 仍有 {missing_years} 条空值，请先补全论文年份"
        )
    op.alter_column(
        "papers",
        "year",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
    op.create_table(
        "paper_reference_extractions",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("parser_name", sa.String(length=32), nullable=False, server_default="grobid"),
        sa.Column("parser_version", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint(
            "status IN ('succeeded', 'partial', 'failed', 'unavailable')",
            name="ck_paper_reference_extractions_status",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_reference_extractions_paper_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.PrimaryKeyConstraint("paper_id", "paper_revision"),
    )
    op.create_table(
        "paper_references",
        sa.Column("id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), primary_key=True, autoincrement=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("reference_index", sa.Integer(), nullable=False),
        sa.Column("raw_citation", sa.Text().with_variant(mysql.LONGTEXT(), "mysql"), nullable=False),
        sa.Column("doi", sa.String(length=255), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("normalized_title", sa.String(length=512), nullable=True),
        sa.Column("authors", sa.JSON(), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("cited_paper_id", sa.Integer(), nullable=True),
        sa.Column("match_status", sa.String(length=20), nullable=False, server_default="unmatched"),
        sa.Column("match_method", sa.String(length=20), nullable=True),
        sa.Column("match_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("reference_index >= 0", name="ck_paper_references_index"),
        sa.CheckConstraint(
            "match_status IN ('matched', 'unmatched', 'ambiguous')",
            name="ck_paper_references_match_status",
        ),
        sa.CheckConstraint(
            "match_method IS NULL OR match_method IN ('doi', 'title_year', 'manual')",
            name="ck_paper_references_match_method",
        ),
        sa.CheckConstraint(
            "(match_status = 'matched' AND cited_paper_id IS NOT NULL AND match_method IS NOT NULL) "
            "OR (match_status IN ('unmatched', 'ambiguous') AND cited_paper_id IS NULL AND match_method IS NULL)",
            name="ck_paper_references_match_consistency",
        ),
        sa.ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_references_citing_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cited_paper_id"],
            ["papers.id"],
            name="fk_paper_references_cited_paper",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("paper_id", "paper_revision", "reference_index", name="uq_paper_references_source_index"),
    )
    op.create_index("ix_paper_references_source_revision", "paper_references", ["paper_id", "paper_revision"])
    op.create_index("ix_paper_references_doi", "paper_references", ["doi"])
    op.create_index("ix_paper_references_normalized_title", "paper_references", ["normalized_title"])
    op.create_index("ix_paper_references_year", "paper_references", ["year"])
    op.create_index("ix_paper_references_cited_paper", "paper_references", ["cited_paper_id"])
    op.create_table(
        "paper_graph_marks",
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("mark_type", sa.String(length=20), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("mark_type IN ('origin', 'breakthrough')", name="ck_paper_graph_marks_type"),
        sa.ForeignKeyConstraint(["paper_id"], ["papers.id"], name="fk_paper_graph_marks_paper", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], name="fk_paper_graph_marks_user", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("paper_id", "mark_type"),
    )


def downgrade() -> None:
    op.drop_table("paper_graph_marks")
    op.drop_index("ix_paper_references_cited_paper", table_name="paper_references")
    op.drop_index("ix_paper_references_year", table_name="paper_references")
    op.drop_index("ix_paper_references_normalized_title", table_name="paper_references")
    op.drop_index("ix_paper_references_doi", table_name="paper_references")
    op.drop_index("ix_paper_references_source_revision", table_name="paper_references")
    op.drop_table("paper_references")
    op.drop_table("paper_reference_extractions")
    op.alter_column(
        "papers",
        "year",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )
