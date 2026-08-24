"""add account identity, applications and governance

Revision ID: 20260824_0009
Revises: 20260821_0008
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0009"
down_revision = "20260821_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_key", sa.String(500), nullable=True))
    op.add_column("users", sa.Column("orcid", sa.String(19), nullable=True))
    op.add_column("users", sa.Column("research_interests", sa.JSON(), nullable=True))
    op.add_column(
        "users",
        sa.Column("session_version", sa.BigInteger(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("account_status", sa.String(20), nullable=False, server_default="active"),
    )
    op.create_unique_constraint("uq_users_orcid", "users", ["orcid"])
    op.create_check_constraint(
        "ck_users_account_status",
        "users",
        "account_status IN ('active', 'banned', 'deactivated')",
    )

    op.create_table(
        "profile_change_audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=False),
        sa.Column("field_name", sa.String(32), nullable=False),
        sa.Column("old_value", sa.Text(), nullable=True),
        sa.Column("new_value", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.CheckConstraint(
            "field_name IN ('real_name', 'affiliation')",
            name="ck_profile_audit_field",
        ),
    )
    op.create_index(
        "ix_profile_audit_target_time",
        "profile_change_audit_events",
        ["target_user_id", "created_at"],
    )

    op.create_table(
        "admin_applications",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("real_name_snapshot", sa.String(100), nullable=False),
        sa.Column("affiliation_snapshot", sa.String(255), nullable=False),
        sa.Column("orcid_snapshot", sa.String(19), nullable=True),
        sa.Column("research_interests_snapshot", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("pending_guard", sa.Boolean(), nullable=True, server_default="1"),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("withdrawn_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("user_id", "pending_guard", name="uq_admin_application_pending"),
        sa.CheckConstraint(
            "status IN ('pending', 'withdrawn', 'approved', 'rejected')",
            name="ck_admin_application_status",
        ),
    )
    op.create_index(
        "ix_admin_applications_status_time",
        "admin_applications",
        ["status", "submitted_at"],
    )

    op.create_table(
        "user_governance_audit_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("old_role", sa.String(50), nullable=True),
        sa.Column("new_role", sa.String(50), nullable=True),
        sa.Column("old_status", sa.String(20), nullable=True),
        sa.Column("new_status", sa.String(20), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="RESTRICT"),
    )
    op.create_index(
        "ix_governance_target_time",
        "user_governance_audit_events",
        ["target_user_id", "created_at"],
    )

    bind = op.get_bind()
    bind.execute(sa.text("""
        INSERT INTO admin_applications
            (user_id, real_name_snapshot, affiliation_snapshot, status, pending_guard, submitted_at)
        SELECT id, COALESCE(real_name, ''), COALESCE(affiliation, ''), 'pending', 1, created_at
        FROM users
        WHERE role = 'admin' AND is_approved = 0
    """))
    bind.execute(sa.text("""
        UPDATE users
        SET role = CASE WHEN role = 'admin' AND is_approved = 0 THEN 'user' ELSE role END,
            is_approved = 1,
            is_email_verified = 1,
            account_status = 'active'
    """))


def downgrade() -> None:
    op.drop_table("user_governance_audit_events")
    op.drop_table("admin_applications")
    op.drop_table("profile_change_audit_events")
    op.drop_constraint("ck_users_account_status", "users", type_="check")
    op.drop_constraint("uq_users_orcid", "users", type_="unique")
    op.drop_column("users", "account_status")
    op.drop_column("users", "session_version")
    op.drop_column("users", "research_interests")
    op.drop_column("users", "orcid")
    op.drop_column("users", "avatar_key")
