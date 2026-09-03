"""evolve paper review events into immutable paper history

Revision ID: paper_history_events
Revises: experimental_tc_context
Create Date: 2026-09-03
"""

from alembic import op
import sqlalchemy as sa


revision = "paper_history_events"
down_revision = "experimental_tc_context"
branch_labels = None
depends_on = None


_TABLE = "paper_history_events"


def upgrade() -> None:
    op.rename_table("paper_review_events", _TABLE)

    # 旧外键仍引用 paper_id。先建立新表名下的同等前缀索引，避免 MySQL
    # 在移除旧索引的瞬间拒绝保留该外键。
    op.create_index(
        "ix_paper_history_events_paper_revision",
        _TABLE,
        ["paper_id", "paper_revision"],
    )

    # 旧约束和索引依赖审核专用列名，先移除再演进字段。
    op.drop_constraint("ck_paper_review_events_status", _TABLE, type_="check")
    op.drop_constraint("ck_paper_review_events_revision", _TABLE, type_="check")
    op.drop_constraint("uq_paper_review_events_request_id", _TABLE, type_="unique")
    op.drop_index("ix_paper_review_events_paper_time", table_name=_TABLE)
    op.drop_index("ix_paper_review_events_paper_revision", table_name=_TABLE)
    op.drop_index("ix_paper_review_events_reviewer_time", table_name=_TABLE)

    op.alter_column(
        _TABLE,
        "reviewer_user_id",
        new_column_name="actor_user_id",
        existing_type=sa.Integer(),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        _TABLE,
        "status",
        new_column_name="review_status",
        existing_type=sa.String(length=50),
        existing_nullable=False,
        nullable=True,
    )
    op.alter_column(
        _TABLE,
        "reviewed_at",
        new_column_name="occurred_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        _TABLE,
        "request_id",
        new_column_name="operation_id",
        existing_type=sa.String(length=64),
        existing_nullable=True,
    )
    op.drop_column(_TABLE, "source")
    op.add_column(_TABLE, sa.Column("event_type", sa.String(length=20), nullable=False, server_default="reviewed"))
    op.add_column(_TABLE, sa.Column("actor_username_snapshot", sa.String(length=32), nullable=True))
    op.alter_column(_TABLE, "event_type", server_default=None)

    # 旧审核事件用迁移执行时仍可读到的用户名做快照；不存在的用户保留空值。
    op.execute(sa.text("""
        UPDATE paper_history_events event
        LEFT JOIN users actor ON actor.id = event.actor_user_id
        SET event.actor_username_snapshot = actor.username
        WHERE event.actor_user_id IS NOT NULL
    """))

    op.create_unique_constraint("uq_paper_history_events_operation_id", _TABLE, ["operation_id"])
    op.create_check_constraint(
        "ck_paper_history_events_revision",
        _TABLE,
        "paper_revision >= 1",
    )
    op.create_check_constraint(
        "ck_paper_history_events_shape",
        _TABLE,
        """
        (event_type = 'reviewed' AND review_status IN ('approved', 'rejected', 'pending'))
        OR
        (event_type IN ('uploaded', 'modified') AND review_status IS NULL AND review_comment IS NULL)
        """,
    )
    op.create_index(
        "ix_paper_history_events_paper_time",
        _TABLE,
        ["paper_id", "occurred_at", "id"],
    )
    op.create_index(
        "ix_paper_history_events_actor_time",
        _TABLE,
        ["actor_user_id", "occurred_at", "id"],
    )

    # 仅用确切的创建时间和上传者回填上传事件；不从 updated_at 编造修改历史。
    op.execute(sa.text("""
        INSERT INTO paper_history_events
            (paper_id, paper_revision, event_type, actor_user_id,
             actor_username_snapshot, review_status, review_comment,
             occurred_at, operation_id, classification_snapshot)
        SELECT
            papers.id,
            1,
            'uploaded',
            papers.uploaded_by_user_id,
            uploader.username,
            NULL,
            NULL,
            papers.created_at,
            NULL,
            NULL
        FROM papers
        LEFT JOIN users uploader ON uploader.id = papers.uploaded_by_user_id
    """))


def downgrade() -> None:
    # 回退到审核专用模型时，上传和修改事件没有可表示的旧字段，只保留审核记录。
    op.execute(sa.text("DELETE FROM paper_history_events WHERE event_type <> 'reviewed'"))

    # 旧 paper_id 外键需要一个以 paper_id 开头的索引。先恢复旧索引，再删除
    # 新索引，避免 MySQL 在回退时拒绝删除外键依赖的索引。
    op.create_index(
        "ix_paper_review_events_paper_revision",
        _TABLE,
        ["paper_id", "paper_revision", "occurred_at"],
    )
    op.drop_constraint("ck_paper_history_events_shape", _TABLE, type_="check")
    op.drop_constraint("ck_paper_history_events_revision", _TABLE, type_="check")
    op.drop_constraint("uq_paper_history_events_operation_id", _TABLE, type_="unique")
    op.drop_index("ix_paper_history_events_paper_time", table_name=_TABLE)
    op.drop_index("ix_paper_history_events_actor_time", table_name=_TABLE)
    op.drop_index("ix_paper_history_events_paper_revision", table_name=_TABLE)

    op.drop_column(_TABLE, "event_type")
    op.drop_column(_TABLE, "actor_username_snapshot")
    op.alter_column(
        _TABLE,
        "actor_user_id",
        new_column_name="reviewer_user_id",
        existing_type=sa.Integer(),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        _TABLE,
        "review_status",
        new_column_name="status",
        existing_type=sa.String(length=50),
        existing_nullable=True,
        nullable=False,
    )
    op.alter_column(
        _TABLE,
        "occurred_at",
        new_column_name="reviewed_at",
        existing_type=sa.DateTime(),
        existing_nullable=False,
        existing_server_default=sa.text("CURRENT_TIMESTAMP"),
    )
    op.alter_column(
        _TABLE,
        "operation_id",
        new_column_name="request_id",
        existing_type=sa.String(length=64),
        existing_nullable=True,
    )
    op.add_column(_TABLE, sa.Column("source", sa.String(length=20), nullable=False, server_default="single"))
    op.alter_column(_TABLE, "source", server_default=None)

    op.create_unique_constraint("uq_paper_review_events_request_id", _TABLE, ["request_id"])
    op.create_check_constraint(
        "ck_paper_review_events_status",
        _TABLE,
        "status IN ('approved', 'rejected', 'pending')",
    )
    op.create_check_constraint("ck_paper_review_events_revision", _TABLE, "paper_revision >= 1")
    op.create_index(
        "ix_paper_review_events_paper_time",
        _TABLE,
        ["paper_id", "reviewed_at"],
    )
    op.create_index(
        "ix_paper_review_events_reviewer_time",
        _TABLE,
        ["reviewer_user_id", "reviewed_at", "id"],
    )
    op.rename_table(_TABLE, "paper_review_events")
