"""create chart_groups and chart_group_items tables

Go 侧 goserver/models/models.go 早已定义 ChartGroup / ChartGroupItem 并注册了
/api/chart-groups 全套 CRUD 路由，但从未有迁移建表，导致图表组合功能整体不可用
（goserver 日志持续报 Error 1146: Table 'scwiki.chart_groups' doesn't exist），
超级管理员工作台的「图表管理」卡片也因此恒显示 0。本迁移补齐这两张表。

字段与 Go 模型逐一对齐。两处刻意的取舍：

1. chart_group_items.key_property_id 用 INTEGER UNSIGNED，而它逻辑上指向
   superconductor_properties.id（BIGINT）。Go 模型该字段是 *uint，若改用 BIGINT
   会与 GORM 的读写类型不符。类型既然不匹配就无法建立该外键约束，此处只保留普通
   索引，引用完整性由应用层保证。修正需同时调整 Go 模型，超出本次范围。

2. created_by 指向 users.id（INT），类型一致，但同样不建外键：用户已改为「注销而
   非删除」，历史关系需保留，加 FK 反而会阻碍既有的账号治理语义。

Revision ID: 20260831_0065
Revises: 20260831_0064
Create Date: 2026-08-31 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


revision = '20260831_0065'
down_revision = '20260831_0064'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'chart_groups',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_preset', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('is_public', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.Column('created_by', mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_chart_groups_is_preset', 'chart_groups', ['is_preset'])
    op.create_index('idx_chart_groups_is_public', 'chart_groups', ['is_public'])
    op.create_index('idx_chart_groups_created_by', 'chart_groups', ['created_by'])

    op.create_table(
        'chart_group_items',
        sa.Column('id', mysql.INTEGER(unsigned=True), autoincrement=True, nullable=False),
        sa.Column('group_id', mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column('key_property_id', mysql.INTEGER(unsigned=True), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('custom_label', sa.Text(), nullable=True),
        sa.Column('custom_tc', sa.Float(), nullable=True),
        sa.Column('custom_pressure', sa.Float(), nullable=True),
        sa.Column('custom_type', sa.String(length=20), nullable=True),
        sa.Column('custom_article_type', sa.String(length=10), nullable=True),
        sa.Column('custom_year', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        # 组合被删除时其数据点一并清理，避免留下孤儿行
        sa.ForeignKeyConstraint(['group_id'], ['chart_groups.id'], ondelete='CASCADE'),
    )
    op.create_index('idx_chart_group_items_group_id', 'chart_group_items', ['group_id'])
    op.create_index('idx_chart_group_items_key_property_id', 'chart_group_items', ['key_property_id'])


def downgrade():
    op.drop_index('idx_chart_group_items_key_property_id', table_name='chart_group_items')
    op.drop_index('idx_chart_group_items_group_id', table_name='chart_group_items')
    op.drop_table('chart_group_items')
    op.drop_index('idx_chart_groups_created_by', table_name='chart_groups')
    op.drop_index('idx_chart_groups_is_public', table_name='chart_groups')
    op.drop_index('idx_chart_groups_is_preset', table_name='chart_groups')
    op.drop_table('chart_groups')
