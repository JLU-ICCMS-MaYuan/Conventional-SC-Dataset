"""rename papers.rationale to research_motivation, preserving data

字段承载的内容发生变更，不只是改名：

- 旧 `rationale`：本应是 AI 的分类判据，但 `SUMMARY_SYSTEM_PROMPT` 对该字段没有
  任何内容说明，模型在无指引下自行发挥。
- 新 `research_motivation`：作者开展该研究的驱动力，依据引言与背景段落归纳，
  按 1. 2. 3. 分条，不超过 500 字。

**保留存量数据**：执行前核查 papers 表唯一有值的一行（id=9）内容为分条式研究动因
（443 字，判定低温电阻三种对立理论、选汞的纯度理由），已符合新字段契约，丢弃它没有
道理。故用 UPDATE 搬迁后再删旧列，而非直接 drop。

若某些行的旧值仍是旧语义，人工在校对页修正即可——保留可修正，删除不可恢复。

Revision ID: 20260831_0066
Revises: 20260831_0065
Create Date: 2026-08-31 16:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = '20260831_0066'
down_revision = '20260831_0065'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('papers', sa.Column('research_motivation', sa.Text(), nullable=True))
    # 先搬数据再删列，顺序颠倒会丢失内容
    op.execute('UPDATE papers SET research_motivation = rationale WHERE rationale IS NOT NULL')
    op.drop_column('papers', 'rationale')


def downgrade():
    op.add_column('papers', sa.Column('rationale', sa.Text(), nullable=True))
    op.execute('UPDATE papers SET rationale = research_motivation WHERE research_motivation IS NOT NULL')
    op.drop_column('papers', 'research_motivation')
