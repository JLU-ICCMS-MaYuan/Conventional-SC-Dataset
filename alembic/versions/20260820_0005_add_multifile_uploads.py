"""add multi-file uploads and paper access fields

Revision ID: 20260820_0005
Revises: 20260820_0004
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0005"
down_revision = "20260820_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("papers", sa.Column("upload_task_id", sa.String(length=32), nullable=True))
    op.add_column("papers", sa.Column("admin_internal_note", sa.Text(), nullable=True))
    op.create_index("ix_papers_upload_task_id", "papers", ["upload_task_id"], unique=True)

    op.create_table(
        "paper_files",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("original_filename", sa.String(length=500), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("paper_id", "sort_order", name="uq_paper_files_order"),
    )
    op.create_index("ix_paper_files_paper_id", "paper_files", ["paper_id"])
    op.create_index("ix_paper_files_sha256", "paper_files", ["sha256"])

    op.add_column("paper_chunks", sa.Column("paper_file_id", sa.Integer(), nullable=True))
    op.add_column("paper_chunks", sa.Column("page_start", sa.Integer(), nullable=True))
    op.add_column("paper_chunks", sa.Column("page_end", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_paper_chunks_paper_file_id", "paper_chunks", "paper_files",
        ["paper_file_id"], ["id"],
    )
    op.create_index("ix_paper_chunks_paper_file_id", "paper_chunks", ["paper_file_id"])

    op.create_table(
        "paper_evidences",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), sa.ForeignKey("papers.id"), nullable=False),
        sa.Column("paper_file_id", sa.Integer(), sa.ForeignKey("paper_files.id"), nullable=True),
        sa.Column("field_path", sa.String(length=255), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=True),
        sa.Column("section", sa.String(length=500), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_paper_evidences_paper_id", "paper_evidences", ["paper_id"])
    op.create_index("ix_paper_evidences_paper_file_id", "paper_evidences", ["paper_file_id"])


def downgrade() -> None:
    op.drop_index("ix_paper_evidences_paper_file_id", table_name="paper_evidences")
    op.drop_index("ix_paper_evidences_paper_id", table_name="paper_evidences")
    op.drop_table("paper_evidences")
    op.drop_index("ix_paper_chunks_paper_file_id", table_name="paper_chunks")
    op.drop_constraint("fk_paper_chunks_paper_file_id", "paper_chunks", type_="foreignkey")
    op.drop_column("paper_chunks", "page_end")
    op.drop_column("paper_chunks", "page_start")
    op.drop_column("paper_chunks", "paper_file_id")
    op.drop_index("ix_paper_files_sha256", table_name="paper_files")
    op.drop_index("ix_paper_files_paper_id", table_name="paper_files")
    op.drop_table("paper_files")
    op.drop_index("ix_papers_upload_task_id", table_name="papers")
    op.drop_column("papers", "admin_internal_note")
    op.drop_column("papers", "upload_task_id")
