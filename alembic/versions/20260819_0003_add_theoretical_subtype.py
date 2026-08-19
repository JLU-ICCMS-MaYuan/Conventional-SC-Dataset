"""add theoretical paper subtype

Revision ID: 20260819_0003
Revises: b95420be551f
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0003"
down_revision = "b95420be551f"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("papers", sa.Column("theoretical_subtype", sa.String(length=20), nullable=True))


def downgrade():
    op.drop_column("papers", "theoretical_subtype")
