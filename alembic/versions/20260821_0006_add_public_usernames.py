"""add public usernames and immutable rename audit

Revision ID: 20260821_0006
Revises: 20260820_0005
Create Date: 2026-08-21
"""

import secrets
import string

from alembic import op
import sqlalchemy as sa


revision = "20260821_0006"
down_revision = "20260820_0005"
branch_labels = None
depends_on = None


_RANDOM_ALPHABET = string.ascii_lowercase + string.digits


def _historical_username() -> str:
    return "sc_" + "".join(secrets.choice(_RANDOM_ALPHABET) for _ in range(12))


def upgrade() -> None:
    username_type = sa.String(length=32, collation="ascii_bin")
    op.add_column("users", sa.Column("username", username_type, nullable=True))
    op.add_column(
        "users",
        sa.Column(
            "username_change_allowed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )

    bind = op.get_bind()
    used = {
        row[0]
        for row in bind.execute(
            sa.text("SELECT username FROM users WHERE username IS NOT NULL")
        )
    }
    user_ids = [
        row[0]
        for row in bind.execute(sa.text("SELECT id FROM users WHERE username IS NULL"))
    ]
    for user_id in user_ids:
        candidate = _historical_username()
        while candidate in used:
            candidate = _historical_username()
        used.add(candidate)
        bind.execute(
            sa.text(
                "UPDATE users SET username = :username, "
                "username_change_allowed = 1 WHERE id = :user_id"
            ),
            {"username": candidate, "user_id": user_id},
        )

    op.alter_column("users", "username", existing_type=username_type, nullable=False)
    op.create_index("uq_users_username", "users", ["username"], unique=True)

    op.create_table(
        "username_change_audit_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "target_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "changed_by_user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("old_username", username_type, nullable=False),
        sa.Column("new_username", username_type, nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_username_audit_target_time",
        "username_change_audit_events",
        ["target_user_id", "created_at"],
    )
    op.create_index(
        "ix_username_audit_actor_time",
        "username_change_audit_events",
        ["changed_by_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_username_audit_actor_time", table_name="username_change_audit_events"
    )
    op.drop_index(
        "ix_username_audit_target_time", table_name="username_change_audit_events"
    )
    op.drop_table("username_change_audit_events")
    op.drop_index("uq_users_username", table_name="users")
    op.drop_column("users", "username_change_allowed")
    op.drop_column("users", "username")
