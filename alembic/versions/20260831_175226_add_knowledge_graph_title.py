"""add knowledge_graph_title to papers

Revision ID: add_kg_title
Revises: 20260831_0066
Create Date: 2026-08-31 17:52:26

"""
from alembic import op
import sqlalchemy as sa

revision = 'add_kg_title'
down_revision = '20260831_0066'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('papers', sa.Column('knowledge_graph_title', sa.String(200), nullable=True))


def downgrade():
    op.drop_column('papers', 'knowledge_graph_title')
