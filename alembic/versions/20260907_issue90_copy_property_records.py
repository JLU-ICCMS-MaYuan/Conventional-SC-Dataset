"""Issue #90 Copy：迁移旧 Tc/普通物性到统一记录表。"""

from alembic import op

revision = "issue90_copy_property_records"
down_revision = "issue90_expand_modular_property_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 数据复制依赖可回滚/可重放的应用脚本，避免在 Alembic DDL 事务中
    # 混入大批量 JSON 转换。部署时显式运行 migrate_issue90_properties。
    return None


def downgrade() -> None:
    return None

