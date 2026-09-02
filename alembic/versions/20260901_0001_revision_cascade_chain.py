"""revision cascade chain for paper lineage tables

Revision ID: revision_cascade_chain
Revises: add_kg_title
Create Date: 2026-09-01 18:50:00

Issue #76：把论文血缘链改为单向外键级联，使升版（papers.content_revision 递增）
由 MySQL 在单一事务内级联更新 paper_files / paper_chunks / paper_evidences /
material_states 的 paper_revision。

背景：5 条复合外键全部是 ON UPDATE NO ACTION（立即检查的 RESTRICT），
任何 content_revision 更新都会被拒绝——这是「手工逐表迁移版本号」方案不可行的根因。
本迁移把四条外键改为 ON UPDATE CASCADE，并删除 paper_chunks / paper_evidences
到 papers 的两条冗余直连外键（MySQL 不允许多条 CASCADE 作用于同一子表的同一列，
实测冲突在建表期不报错、仅在级联更新时抛 1452）。ON DELETE 全部保持 RESTRICT。

详见 docs/specs/76-review-scientific-data-editing/data-model.md（外键迁移）。
"""
from alembic import op
from sqlalchemy import inspect, text

revision = 'revision_cascade_chain'
down_revision = 'add_kg_title'
branch_labels = None
depends_on = None


def _recreate_fk(
    name: str,
    table: str,
    ref_table: str,
    local_cols: list[str],
    remote_cols: list[str],
    *,
    onupdate: str,
) -> None:
    """删除并重建一条外键，保留 ON DELETE RESTRICT，按需指定 ON UPDATE 规则。"""
    op.drop_constraint(name, table, type_="foreignkey")
    op.create_foreign_key(
        name,
        table,
        ref_table,
        local_cols,
        remote_cols,
        ondelete="RESTRICT",
        onupdate=onupdate,
    )


def _reject_bumped_papers() -> None:
    """downgrade 守卫：存在 content_revision > 1 的论文时禁止回退。

    恢复 RESTRICT 后这些论文的血缘数据虽一致，但后续无法再升版；
    静默回退会让运行库进入无法继续升版的状态，必须显式报错。
    """
    connection = op.get_bind()
    bumped = connection.execute(
        text("SELECT COUNT(*) FROM papers WHERE content_revision > 1")
    ).scalar()
    if bumped:
        raise RuntimeError(
            f"存在 {bumped} 篇 content_revision > 1 的论文；"
            "回退会恢复 ON UPDATE RESTRICT，使这些论文无法再升版，已拒绝执行。"
        )


def upgrade() -> None:
    # 四条外键改为 ON UPDATE CASCADE（ON DELETE 保持 RESTRICT）
    _recreate_fk(
        "fk_paper_files_paper_revision",
        "paper_files", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        onupdate="CASCADE",
    )
    _recreate_fk(
        "fk_paper_chunks_file_revision",
        "paper_chunks", "paper_files",
        ["paper_file_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        onupdate="CASCADE",
    )
    _recreate_fk(
        "fk_paper_evidences_chunk_revision",
        "paper_evidences", "paper_chunks",
        ["paper_chunk_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        onupdate="CASCADE",
    )
    _recreate_fk(
        "fk_material_states_paper_revision",
        "material_states", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        onupdate="CASCADE",
    )

    # 删除两条冗余直连外键：paper_chunks / paper_evidences 经文件链到达 papers，
    # 完整性由链条传递（见 data-model.md 的实测验证）。
    op.drop_constraint("fk_paper_chunks_paper_revision", "paper_chunks", type_="foreignkey")
    op.drop_constraint("fk_paper_evidences_paper_revision", "paper_evidences", type_="foreignkey")


def downgrade() -> None:
    _reject_bumped_papers()

    # 先重建两条直连外键（NO ACTION / RESTRICT，与多条 CASCADE 不冲突），
    # 再把四条 CASCADE 改回 NO ACTION。
    op.create_foreign_key(
        "fk_paper_chunks_paper_revision",
        "paper_chunks", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_paper_evidences_paper_revision",
        "paper_evidences", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        ondelete="RESTRICT",
    )
    _recreate_fk(
        "fk_paper_files_paper_revision",
        "paper_files", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        onupdate="NO ACTION",
    )
    _recreate_fk(
        "fk_paper_chunks_file_revision",
        "paper_chunks", "paper_files",
        ["paper_file_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        onupdate="NO ACTION",
    )
    _recreate_fk(
        "fk_paper_evidences_chunk_revision",
        "paper_evidences", "paper_chunks",
        ["paper_chunk_id", "paper_id", "paper_revision"],
        ["id", "paper_id", "paper_revision"],
        onupdate="NO ACTION",
    )
    _recreate_fk(
        "fk_material_states_paper_revision",
        "material_states", "papers",
        ["paper_id", "paper_revision"], ["id", "content_revision"],
        onupdate="NO ACTION",
    )
