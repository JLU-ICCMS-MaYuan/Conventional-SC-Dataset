"""add current-generation paper lineage schema

Revision ID: 20260821_0007
Revises: 20260821_0006
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = "20260821_0007"
down_revision = "20260821_0006"
branch_labels = None
depends_on = None


_BUSINESS_TABLES = (
    "papers",
    "paper_files",
    "paper_chunks",
    "paper_evidences",
    "paper_review_events",
)


def _require_empty_business_tables() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    populated = []
    for table_name in _BUSINESS_TABLES:
        if not inspector.has_table(table_name):
            continue
        if bind.execute(sa.text(f"SELECT 1 FROM `{table_name}` LIMIT 1")).first():
            populated.append(table_name)
    if populated:
        names = ", ".join(populated)
        raise RuntimeError(
            "20260821_0007 仅支持全新空业务库；检测到已有数据表: "
            f"{names}。本迁移不会回填、转换或删除现有数据。"
        )


def _drop_foreign_keys_for_columns(table_name: str, columns: set[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if set(foreign_key.get("constrained_columns") or ()) == columns:
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    _require_empty_business_tables()

    for column in (
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("paper_type", sa.String(length=20), nullable=True),
        sa.Column("keywords_tags", sa.Text(), nullable=True),
        sa.Column("methodology", sa.Text(), nullable=True),
        sa.Column("key_finding", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("research_materials", sa.JSON(), nullable=True),
        sa.Column("referenced_materials", sa.JSON(), nullable=True),
        sa.Column("material_relations", sa.JSON(), nullable=True),
        sa.Column("builds_on", sa.JSON(), nullable=True),
    ):
        op.add_column("papers", column)
    op.alter_column(
        "papers",
        "doi",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.alter_column(
        "papers",
        "title",
        existing_type=sa.Text(),
        nullable=True,
    )
    op.alter_column(
        "papers",
        "authors",
        existing_type=sa.JSON(),
        nullable=True,
    )
    op.alter_column(
        "papers",
        "uploaded_by_user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.add_column(
        "papers",
        sa.Column(
            "content_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column("papers", sa.Column("approved_revision", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_papers_review_revision",
        "papers",
        """
        content_revision >= 1
        AND (
            (review_status = 'approved' AND approved_revision = content_revision)
            OR
            (review_status IN ('pending', 'rejected') AND approved_revision IS NULL)
        )
        """,
    )
    op.create_unique_constraint(
        "uq_papers_id_content_revision",
        "papers",
        ["id", "content_revision"],
    )
    op.create_index(
        "ix_papers_public_revision",
        "papers",
        ["review_status", "approved_revision", "content_revision"],
    )

    op.add_column(
        "paper_files",
        sa.Column(
            "paper_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.alter_column(
        "paper_files",
        "size",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.add_column(
        "paper_files",
        sa.Column(
            "main_marker",
            sa.Integer(),
            sa.Computed(
                "CASE WHEN role = 'main' THEN 1 ELSE NULL END",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_check_constraint(
        "ck_paper_files_role",
        "paper_files",
        "role IN ('main', 'supplementary', 'attachment')",
    )
    op.create_check_constraint("ck_paper_files_size", "paper_files", "size >= 0")
    op.create_check_constraint(
        "ck_paper_files_sort_order",
        "paper_files",
        "sort_order >= 0",
    )
    op.create_unique_constraint(
        "uq_paper_files_path",
        "paper_files",
        ["paper_id", "stored_path"],
    )
    op.create_unique_constraint(
        "uq_paper_files_main",
        "paper_files",
        ["paper_id", "main_marker"],
    )
    op.create_unique_constraint(
        "uq_paper_files_identity_revision",
        "paper_files",
        ["id", "paper_id", "paper_revision"],
    )
    _drop_foreign_keys_for_columns("paper_files", {"paper_id"})
    op.create_foreign_key(
        "fk_paper_files_paper_revision",
        "paper_files",
        "papers",
        ["paper_id", "paper_revision"],
        ["id", "content_revision"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_paper_files_paper_revision",
        "paper_files",
        ["paper_id", "paper_revision"],
    )

    op.add_column(
        "paper_chunks",
        sa.Column(
            "paper_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.alter_column(
        "paper_chunks",
        "paper_file_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "paper_chunks",
        "content",
        existing_type=sa.Text(),
        type_=mysql.LONGTEXT(),
        existing_nullable=False,
    )
    op.create_check_constraint(
        "ck_paper_chunks_chunk_index",
        "paper_chunks",
        "chunk_index >= 0",
    )
    op.create_check_constraint(
        "ck_paper_chunks_token_count",
        "paper_chunks",
        "token_count IS NULL OR token_count >= 0",
    )
    op.create_check_constraint(
        "ck_paper_chunks_pages",
        "paper_chunks",
        """
        (page_start IS NULL AND page_end IS NULL)
        OR
        (
            page_start IS NOT NULL
            AND page_end IS NOT NULL
            AND page_start >= 1
            AND page_end >= page_start
        )
        """,
    )
    op.create_unique_constraint(
        "uq_paper_chunks_file_index",
        "paper_chunks",
        ["paper_file_id", "chunk_index"],
    )
    op.create_unique_constraint(
        "uq_paper_chunks_identity_revision",
        "paper_chunks",
        ["id", "paper_id", "paper_revision"],
    )
    _drop_foreign_keys_for_columns("paper_chunks", {"paper_id"})
    _drop_foreign_keys_for_columns("paper_chunks", {"paper_file_id"})
    op.create_foreign_key(
        "fk_paper_chunks_file_revision",
        "paper_chunks",
        "paper_files",
        ["paper_file_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_paper_chunks_paper_revision",
        "paper_chunks",
        "papers",
        ["paper_id", "paper_revision"],
        ["id", "content_revision"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_paper_chunks_paper_revision",
        "paper_chunks",
        ["paper_id", "paper_revision"],
    )

    op.add_column(
        "paper_evidences",
        sa.Column(
            "paper_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.add_column(
        "paper_evidences",
        sa.Column("paper_chunk_id", sa.Integer(), nullable=False),
    )
    op.alter_column(
        "paper_evidences",
        "quote",
        existing_type=sa.Text(),
        type_=mysql.LONGTEXT(),
        existing_nullable=False,
    )
    _drop_foreign_keys_for_columns("paper_evidences", {"paper_file_id"})
    _drop_foreign_keys_for_columns("paper_evidences", {"paper_id"})
    op.drop_index("ix_paper_evidences_paper_file_id", table_name="paper_evidences")
    op.drop_column("paper_evidences", "paper_file_id")
    op.drop_column("paper_evidences", "chunk_index")
    op.create_unique_constraint(
        "uq_paper_evidences_identity_revision",
        "paper_evidences",
        ["id", "paper_id", "paper_revision"],
    )
    op.create_foreign_key(
        "fk_paper_evidences_chunk_revision",
        "paper_evidences",
        "paper_chunks",
        ["paper_chunk_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_paper_evidences_paper_revision",
        "paper_evidences",
        "papers",
        ["paper_id", "paper_revision"],
        ["id", "content_revision"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_paper_evidences_chunk",
        "paper_evidences",
        ["paper_chunk_id"],
    )
    op.create_index(
        "ix_paper_evidences_paper_revision",
        "paper_evidences",
        ["paper_id", "paper_revision"],
    )

    op.add_column(
        "paper_review_events",
        sa.Column(
            "paper_revision",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("1"),
        ),
    )
    op.alter_column(
        "paper_review_events",
        "reviewed_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.create_check_constraint(
        "ck_paper_review_events_revision",
        "paper_review_events",
        "paper_revision >= 1",
    )
    op.create_foreign_key(
        "fk_paper_review_events_paper",
        "paper_review_events",
        "papers",
        ["paper_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_paper_review_events_paper_revision",
        "paper_review_events",
        ["paper_id", "paper_revision", "reviewed_at"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_paper_review_events_paper",
        "paper_review_events",
        type_="foreignkey",
    )
    op.drop_index(
        "ix_paper_review_events_paper_revision",
        table_name="paper_review_events",
    )
    op.drop_constraint(
        "ck_paper_review_events_revision",
        "paper_review_events",
        type_="check",
    )
    op.alter_column(
        "paper_review_events",
        "reviewed_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        server_default=None,
    )
    op.drop_column("paper_review_events", "paper_revision")

    op.drop_constraint(
        "fk_paper_evidences_paper_revision",
        "paper_evidences",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_paper_evidences_chunk_revision",
        "paper_evidences",
        type_="foreignkey",
    )
    op.drop_index("ix_paper_evidences_paper_revision", table_name="paper_evidences")
    op.drop_index("ix_paper_evidences_chunk", table_name="paper_evidences")
    op.drop_constraint(
        "uq_paper_evidences_identity_revision",
        "paper_evidences",
        type_="unique",
    )
    op.add_column(
        "paper_evidences",
        sa.Column("paper_file_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "paper_evidences",
        sa.Column("chunk_index", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_paper_evidences_paper_file_id",
        "paper_evidences",
        "paper_files",
        ["paper_file_id"],
        ["id"],
    )
    op.create_index(
        "ix_paper_evidences_paper_file_id",
        "paper_evidences",
        ["paper_file_id"],
    )
    op.drop_column("paper_evidences", "paper_chunk_id")
    op.drop_column("paper_evidences", "paper_revision")
    op.alter_column(
        "paper_evidences",
        "quote",
        existing_type=mysql.LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_paper_evidences_paper_id_legacy",
        "paper_evidences",
        "papers",
        ["paper_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_paper_chunks_paper_revision",
        "paper_chunks",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_paper_chunks_file_revision",
        "paper_chunks",
        type_="foreignkey",
    )
    op.drop_index("ix_paper_chunks_paper_revision", table_name="paper_chunks")
    op.drop_constraint(
        "uq_paper_chunks_identity_revision",
        "paper_chunks",
        type_="unique",
    )
    op.drop_constraint(
        "uq_paper_chunks_file_index",
        "paper_chunks",
        type_="unique",
    )
    op.drop_constraint("ck_paper_chunks_pages", "paper_chunks", type_="check")
    op.drop_constraint("ck_paper_chunks_token_count", "paper_chunks", type_="check")
    op.drop_constraint("ck_paper_chunks_chunk_index", "paper_chunks", type_="check")
    op.alter_column(
        "paper_chunks",
        "paper_file_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.drop_column("paper_chunks", "paper_revision")
    op.alter_column(
        "paper_chunks",
        "content",
        existing_type=mysql.LONGTEXT(),
        type_=sa.Text(),
        existing_nullable=False,
    )
    op.create_foreign_key(
        "fk_paper_chunks_paper_id_legacy",
        "paper_chunks",
        "papers",
        ["paper_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_paper_chunks_paper_file_id",
        "paper_chunks",
        "paper_files",
        ["paper_file_id"],
        ["id"],
    )

    op.drop_constraint(
        "fk_paper_files_paper_revision",
        "paper_files",
        type_="foreignkey",
    )
    op.drop_index("ix_paper_files_paper_revision", table_name="paper_files")
    op.drop_constraint(
        "uq_paper_files_identity_revision",
        "paper_files",
        type_="unique",
    )
    op.drop_constraint("uq_paper_files_main", "paper_files", type_="unique")
    op.drop_constraint("uq_paper_files_path", "paper_files", type_="unique")
    op.drop_constraint("ck_paper_files_sort_order", "paper_files", type_="check")
    op.drop_constraint("ck_paper_files_size", "paper_files", type_="check")
    op.drop_constraint("ck_paper_files_role", "paper_files", type_="check")
    op.drop_column("paper_files", "main_marker")
    op.alter_column(
        "paper_files",
        "size",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
    op.drop_column("paper_files", "paper_revision")
    op.create_foreign_key(
        "fk_paper_files_paper_id_legacy",
        "paper_files",
        "papers",
        ["paper_id"],
        ["id"],
    )

    op.drop_index("ix_papers_public_revision", table_name="papers")
    op.drop_constraint(
        "uq_papers_id_content_revision",
        "papers",
        type_="unique",
    )
    op.drop_constraint("ck_papers_review_revision", "papers", type_="check")
    op.drop_column("papers", "approved_revision")
    op.drop_column("papers", "content_revision")
    op.alter_column(
        "papers",
        "uploaded_by_user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "papers",
        "authors",
        existing_type=sa.JSON(),
        nullable=False,
    )
    op.alter_column(
        "papers",
        "title",
        existing_type=sa.Text(),
        nullable=False,
    )
    op.alter_column(
        "papers",
        "doi",
        existing_type=sa.String(length=255),
        nullable=False,
    )
    for column_name in (
        "builds_on",
        "material_relations",
        "referenced_materials",
        "research_materials",
        "rationale",
        "key_finding",
        "methodology",
        "keywords_tags",
        "paper_type",
        "summary",
    ):
        op.drop_column("papers", column_name)
