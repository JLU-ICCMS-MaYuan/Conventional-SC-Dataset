"""add material-state classification catalogs and governance

Revision ID: 20260825_0012
Revises: 20260824_0011
Create Date: 2026-08-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260825_0012"
down_revision = "20260824_0011"
branch_labels = None
depends_on = None


MATERIAL_FAMILIES = [
    (1, "hydrogen_based", "氢基超导体", "Hydrogen-based superconductor", "氢基超导体"),
    (2, "copper_based", "铜基超导体", "Copper-based superconductor", "铜基超导体"),
    (3, "iron_based", "铁基超导体", "Iron-based superconductor", "铁基超导体"),
    (4, "nickel_based", "镍基超导体", "Nickel-based superconductor", "镍基超导体"),
    (
        5,
        "inorganic_bcn_based",
        "无机硼碳氮基超导体",
        "Inorganic boron-carbon-nitrogen-based superconductor",
        "无机硼碳氮基超导体",
    ),
    (6, "organic", "有机超导体", "Organic superconductor", "有机超导体"),
    (7, "heavy_fermion", "重费米子超导体", "Heavy-fermion superconductor", "重费米子超导体"),
]

MATERIAL_ALIASES = [
    (1, 1, "hydrogen_based", "hydrogen based", "code"),
    (2, 1, "Hydrogen-based superconductor", "hydrogen based superconductor", "en"),
    (3, 1, "hydride", "hydride", "en"),
    (4, 1, "氢化物", "氢化物", "zh"),
    (5, 1, "高压氢化物", "高压氢化物", "zh"),
    (6, 1, "hydrogen-rich superconductor", "hydrogen rich superconductor", "en"),
    (7, 2, "copper_based", "copper based", "code"),
    (8, 2, "Copper-based superconductor", "copper based superconductor", "en"),
    (9, 2, "cuprate", "cuprate", "en"),
    (10, 2, "铜氧化物超导体", "铜氧化物超导体", "zh"),
    (11, 2, "铜基", "铜基", "zh"),
    (12, 3, "iron_based", "iron based", "code"),
    (13, 3, "Iron-based superconductor", "iron based superconductor", "en"),
    (14, 3, "铁基", "铁基", "zh"),
    (15, 4, "nickel_based", "nickel based", "code"),
    (16, 4, "Nickel-based superconductor", "nickel based superconductor", "en"),
    (17, 4, "nickelate", "nickelate", "en"),
    (18, 4, "镍基", "镍基", "zh"),
    (19, 5, "inorganic_bcn_based", "inorganic bcn based", "code"),
    (20, 5, "无机硼碳氮基超导", "无机硼碳氮基超导", "zh"),
    (21, 6, "organic", "organic", "code"),
    (22, 6, "Organic superconductor", "organic superconductor", "en"),
    (23, 6, "有机超导", "有机超导", "zh"),
    (24, 7, "heavy_fermion", "heavy fermion", "code"),
    (25, 7, "Heavy-fermion superconductor", "heavy fermion superconductor", "en"),
    (26, 7, "重费米子超导", "重费米子超导", "zh"),
]


def upgrade() -> None:
    op.create_table(
        "material_families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_zh", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("merged_into_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("merged_into_id IS NULL OR merged_into_id <> id", name="ck_material_families_not_self_merged"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merged_into_id"], ["material_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_material_families_code"),
        sa.UniqueConstraint("name_zh", name="uq_material_families_name_zh"),
        sa.UniqueConstraint("normalized_name", name="uq_material_families_normalized_name"),
    )
    material_families = sa.table(
        "material_families",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name_zh", sa.String()),
        sa.column("name_en", sa.String()),
        sa.column("normalized_name", sa.String()),
    )
    op.bulk_insert(
        material_families,
        [
            {"id": item[0], "code": item[1], "name_zh": item[2], "name_en": item[3], "normalized_name": item[4]}
            for item in MATERIAL_FAMILIES
        ],
    )

    op.create_table(
        "material_family_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("material_family_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(160), nullable=False),
        sa.Column("normalized_alias", sa.String(160), nullable=False),
        sa.Column("language", sa.String(10), server_default="other", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("language IN ('zh', 'en', 'code', 'other')", name="ck_material_family_alias_language"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["material_family_id"], ["material_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias", name="uq_material_family_alias_normalized"),
    )
    op.create_index("ix_material_family_aliases_family", "material_family_aliases", ["material_family_id"])
    material_aliases = sa.table(
        "material_family_aliases",
        sa.column("id", sa.Integer()),
        sa.column("material_family_id", sa.Integer()),
        sa.column("alias", sa.String()),
        sa.column("normalized_alias", sa.String()),
        sa.column("language", sa.String()),
    )
    op.bulk_insert(
        material_aliases,
        [
            {"id": item[0], "material_family_id": item[1], "alias": item[2], "normalized_alias": item[3], "language": item[4]}
            for item in MATERIAL_ALIASES
        ],
    )

    op.create_table(
        "structure_families",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("name_zh", sa.String(100), nullable=False),
        sa.Column("name_en", sa.String(160), nullable=False),
        sa.Column("normalized_name", sa.String(160), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("merged_into_id", sa.Integer(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("merged_into_id IS NULL OR merged_into_id <> id", name="ck_structure_families_not_self_merged"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merged_into_id"], ["structure_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_structure_families_code"),
        sa.UniqueConstraint("name_zh", name="uq_structure_families_name_zh"),
        sa.UniqueConstraint("normalized_name", name="uq_structure_families_normalized_name"),
    )
    op.bulk_insert(
        sa.table(
            "structure_families",
            sa.column("id", sa.Integer()),
            sa.column("code", sa.String()),
            sa.column("name_zh", sa.String()),
            sa.column("name_en", sa.String()),
            sa.column("normalized_name", sa.String()),
        ),
        [{"id": 1, "code": "clathrate", "name_zh": "笼状结构", "name_en": "Clathrate structure", "normalized_name": "笼状结构"}],
    )
    op.create_table(
        "structure_family_aliases",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("structure_family_id", sa.Integer(), nullable=False),
        sa.Column("alias", sa.String(160), nullable=False),
        sa.Column("normalized_alias", sa.String(160), nullable=False),
        sa.Column("language", sa.String(10), server_default="other", nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("language IN ('zh', 'en', 'code', 'other')", name="ck_structure_family_alias_language"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["structure_family_id"], ["structure_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("normalized_alias", name="uq_structure_family_alias_normalized"),
    )
    op.create_index("ix_structure_family_aliases_family", "structure_family_aliases", ["structure_family_id"])
    op.bulk_insert(
        sa.table(
            "structure_family_aliases",
            sa.column("id", sa.Integer()),
            sa.column("structure_family_id", sa.Integer()),
            sa.column("alias", sa.String()),
            sa.column("normalized_alias", sa.String()),
            sa.column("language", sa.String()),
        ),
        [
            {"id": 1, "structure_family_id": 1, "alias": "clathrate", "normalized_alias": "clathrate", "language": "en"},
            {"id": 2, "structure_family_id": 1, "alias": "Clathrate structure", "normalized_alias": "clathrate structure", "language": "en"},
            {"id": 3, "structure_family_id": 1, "alias": "笼状", "normalized_alias": "笼状", "language": "zh"},
        ],
    )

    op.add_column("material_states", sa.Column("material_family_id", sa.Integer(), nullable=True))
    op.add_column("material_states", sa.Column("element_count", sa.SmallInteger(), nullable=True))
    op.add_column(
        "material_states",
        sa.Column("material_dimensionality", sa.String(32), server_default="unknown", nullable=False),
    )
    op.create_foreign_key(
        "fk_material_states_material_family",
        "material_states",
        "material_families",
        ["material_family_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_index("ix_material_states_material_family", "material_states", ["material_family_id"])
    op.create_check_constraint(
        "ck_material_states_element_count",
        "material_states",
        "element_count IS NULL OR element_count BETWEEN 1 AND 118",
    )
    op.create_check_constraint(
        "ck_material_states_dimensionality",
        "material_states",
        "material_dimensionality IN ('zero_dimensional', 'one_dimensional', 'two_dimensional', 'three_dimensional', 'quasi_one_dimensional', 'quasi_two_dimensional', 'unknown')",
    )

    op.create_table(
        "material_state_structure_families",
        sa.Column("material_state_id", sa.BigInteger(), nullable=False),
        sa.Column("structure_family_id", sa.Integer(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default="0", nullable=False),
        sa.Column(
            "primary_marker",
            sa.BigInteger(),
            sa.Computed("CASE WHEN is_primary = 1 THEN material_state_id ELSE NULL END", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["material_state_id"], ["material_states.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["structure_family_id"], ["structure_families.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("material_state_id", "structure_family_id"),
        sa.UniqueConstraint("primary_marker", name="uq_material_state_structure_primary"),
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
        sa.ForeignKeyConstraint(["material_state_id", "paper_id", "paper_revision"], ["material_states.id", "material_states.paper_id", "material_states.paper_revision"], name="fk_classification_evidences_state_revision", ondelete="CASCADE"),
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

    op.drop_column("papers", "referenced_materials")


def downgrade() -> None:
    op.add_column("papers", sa.Column("referenced_materials", sa.JSON(), nullable=True))
    op.drop_index("ix_classification_audits_entity_time", table_name="classification_audit_events")
    op.drop_table("classification_audit_events")
    op.drop_index("ix_classification_evidences_paper_revision", table_name="classification_evidences")
    op.drop_table("classification_evidences")
    op.drop_index("ix_classification_proposals_queue", table_name="classification_proposals")
    op.drop_index("ix_classification_proposals_state", table_name="classification_proposals")
    op.drop_table("classification_proposals")
    op.drop_table("material_state_structure_families")
    op.drop_constraint("ck_material_states_dimensionality", "material_states", type_="check")
    op.drop_constraint("ck_material_states_element_count", "material_states", type_="check")
    op.drop_index("ix_material_states_material_family", table_name="material_states")
    op.drop_constraint("fk_material_states_material_family", "material_states", type_="foreignkey")
    op.drop_column("material_states", "material_dimensionality")
    op.drop_column("material_states", "element_count")
    op.drop_column("material_states", "material_family_id")
    op.drop_index("ix_structure_family_aliases_family", table_name="structure_family_aliases")
    op.drop_table("structure_family_aliases")
    op.drop_table("structure_families")
    op.drop_index("ix_material_family_aliases_family", table_name="material_family_aliases")
    op.drop_table("material_family_aliases")
    op.drop_table("material_families")
