"""create news_items table for manual news

Revision ID: 20260831_0064
Revises: 20260831_0063
Create Date: 2026-08-31 14:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260831_0064'
down_revision = '20260831_0063'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'news_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_date', sa.String(length=20), nullable=True),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('link', sa.String(length=1000), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_news_items_event_date', 'news_items', ['event_date'], unique=False)


def downgrade():
    op.drop_index('idx_news_items_event_date', table_name='news_items')
    op.drop_table('news_items')
