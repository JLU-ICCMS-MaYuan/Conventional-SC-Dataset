"""fill canonical English name for the elemental superconductor family

Revision ID: fill_elemental_name_en
Revises: revision_cascade_chain
Create Date: 2026-09-02

Issue #76（FR-024、SC-010）：为既有自建家族「单质超导体」补齐规范英文名。

背景：material_families.name_en 列在自建家族创建时留空（goserver 的
resolveMaterialFamily 不写 name_en），Issue #74 据此设计「英文缺失回退中文名」。
#76 的审核编辑弹窗需要英文界面显示规范英文名，因此对既有数据补齐一次：

  name_en: '' -> 'Elemental superconductor'  （按 name_zh = '单质超导体' 定位）

code 列是生成的 custom_* 哈希（不稳定），不能作为定位依据；name_zh 有唯一约束。
迁移幂等：库中不存在该家族的安装执行 0 行更新，不受影响。只补数据、不改 Schema、
不改创建路径——新建自建家族仍留空 name_en，回退语义不变。

详见 docs/specs/76-review-scientific-data-editing/data-model.md（家族英文名补齐）。
"""
from alembic import op
from sqlalchemy import text

revision = 'fill_elemental_name_en'
down_revision = 'revision_cascade_chain'
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        text(
            "UPDATE material_families "
            "SET name_en = 'Elemental superconductor' "
            "WHERE name_zh = '单质超导体' AND (name_en IS NULL OR name_en = '')"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(
        text(
            "UPDATE material_families "
            "SET name_en = '' "
            "WHERE name_zh = '单质超导体' AND name_en = 'Elemental superconductor'"
        )
    )
