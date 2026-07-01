"""add missing columns from sqlite schema

Revision ID: b95420be551f
Revises: 20260610_0002
Create Date: 2026-06-17 14:45:31.399706
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = 'b95420be551f'
down_revision: Union[str, None] = '20260610_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('superconductor_records', sa.Column('article_type', sa.String(length=10), nullable=True))
    op.add_column('superconductor_records', sa.Column('superconductor_type', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('superconductor_records', 'superconductor_type')
    op.drop_column('superconductor_records', 'article_type')
