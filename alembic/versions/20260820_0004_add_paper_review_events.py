"""add paper review events for contribution ranking

Revision ID: 20260820_0004
Revises: 20260819_0003
Create Date: 2026-08-20
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0004"
down_revision = "20260819_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paper_review_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("reviewer_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("review_comment", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default="single"),
        sa.CheckConstraint(
            "status IN ('approved', 'rejected', 'pending')",
            name="ck_paper_review_events_status",
        ),
        sa.UniqueConstraint("request_id", name="uq_paper_review_events_request_id"),
    )
    op.create_index(
        "ix_paper_review_events_reviewer_time",
        "paper_review_events",
        ["reviewer_user_id", "reviewed_at", "id"],
    )
    op.create_index(
        "ix_paper_review_events_paper_time",
        "paper_review_events",
        ["paper_id", "reviewed_at"],
    )
    op.execute(sa.text("""
        INSERT INTO paper_review_events
            (paper_id, reviewer_user_id, status, review_comment, reviewed_at, request_id, source)
        SELECT id, reviewed_by_user_id, review_status, review_comment, reviewed_at,
               CONCAT('backfill-paper-', id), 'backfill'
        FROM papers
        WHERE reviewed_by_user_id IS NOT NULL
          AND reviewed_at IS NOT NULL
          AND review_status IN ('approved', 'rejected', 'pending')
    """))


def downgrade() -> None:
    op.drop_index("ix_paper_review_events_paper_time", table_name="paper_review_events")
    op.drop_index("ix_paper_review_events_reviewer_time", table_name="paper_review_events")
    op.drop_table("paper_review_events")
