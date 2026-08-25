"""Simplify classification governance into the paper review transaction.

Revision ID: 20260825_0013
Revises: 20260825_0012
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0013"
down_revision = "20260825_0012"
branch_labels = None
depends_on = None


def _drop_foreign_keys_for_column(table_name: str, column_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if column_name in (foreign_key.get("constrained_columns") or []):
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")


def upgrade() -> None:
    op.add_column(
        "paper_review_events",
        sa.Column("classification_snapshot", sa.JSON(), nullable=True),
    )

    op.drop_table("classification_evidences")
    op.drop_table("classification_proposals")
    op.drop_table("classification_audit_events")

    for table_name in ("material_families", "structure_families"):
        _drop_foreign_keys_for_column(table_name, "merged_into_id")
        op.drop_column(table_name, "merged_into_id")
        op.drop_column(table_name, "is_active")
        op.alter_column(
            table_name,
            "name_en",
            existing_type=sa.String(length=160),
            nullable=True,
        )


def downgrade() -> None:
    for table_name in ("material_families", "structure_families"):
        op.execute(
            sa.text(
                f"UPDATE {table_name} SET name_en = name_zh "
                "WHERE name_en IS NULL OR name_en = ''"
            )
        )
        op.alter_column(
            table_name,
            "name_en",
            existing_type=sa.String(length=160),
            nullable=False,
        )
        op.add_column(
            table_name,
            sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        )
        op.add_column(table_name, sa.Column("merged_into_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            f"fk_{table_name}_merged_into",
            table_name,
            table_name,
            ["merged_into_id"],
            ["id"],
            ondelete="RESTRICT",
        )

    op.create_table(
        "classification_proposals",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("raw_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(20), server_default="proposed", nullable=False),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("resolution_kind", sa.String(32), nullable=True),
        sa.Column("material_family_id", sa.Integer(), nullable=True),
        sa.Column("structure_family_id", sa.Integer(), nullable=True),
        sa.Column("proposed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("dimension IN ('material_family', 'structure_family')", name="ck_classification_proposals_dimension"),
        sa.CheckConstraint("status IN ('proposed', 'under_review', 'resolved', 'rejected')", name="ck_classification_proposals_status"),
        sa.CheckConstraint("source_kind IN ('ai', 'user', 'admin', 'migration')", name="ck_classification_proposals_source"),
        sa.CheckConstraint("resolution_kind IS NULL OR resolution_kind IN ('mapped_existing', 'alias_created', 'formal_created', 'rejected')", name="ck_classification_proposals_resolution"),
        sa.ForeignKeyConstraint(["material_family_id"], ["material_families.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_state_id"], ["material_states.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["proposed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["structure_family_id"], ["structure_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classification_proposals_state", "classification_proposals", ["material_state_id"])
    op.create_index("ix_classification_proposals_queue", "classification_proposals", ["status", "dimension", "created_at"])

    op.create_table(
        "classification_evidences",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("paper_id", sa.Integer(), nullable=False),
        sa.Column("paper_revision", sa.Integer(), nullable=False),
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("material_family_id", sa.Integer(), nullable=True),
        sa.Column("structure_family_id", sa.Integer(), nullable=True),
        sa.Column("proposal_id", sa.BigInteger(), nullable=True),
        sa.Column("source_kind", sa.String(20), nullable=False),
        sa.Column("scope", sa.String(20), server_default="current_paper", nullable=False),
        sa.Column("raw_value", sa.String(255), nullable=True),
        sa.Column("section", sa.String(500), nullable=True),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("dimension IN ('material_family', 'structure_family', 'element_count', 'material_dimensionality')", name="ck_classification_evidences_dimension"),
        sa.CheckConstraint("source_kind IN ('reported', 'derived', 'reviewed')", name="ck_classification_evidences_source"),
        sa.CheckConstraint("scope IN ('current_paper', 'referenced_work')", name="ck_classification_evidences_scope"),
        sa.ForeignKeyConstraint(["material_family_id"], ["material_families.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_classification_evidences_state_revision",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["proposal_id"], ["classification_proposals.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["structure_family_id"], ["structure_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classification_evidences_paper_revision", "classification_evidences", ["paper_id", "paper_revision"])

    op.create_table(
        "classification_audit_events",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=False),
        sa.Column("dimension", sa.String(32), nullable=False),
        sa.Column("entity_kind", sa.String(20), nullable=False),
        sa.Column("entity_id", sa.BigInteger(), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=True),
        sa.Column("after_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("dimension IN ('material_family', 'structure_family')", name="ck_classification_audits_dimension"),
        sa.CheckConstraint("entity_kind IN ('term', 'alias', 'proposal')", name="ck_classification_audits_entity_kind"),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_classification_audits_entity_time", "classification_audit_events", ["dimension", "entity_kind", "entity_id", "created_at"])

    op.drop_column("paper_review_events", "classification_snapshot")
