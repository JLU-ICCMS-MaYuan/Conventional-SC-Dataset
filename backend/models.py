"""SQLAlchemy models for the fresh MySQL target schema."""

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Computed,
    DateTime,
    Float,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import DeclarativeBase, relationship, synonym
from sqlalchemy.sql import func

from backend.database import Base


USERNAME_TYPE = String(32).with_variant(
    mysql.VARCHAR(32, collation="ascii_bin"),
    "mysql",
)
LONG_TEXT = Text().with_variant(mysql.LONGTEXT(), "mysql")


class PeriodicTableElement(Base):
    __tablename__ = "periodic_table_elements"
    __table_args__ = (
        UniqueConstraint(
            "atomic_number",
            name="uq_periodic_table_elements_atomic_number",
        ),
        UniqueConstraint(
            "symbol",
            name="uq_periodic_table_elements_symbol",
        ),
        Index(
            "ix_periodic_table_elements_atomic_number",
            "atomic_number",
        ),
        Index("ix_periodic_table_elements_symbol", "symbol"),
    )

    id = Column(Integer, primary_key=True)
    atomic_number = Column(Integer, nullable=False)
    symbol = Column(String(8), nullable=False)
    english_name = Column(String(100), nullable=False)
    chinese_name = Column(String(100))
    atomic_mass = Column(Float)
    period_number = Column(Integer)
    group_number = Column(Integer)
    category = Column(String(100))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())


class ChemicalSystem(Base):
    __tablename__ = "chemical_systems"
    __table_args__ = (
        UniqueConstraint(
            "system_key",
            name="uq_chemical_systems_system_key",
        ),
        Index("ix_chemical_systems_system_key", "system_key"),
    )

    id = Column(Integer, primary_key=True)
    system_key = Column(String(255), nullable=False)
    elements_list = Column(JSON, nullable=False)
    element_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    superconductors = relationship("Superconductor", back_populates="chemical_system")


class Superconductor(Base):
    __tablename__ = "superconductors"
    __table_args__ = (
        UniqueConstraint(
            "composition_key",
            name="uq_superconductors_composition_key",
        ),
        UniqueConstraint(
            "formula_normalized",
            name="uq_superconductors_formula_normalized",
        ),
        Index(
            "ix_superconductors_formula_normalized",
            "formula_normalized",
        ),
        Index(
            "ix_superconductors_isotope_signature",
            "isotope_signature",
        ),
    )

    id = Column(Integer, primary_key=True)
    chemical_system_id = Column(
        Integer,
        ForeignKey("chemical_systems.id"),
        nullable=False,
        index=True,
    )
    chemical_formula = Column(String(255), nullable=False)
    formula_normalized = Column(String(255), nullable=False)
    composition_key = Column(String(255), nullable=False)
    isotope_signature = Column(String(255))
    display_name = Column(String(255), nullable=False)
    elements_list = Column(JSON, nullable=False)
    composition = Column(JSON, nullable=False)
    element_ratio = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    chemical_system = relationship("ChemicalSystem", back_populates="superconductors")
    material_states = relationship("MaterialState", back_populates="superconductor")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        Index("ix_users_email", "email"),
        Index("uq_users_username", "username", unique=True),
    )

    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False)
    username = Column(USERNAME_TYPE, nullable=False)
    username_change_allowed = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(100), nullable=False)
    affiliation = Column(String(255))
    avatar_key = Column(String(500))
    orcid = Column(String(19), unique=True)
    research_interests = Column(JSON)
    role = Column(String(50), default="user", nullable=False, index=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    session_version = Column(BigInteger, default=0, nullable=False)
    account_status = Column(String(20), default="active", nullable=False, index=True)
    verification_code = Column(String(16))
    verification_expires = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    uploaded_papers = relationship(
        "Paper",
        back_populates="uploaded_by_user",
        foreign_keys="Paper.uploaded_by_user_id",
    )
    reviewed_papers = relationship(
        "Paper",
        back_populates="reviewed_by_user",
        foreign_keys="Paper.reviewed_by_user_id",
    )
    review_events = relationship("PaperReviewEvent", back_populates="reviewer")
    username_changes_received = relationship(
        "UsernameChangeAuditEvent",
        foreign_keys="UsernameChangeAuditEvent.target_user_id",
        back_populates="target_user",
    )
    username_changes_made = relationship(
        "UsernameChangeAuditEvent",
        foreign_keys="UsernameChangeAuditEvent.changed_by_user_id",
        back_populates="changed_by_user",
    )


class UsernameChangeAuditEvent(Base):
    """Append-only record of a superadmin username correction."""

    __tablename__ = "username_change_audit_events"
    __table_args__ = (
        Index(
            "ix_username_audit_target_time",
            "target_user_id",
            "created_at",
        ),
        Index(
            "ix_username_audit_actor_time",
            "changed_by_user_id",
            "created_at",
        ),
    )

    id = Column(Integer, primary_key=True)
    target_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    changed_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    old_username = Column(USERNAME_TYPE, nullable=False)
    new_username = Column(USERNAME_TYPE, nullable=False)
    reason = Column(String(500), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    target_user = relationship(
        "User",
        foreign_keys=[target_user_id],
        back_populates="username_changes_received",
    )
    changed_by_user = relationship(
        "User",
        foreign_keys=[changed_by_user_id],
        back_populates="username_changes_made",
    )


class ProfileChangeAuditEvent(Base):
    __tablename__ = "profile_change_audit_events"

    id = Column(BigInteger, primary_key=True)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    field_name = Column(String(32), nullable=False)
    old_value = Column(Text)
    new_value = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AdminApplication(Base):
    __tablename__ = "admin_applications"

    id = Column(BigInteger, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    real_name_snapshot = Column(String(100), nullable=False)
    affiliation_snapshot = Column(String(255), nullable=False)
    orcid_snapshot = Column(String(19))
    research_interests_snapshot = Column(JSON)
    status = Column(String(20), nullable=False, default="pending")
    pending_guard = Column(Boolean)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    rejection_reason = Column(Text)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    withdrawn_at = Column(DateTime(timezone=True))
    reviewed_at = Column(DateTime(timezone=True))


class UserGovernanceAuditEvent(Base):
    __tablename__ = "user_governance_audit_events"

    id = Column(BigInteger, primary_key=True)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    target_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    event_type = Column(String(32), nullable=False)
    old_role = Column(String(50))
    new_role = Column(String(50))
    old_status = Column(String(20))
    new_status = Column(String(20))
    reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (
        CheckConstraint(
            """
            content_revision >= 1
            AND (
                (review_status = 'approved' AND approved_revision = content_revision)
                OR
                (
                    review_status IN ('pending', 'rejected')
                    AND approved_revision IS NULL
                )
            )
            """,
            name="ck_papers_review_revision",
        ),
        UniqueConstraint(
            "id",
            "content_revision",
            name="uq_papers_id_content_revision",
        ),
        UniqueConstraint("doi", name="uq_papers_doi"),
        Index("ix_papers_doi", "doi"),
        Index(
            "ix_papers_public_revision",
            "review_status",
            "approved_revision",
            "content_revision",
        ),
    )

    id = Column(Integer, primary_key=True)
    doi = Column(String(255), nullable=True)
    title = Column(Text, nullable=True)
    journal = Column(String(255))
    volume = Column(String(100))
    pages = Column(String(100))
    year = Column(Integer, index=True)
    abstract = Column(Text)
    authors = Column(JSON, nullable=True)
    uploaded_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    reviewed_by_user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    review_status = Column(
        String(50),
        default="pending",
        server_default="pending",
        nullable=False,
        index=True,
    )
    content_revision = Column(
        Integer,
        default=1,
        server_default="1",
        nullable=False,
    )
    approved_revision = Column(Integer, nullable=True)
    reviewed_at = Column(DateTime(timezone=True))
    review_comment = Column(Text)
    admin_internal_note = Column(Text)
    upload_task_id = Column(String(32), unique=True, index=True, nullable=True)
    summary = Column(Text)
    paper_type = Column(String(20))
    theoretical_subtype = Column(String(20), nullable=True)
    keywords_tags = Column(Text)
    methodology = Column(Text)
    key_finding = Column(Text)
    rationale = Column(Text)
    research_materials = Column(JSON)
    material_relations = Column(JSON)
    builds_on = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    uploaded_by_user = relationship(
        "User",
        back_populates="uploaded_papers",
        foreign_keys=[uploaded_by_user_id],
    )
    reviewed_by_user = relationship(
        "User",
        back_populates="reviewed_papers",
        foreign_keys=[reviewed_by_user_id],
    )
    files = relationship("PaperFile", back_populates="paper")
    chunks = relationship(
        "PaperChunk",
        back_populates="paper",
        overlaps="chunks,paper_file",
    )
    evidences = relationship(
        "PaperEvidence",
        back_populates="paper",
        overlaps="evidences,paper_chunk",
    )
    review_events = relationship("PaperReviewEvent", back_populates="paper")
    material_states = relationship("MaterialState", back_populates="paper")


class PaperFile(Base):
    """A current-revision paper body, supplement, or attachment."""

    __tablename__ = "paper_files"
    __table_args__ = (
        CheckConstraint(
            "role IN ('main', 'supplementary', 'attachment')",
            name="ck_paper_files_role",
        ),
        CheckConstraint("size >= 0", name="ck_paper_files_size"),
        CheckConstraint("sort_order >= 0", name="ck_paper_files_sort_order"),
        UniqueConstraint(
            "paper_id",
            "sort_order",
            name="uq_paper_files_order",
        ),
        UniqueConstraint(
            "paper_id",
            "stored_path",
            name="uq_paper_files_path",
        ),
        UniqueConstraint(
            "paper_id",
            "main_marker",
            name="uq_paper_files_main",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_paper_files_identity_revision",
        ),
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_files_paper_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_paper_files_paper_revision",
            "paper_id",
            "paper_revision",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, default=1, server_default="1", nullable=False)
    role = Column(String(20), nullable=False)
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(String(500), nullable=False)
    sha256 = Column(String(64), nullable=False, index=True)
    size = Column(BigInteger, nullable=False)
    media_type = Column(String(100))
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    main_marker = Column(
        Integer,
        Computed(
            "CASE WHEN role = 'main' THEN 1 ELSE NULL END",
            persisted=True,
        ),
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paper = relationship("Paper", back_populates="files")
    chunks = relationship(
        "PaperChunk",
        back_populates="paper_file",
        overlaps="chunks,paper",
    )


class PaperChunk(Base):
    """Current-revision text chunk; vectors are a rebuildable projection."""

    __tablename__ = "paper_chunks"
    __table_args__ = (
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_paper_chunks_chunk_index",
        ),
        CheckConstraint(
            "token_count IS NULL OR token_count >= 0",
            name="ck_paper_chunks_token_count",
        ),
        CheckConstraint(
            """
            (page_start IS NULL AND page_end IS NULL)
            OR
            (
                page_start IS NOT NULL
                AND page_end IS NOT NULL
                AND page_start >= 1
                AND page_end >= page_start
            )
            """,
            name="ck_paper_chunks_pages",
        ),
        UniqueConstraint(
            "paper_file_id",
            "chunk_index",
            name="uq_paper_chunks_file_index",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_paper_chunks_identity_revision",
        ),
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_chunks_paper_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["paper_file_id", "paper_id", "paper_revision"],
            ["paper_files.id", "paper_files.paper_id", "paper_files.paper_revision"],
            name="fk_paper_chunks_file_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_paper_chunks_paper_revision",
            "paper_id",
            "paper_revision",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, default=1, server_default="1", nullable=False)
    paper_file_id = Column(Integer, nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False)
    section_name = Column(String(500))
    heading = Column(String(500))
    content = Column(LONG_TEXT, nullable=False)
    token_count = Column(Integer)
    page_start = Column(Integer)
    page_end = Column(Integer)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    paper = relationship(
        "Paper",
        back_populates="chunks",
        overlaps="chunks,paper_file",
    )
    paper_file = relationship(
        "PaperFile",
        back_populates="chunks",
        overlaps="chunks,paper",
    )
    evidences = relationship(
        "PaperEvidence",
        back_populates="paper_chunk",
        overlaps="evidences,paper",
    )


class PaperEvidence(Base):
    """Evidence snapshot anchored to the same current-revision chunk."""

    __tablename__ = "paper_evidences"
    __table_args__ = (
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_paper_evidences_identity_revision",
        ),
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_evidences_paper_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["paper_chunk_id", "paper_id", "paper_revision"],
            ["paper_chunks.id", "paper_chunks.paper_id", "paper_chunks.paper_revision"],
            name="fk_paper_evidences_chunk_revision",
            ondelete="RESTRICT",
        ),
        Index(
            "ix_paper_evidences_chunk",
            "paper_chunk_id",
        ),
        Index(
            "ix_paper_evidences_paper_revision",
            "paper_id",
            "paper_revision",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, default=1, server_default="1", nullable=False)
    paper_chunk_id = Column(Integer, nullable=False)
    field_path = Column(String(255), nullable=False)
    section = Column(String(500))
    page_start = Column(Integer)
    page_end = Column(Integer)
    quote = Column(LONG_TEXT, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    paper = relationship(
        "Paper",
        back_populates="evidences",
        overlaps="evidences,paper_chunk",
    )
    paper_chunk = relationship(
        "PaperChunk",
        back_populates="evidences",
        overlaps="evidences,paper",
    )


class PaperReviewEvent(Base):
    """Append-only review decision for one whole paper revision."""

    __tablename__ = "paper_review_events"
    __table_args__ = (
        CheckConstraint(
            "status IN ('approved', 'rejected', 'pending')",
            name="ck_paper_review_events_status",
        ),
        CheckConstraint(
            "paper_revision >= 1",
            name="ck_paper_review_events_revision",
        ),
        Index(
            "ix_paper_review_events_paper_revision",
            "paper_id",
            "paper_revision",
            "reviewed_at",
        ),
        Index(
            "ix_paper_review_events_paper_time",
            "paper_id",
            "reviewed_at",
        ),
        Index(
            "ix_paper_review_events_reviewer_time",
            "reviewer_user_id",
            "reviewed_at",
            "id",
        ),
    )

    id = Column(Integer, primary_key=True)
    paper_id = Column(
        Integer,
        ForeignKey("papers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    paper_revision = Column(Integer, nullable=False, default=1, server_default="1")
    reviewer_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    status = Column(String(50), nullable=False)
    review_comment = Column(Text)
    reviewed_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    request_id = Column(String(64), unique=True, nullable=True)
    source = Column(String(20), nullable=False, default="single")

    paper = relationship("Paper", back_populates="review_events")
    reviewer = relationship("User", back_populates="review_events")


class MaterialFamily(Base):
    __tablename__ = "material_families"
    __table_args__ = (
        UniqueConstraint("code", name="uq_material_families_code"),
        UniqueConstraint("name_zh", name="uq_material_families_name_zh"),
        UniqueConstraint("normalized_name", name="uq_material_families_normalized_name"),
        CheckConstraint(
            "merged_into_id IS NULL OR merged_into_id <> id",
            name="ck_material_families_not_self_merged",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name_zh = Column(String(100), nullable=False)
    name_en = Column(String(160), nullable=False)
    normalized_name = Column(String(160), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    merged_into_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
    )
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases = relationship("MaterialFamilyAlias", back_populates="material_family")
    material_states = relationship("MaterialState", back_populates="material_family")
    merged_into = relationship("MaterialFamily", remote_side=[id])


class MaterialFamilyAlias(Base):
    __tablename__ = "material_family_aliases"
    __table_args__ = (
        UniqueConstraint(
            "normalized_alias",
            name="uq_material_family_alias_normalized",
        ),
        CheckConstraint(
            "language IN ('zh', 'en', 'code', 'other')",
            name="ck_material_family_alias_language",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    material_family_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alias = Column(String(160), nullable=False)
    normalized_alias = Column(String(160), nullable=False)
    language = Column(String(10), nullable=False, default="other", server_default="other")
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    material_family = relationship("MaterialFamily", back_populates="aliases")


class StructureFamily(Base):
    __tablename__ = "structure_families"
    __table_args__ = (
        UniqueConstraint("code", name="uq_structure_families_code"),
        UniqueConstraint("name_zh", name="uq_structure_families_name_zh"),
        UniqueConstraint("normalized_name", name="uq_structure_families_normalized_name"),
        CheckConstraint(
            "merged_into_id IS NULL OR merged_into_id <> id",
            name="ck_structure_families_not_self_merged",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name_zh = Column(String(100), nullable=False)
    name_en = Column(String(160), nullable=False)
    normalized_name = Column(String(160), nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    merged_into_id = Column(
        Integer,
        ForeignKey("structure_families.id", ondelete="RESTRICT"),
    )
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases = relationship("StructureFamilyAlias", back_populates="structure_family")
    merged_into = relationship("StructureFamily", remote_side=[id])


class StructureFamilyAlias(Base):
    __tablename__ = "structure_family_aliases"
    __table_args__ = (
        UniqueConstraint(
            "normalized_alias",
            name="uq_structure_family_alias_normalized",
        ),
        CheckConstraint(
            "language IN ('zh', 'en', 'code', 'other')",
            name="ck_structure_family_alias_language",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    structure_family_id = Column(
        Integer,
        ForeignKey("structure_families.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    alias = Column(String(160), nullable=False)
    normalized_alias = Column(String(160), nullable=False)
    language = Column(String(10), nullable=False, default="other", server_default="other")
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    structure_family = relationship("StructureFamily", back_populates="aliases")


class MaterialState(Base):
    __tablename__ = "material_states"
    __table_args__ = (
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_material_states_paper_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "state_kind IN ('theoretical', 'experimental', 'mixed', 'unknown')",
            name="ck_material_states_kind",
        ),
        CheckConstraint(
            """
            (pressure_min_gpa IS NULL AND pressure_max_gpa IS NULL)
            OR
            (
                pressure_min_gpa IS NOT NULL
                AND pressure_max_gpa IS NOT NULL
                AND pressure_min_gpa <= pressure_max_gpa
            )
            """,
            name="ck_material_states_pressure_range",
        ),
        CheckConstraint(
            """
            (pressure_value_gpa IS NULL OR pressure_value_gpa >= 0)
            AND (pressure_min_gpa IS NULL OR pressure_min_gpa >= 0)
            AND (temperature_value_k IS NULL OR temperature_value_k >= 0)
            AND (magnetic_field_t IS NULL OR magnetic_field_t >= 0)
            """,
            name="ck_material_states_nonnegative",
        ),
        CheckConstraint(
            "reported_space_group_number IS NULL OR reported_space_group_number BETWEEN 1 AND 230",
            name="ck_material_states_reported_space_group",
        ),
        CheckConstraint(
            "element_count IS NULL OR element_count BETWEEN 1 AND 118",
            name="ck_material_states_element_count",
        ),
        CheckConstraint(
            """
            material_dimensionality IN (
                'zero_dimensional', 'one_dimensional', 'two_dimensional',
                'three_dimensional', 'quasi_one_dimensional',
                'quasi_two_dimensional', 'unknown'
            )
            """,
            name="ck_material_states_dimensionality",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_material_states_identity_revision",
        ),
        Index(
            "ix_material_states_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        Index(
            "ix_material_states_material_pressure",
            "superconductor_id",
            "pressure_value_gpa",
        ),
        Index(
            "ix_material_states_paper_material_space_group",
            "paper_id",
            "superconductor_id",
            "reported_space_group_symbol",
            "reported_space_group_number",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    superconductor_id = Column(
        Integer,
        ForeignKey("superconductors.id", ondelete="RESTRICT"),
        nullable=False,
    )
    material_family_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
        index=True,
    )
    element_count = Column(SmallInteger)
    material_dimensionality = Column(
        String(32),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    pressure_value_gpa = Column(Numeric(14, 6))
    pressure_min_gpa = Column(Numeric(14, 6))
    pressure_max_gpa = Column(Numeric(14, 6))
    pressure_raw = Column(String(255))
    pressure_unit_raw = Column(String(50))
    reported_space_group_symbol = Column(String(100))
    reported_space_group_number = Column(SmallInteger)
    temperature_value_k = Column(Numeric(14, 6))
    temperature_raw = Column(String(255))
    temperature_unit_raw = Column(String(50))
    magnetic_field_t = Column(Numeric(14, 6))
    state_kind = Column(
        String(20),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    note = Column(Text)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    paper = relationship("Paper", back_populates="material_states")
    superconductor = relationship("Superconductor", back_populates="material_states")
    material_family = relationship("MaterialFamily", back_populates="material_states")
    structure_family_links = relationship(
        "MaterialStateStructureFamily",
        back_populates="material_state",
    )
    classification_proposals = relationship(
        "ClassificationProposal",
        back_populates="material_state",
    )
    classification_evidences = relationship(
        "ClassificationEvidence",
        back_populates="material_state",
    )


class MaterialStateStructureFamily(Base):
    __tablename__ = "material_state_structure_families"
    __table_args__ = (
        UniqueConstraint(
            "primary_marker",
            name="uq_material_state_structure_primary",
        ),
    )

    material_state_id = Column(
        BigInteger,
        ForeignKey("material_states.id", ondelete="CASCADE"),
        primary_key=True,
    )
    structure_family_id = Column(
        Integer,
        ForeignKey("structure_families.id", ondelete="RESTRICT"),
        primary_key=True,
    )
    is_primary = Column(Boolean, nullable=False, default=False, server_default="0")
    primary_marker = Column(
        BigInteger,
        Computed(
            "CASE WHEN is_primary = 1 THEN material_state_id ELSE NULL END",
            persisted=True,
        ),
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    material_state = relationship("MaterialState", back_populates="structure_family_links")
    structure_family = relationship("StructureFamily")


class ClassificationProposal(Base):
    __tablename__ = "classification_proposals"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ('material_family', 'structure_family')",
            name="ck_classification_proposals_dimension",
        ),
        CheckConstraint(
            "status IN ('proposed', 'under_review', 'resolved', 'rejected')",
            name="ck_classification_proposals_status",
        ),
        CheckConstraint(
            "source_kind IN ('ai', 'user', 'admin', 'migration')",
            name="ck_classification_proposals_source",
        ),
        CheckConstraint(
            """
            resolution_kind IS NULL OR resolution_kind IN (
                'mapped_existing', 'alias_created', 'formal_created', 'rejected'
            )
            """,
            name="ck_classification_proposals_resolution",
        ),
        Index(
            "ix_classification_proposals_queue",
            "status",
            "dimension",
            "created_at",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    material_state_id = Column(
        BigInteger,
        ForeignKey("material_states.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    dimension = Column(String(32), nullable=False)
    raw_name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default="proposed", server_default="proposed")
    source_kind = Column(String(20), nullable=False)
    resolution_kind = Column(String(32))
    material_family_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
    )
    structure_family_id = Column(
        Integer,
        ForeignKey("structure_families.id", ondelete="RESTRICT"),
    )
    proposed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    review_note = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    resolved_at = Column(DateTime(timezone=True))

    material_state = relationship("MaterialState", back_populates="classification_proposals")


class ClassificationEvidence(Base):
    __tablename__ = "classification_evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_classification_evidences_state_revision",
            ondelete="CASCADE",
        ),
        CheckConstraint(
            "dimension IN ('material_family', 'structure_family', 'element_count', 'material_dimensionality')",
            name="ck_classification_evidences_dimension",
        ),
        CheckConstraint(
            "source_kind IN ('reported', 'derived', 'reviewed')",
            name="ck_classification_evidences_source",
        ),
        CheckConstraint(
            "scope IN ('current_paper', 'referenced_work')",
            name="ck_classification_evidences_scope",
        ),
        Index(
            "ix_classification_evidences_paper_revision",
            "paper_id",
            "paper_revision",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    dimension = Column(String(32), nullable=False)
    material_family_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
    )
    structure_family_id = Column(
        Integer,
        ForeignKey("structure_families.id", ondelete="RESTRICT"),
    )
    proposal_id = Column(
        BigInteger,
        ForeignKey("classification_proposals.id", ondelete="SET NULL"),
    )
    source_kind = Column(String(20), nullable=False)
    scope = Column(String(20), nullable=False, default="current_paper", server_default="current_paper")
    raw_value = Column(String(255))
    section = Column(String(500))
    page_start = Column(Integer)
    page_end = Column(Integer)
    quote = Column(Text)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    material_state = relationship("MaterialState", back_populates="classification_evidences")


class ClassificationAuditEvent(Base):
    __tablename__ = "classification_audit_events"
    __table_args__ = (
        CheckConstraint(
            "dimension IN ('material_family', 'structure_family')",
            name="ck_classification_audits_dimension",
        ),
        CheckConstraint(
            "entity_kind IN ('term', 'alias', 'proposal')",
            name="ck_classification_audits_entity_kind",
        ),
        Index(
            "ix_classification_audits_entity_time",
            "dimension",
            "entity_kind",
            "entity_id",
            "created_at",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    dimension = Column(String(32), nullable=False)
    entity_kind = Column(String(20), nullable=False)
    entity_id = Column(BigInteger, nullable=False)
    action = Column(String(32), nullable=False)
    reason = Column(Text, nullable=False)
    before_json = Column(JSON)
    after_json = Column(JSON)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class StructureModel(Base):
    __tablename__ = "structure_models"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_structure_models_state_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["parent_structure_id", "paper_id", "paper_revision"],
            ["structure_models.id", "structure_models.paper_id", "structure_models.paper_revision"],
            name="fk_structure_models_parent_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "space_group_number IS NULL OR space_group_number BETWEEN 1 AND 230",
            name="ck_structure_models_space_group",
        ),
        CheckConstraint(
            "atom_count IS NULL OR atom_count >= 0",
            name="ck_structure_models_atom_count",
        ),
        CheckConstraint(
            "volume_angstrom3 IS NULL OR volume_angstrom3 >= 0",
            name="ck_structure_models_volume",
        ),
        CheckConstraint(
            """
            nuclear_treatment IN (
                'classical_static', 'harmonic', 'quasi_harmonic',
                'anharmonic_classical', 'anharmonic_quantum',
                'experimental', 'unknown'
            )
            """,
            name="ck_structure_models_nuclear_treatment",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_structure_models_identity_revision",
        ),
        UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_structure_models_state_revision",
        ),
        Index("ix_structure_models_state", "material_state_id"),
        Index("ix_structure_models_hash", "structure_hash"),
        Index(
            "ix_structure_models_paper_revision",
            "paper_id",
            "paper_revision",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    parent_structure_id = Column(BigInteger)
    space_group_symbol = Column(String(100))
    space_group_number = Column(SmallInteger)
    structure_format = Column(String(20), nullable=False)
    structure_text = Column(LONG_TEXT, nullable=False)
    structure_hash = Column(String(64), nullable=False)
    cell_parameters = Column(JSON)
    volume_angstrom3 = Column(Numeric(20, 8))
    atom_count = Column(Integer)
    geometry_method = Column(String(100))
    nuclear_treatment = Column(String(32), nullable=False)
    exchange_correlation = Column(String(100))
    calculation_code = Column(String(100))
    method_parameters = Column(JSON)
    source_locator = Column(String(500))
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CalculationContext(Base):
    __tablename__ = "calculation_contexts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_calculation_contexts_state_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_calculation_contexts_structure_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            """
            (structure_id IS NOT NULL AND missing_structure_reason IS NULL)
            OR
            (
                structure_id IS NULL
                AND missing_structure_reason IS NOT NULL
                AND length(trim(missing_structure_reason)) > 0
            )
            """,
            name="ck_calculation_contexts_structure",
        ),
        CheckConstraint(
            """
            phonon_nuclear_treatment IN (
                'classical_static', 'harmonic', 'quasi_harmonic',
                'anharmonic_classical', 'anharmonic_quantum',
                'experimental', 'unknown'
            )
            """,
            name="ck_calculation_contexts_nuclear_treatment",
        ),
        CheckConstraint(
            """
            (mu_star IS NULL OR mu_star >= 0)
            AND (lambda_ep IS NULL OR lambda_ep >= 0)
            AND (omega_log_k IS NULL OR omega_log_k >= 0)
            AND (energy_cutoff_value IS NULL OR energy_cutoff_value >= 0)
            """,
            name="ck_calculation_contexts_nonnegative",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_calculation_contexts_identity_revision",
        ),
        UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_calculation_contexts_state_revision",
        ),
        Index(
            "ix_calculation_contexts_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        Index("ix_calculation_contexts_state", "material_state_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    structure_id = Column(BigInteger)
    missing_structure_reason = Column(Text)
    electronic_method = Column(String(100))
    exchange_correlation = Column(String(100))
    pseudopotential_type = Column(String(100))
    pseudopotential_name = Column(String(255))
    spin_orbit_coupling = Column(Boolean)
    phonon_method = Column(String(100))
    phonon_nuclear_treatment = Column(String(32), nullable=False)
    epc_method = Column(String(100))
    mu_star = Column(Numeric(12, 8))
    lambda_ep = Column(Numeric(20, 8))
    omega_log_k = Column(Numeric(20, 8))
    k_grid = Column(String(100))
    q_grid = Column(String(100))
    energy_cutoff_value = Column(Numeric(20, 8))
    energy_cutoff_unit = Column(String(50))
    calculation_code = Column(String(100))
    parameters_json = Column(JSON)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class ExperimentalContext(Base):
    __tablename__ = "experimental_contexts"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_experimental_contexts_state_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_experimental_contexts_structure_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            """
            tc_criterion IN (
                'resistance_onset', 'resistance_midpoint', 'zero_resistance',
                'magnetic_susceptibility', 'specific_heat',
                'author_reported', 'unknown'
            )
            """,
            name="ck_experimental_contexts_criterion",
        ),
        CheckConstraint(
            """
            (applied_field_t IS NULL OR applied_field_t >= 0)
            AND (
                pressure_uncertainty_gpa IS NULL
                OR pressure_uncertainty_gpa >= 0
            )
            """,
            name="ck_experimental_contexts_nonnegative",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_experimental_contexts_identity_revision",
        ),
        UniqueConstraint(
            "id",
            "material_state_id",
            "paper_id",
            "paper_revision",
            name="uq_experimental_contexts_state_revision",
        ),
        Index(
            "ix_experimental_contexts_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        Index("ix_experimental_contexts_state", "material_state_id"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    structure_id = Column(BigInteger)
    sample_label = Column(String(255))
    sample_preparation = Column(Text)
    measurement_method = Column(String(100))
    tc_criterion = Column(String(64), nullable=False)
    applied_field_t = Column(Numeric(14, 6))
    pressure_uncertainty_gpa = Column(Numeric(14, 6))
    parameters_json = Column(JSON)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class TcResult(Base):
    __tablename__ = "tc_results"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_tc_results_state_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["calculation_context_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "calculation_contexts.id",
                "calculation_contexts.material_state_id",
                "calculation_contexts.paper_id",
                "calculation_contexts.paper_revision",
            ],
            name="fk_tc_results_calculation_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["experimental_context_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "experimental_contexts.id",
                "experimental_contexts.material_state_id",
                "experimental_contexts.paper_id",
                "experimental_contexts.paper_revision",
            ],
            name="fk_tc_results_experimental_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "result_kind IN ('theoretical', 'experimental')",
            name="ck_tc_results_kind",
        ),
        CheckConstraint(
            """
            tc_method IN (
                'experimental', 'anisotropic_eliashberg',
                'isotropic_eliashberg', 'allen_dynes',
                'mcmillan', 'unknown'
            )
            """,
            name="ck_tc_results_method",
        ),
        CheckConstraint(
            """
            (
                result_kind = 'theoretical'
                AND calculation_context_id IS NOT NULL
                AND experimental_context_id IS NULL
            )
            OR
            (
                result_kind = 'experimental'
                AND calculation_context_id IS NULL
                AND experimental_context_id IS NOT NULL
                AND tc_method = 'experimental'
            )
            """,
            name="ck_tc_results_context_kind",
        ),
        CheckConstraint(
            "tc_value_k IS NOT NULL OR (tc_min_k IS NOT NULL AND tc_max_k IS NOT NULL)",
            name="ck_tc_results_value",
        ),
        CheckConstraint(
            """
            (tc_min_k IS NULL AND tc_max_k IS NULL)
            OR
            (
                tc_min_k IS NOT NULL
                AND tc_max_k IS NOT NULL
                AND tc_min_k <= tc_max_k
            )
            """,
            name="ck_tc_results_range",
        ),
        CheckConstraint(
            """
            (tc_value_k IS NULL OR tc_value_k >= 0)
            AND (tc_min_k IS NULL OR tc_min_k >= 0)
            AND (uncertainty_k IS NULL OR uncertainty_k >= 0)
            """,
            name="ck_tc_results_nonnegative",
        ),
        UniqueConstraint(
            "paper_id",
            "paper_revision",
            "source_fingerprint",
            name="uq_tc_results_source",
        ),
        UniqueConstraint(
            "paper_id",
            "material_state_id",
            "tc_method",
            "representative_marker",
            name="uq_tc_results_representative",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_tc_results_identity_revision",
        ),
        Index(
            "ix_tc_results_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        Index(
            "ix_tc_results_state_method",
            "material_state_id",
            "tc_method",
        ),
        Index("ix_tc_results_method_value", "tc_method", "tc_value_k"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    calculation_context_id = Column(BigInteger)
    experimental_context_id = Column(BigInteger)
    result_kind = Column(String(16), nullable=False)
    tc_method = Column(String(64), nullable=False)
    tc_value_k = Column(Numeric(20, 8))
    tc_min_k = Column(Numeric(20, 8))
    tc_max_k = Column(Numeric(20, 8))
    uncertainty_k = Column(Numeric(20, 8))
    value_raw = Column(String(255), nullable=False)
    unit_raw = Column(String(50), nullable=False)
    source_locator = Column(String(500))
    source_fingerprint = Column(String(64), nullable=False)
    is_representative = Column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    representative_marker = Column(
        Integer,
        Computed(
            "CASE WHEN is_representative THEN 1 ELSE NULL END",
            persisted=True,
        ),
    )
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class PropertyDefinition(Base):
    __tablename__ = "property_definitions"
    __table_args__ = (
        CheckConstraint(
            "value_kind IN ('number', 'range', 'text', 'boolean')",
            name="ck_property_definitions_value_kind",
        ),
        CheckConstraint(
            """
            lower(code) NOT IN (
                'tc', 'critical_temperature', 'experimental',
                'anisotropic_eliashberg', 'isotropic_eliashberg',
                'allen_dynes', 'mcmillan'
            )
            """,
            name="ck_property_definitions_non_tc",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    canonical_unit = Column(String(50))
    value_kind = Column(String(20), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class SuperconductorProperty(Base):
    __tablename__ = "superconductor_properties"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_superconductor_properties_state_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["structure_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "structure_models.id",
                "structure_models.material_state_id",
                "structure_models.paper_id",
                "structure_models.paper_revision",
            ],
            name="fk_superconductor_properties_structure_revision",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["calculation_context_id", "material_state_id", "paper_id", "paper_revision"],
            [
                "calculation_contexts.id",
                "calculation_contexts.material_state_id",
                "calculation_contexts.paper_id",
                "calculation_contexts.paper_revision",
            ],
            name="fk_superconductor_properties_calculation_revision",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            """
            value_number IS NOT NULL
            OR (value_min IS NOT NULL AND value_max IS NOT NULL)
            OR length(trim(value_raw)) > 0
            """,
            name="ck_superconductor_properties_value",
        ),
        CheckConstraint(
            """
            (value_min IS NULL AND value_max IS NULL)
            OR
            (
                value_min IS NOT NULL
                AND value_max IS NOT NULL
                AND value_min <= value_max
            )
            """,
            name="ck_superconductor_properties_range",
        ),
        UniqueConstraint(
            "paper_id",
            "paper_revision",
            "source_fingerprint",
            name="uq_superconductor_properties_source",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_superconductor_properties_identity_revision",
        ),
        Index(
            "ix_superconductor_properties_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        Index(
            "ix_superconductor_properties_definition",
            "property_definition_id",
        ),
        Index(
            "ix_superconductor_properties_state",
            "material_state_id",
        ),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    material_state_id = Column(BigInteger, nullable=False)
    structure_id = Column(BigInteger)
    calculation_context_id = Column(BigInteger)
    property_definition_id = Column(
        Integer,
        ForeignKey("property_definitions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    material_raw = Column(String(255))
    name_raw = Column(String(255), nullable=False)
    value_raw = Column(Text, nullable=False)
    unit_raw = Column(String(100))
    value_number = Column(Numeric(30, 12))
    value_min = Column(Numeric(30, 12))
    value_max = Column(Numeric(30, 12))
    canonical_unit = Column(String(50))
    condition_note = Column(Text)
    source_fingerprint = Column(String(64), nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Temporary Python attribute aliases; the target table remains normalized.
    material = synonym("material_raw")
    name = synonym("name_raw")
    unit = synonym("unit_raw")


class TcResultEvidence(Base):
    __tablename__ = "tc_result_evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tc_result_id", "paper_id", "paper_revision"],
            ["tc_results.id", "tc_results.paper_id", "tc_results.paper_revision"],
            name="fk_tc_result_evidences_result",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["paper_evidence_id", "paper_id", "paper_revision"],
            [
                "paper_evidences.id",
                "paper_evidences.paper_id",
                "paper_evidences.paper_revision",
            ],
            name="fk_tc_result_evidences_evidence",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "tc_result_id",
            "paper_evidence_id",
            name="uq_tc_result_evidences",
        ),
        Index("ix_tc_result_evidences_evidence", "paper_evidence_id"),
    )

    tc_result_id = Column(BigInteger, primary_key=True)
    paper_evidence_id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    evidence_role = Column(
        String(32),
        nullable=False,
        default="primary",
        server_default="primary",
    )


class StructureModelEvidence(Base):
    __tablename__ = "structure_model_evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["structure_id", "paper_id", "paper_revision"],
            ["structure_models.id", "structure_models.paper_id", "structure_models.paper_revision"],
            name="fk_structure_model_evidences_structure",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["paper_evidence_id", "paper_id", "paper_revision"],
            [
                "paper_evidences.id",
                "paper_evidences.paper_id",
                "paper_evidences.paper_revision",
            ],
            name="fk_structure_model_evidences_evidence",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "structure_id",
            "paper_evidence_id",
            name="uq_structure_model_evidences",
        ),
        Index(
            "ix_structure_model_evidences_evidence",
            "paper_evidence_id",
        ),
    )

    structure_id = Column(BigInteger, primary_key=True)
    paper_evidence_id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    evidence_role = Column(
        String(32),
        nullable=False,
        default="primary",
        server_default="primary",
    )


class SuperconductorPropertyEvidence(Base):
    __tablename__ = "superconductor_property_evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["superconductor_property_id", "paper_id", "paper_revision"],
            [
                "superconductor_properties.id",
                "superconductor_properties.paper_id",
                "superconductor_properties.paper_revision",
            ],
            name="fk_superconductor_property_evidences_property",
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["paper_evidence_id", "paper_id", "paper_revision"],
            [
                "paper_evidences.id",
                "paper_evidences.paper_id",
                "paper_evidences.paper_revision",
            ],
            name="fk_superconductor_property_evidences_evidence",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "superconductor_property_id",
            "paper_evidence_id",
            name="uq_superconductor_property_evidences",
        ),
        Index(
            "ix_superconductor_property_evidences_evidence",
            "paper_evidence_id",
        ),
    )

    superconductor_property_id = Column(BigInteger, primary_key=True)
    paper_evidence_id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    evidence_role = Column(
        String(32),
        nullable=False,
        default="primary",
        server_default="primary",
    )


class LegacyBase(DeclarativeBase):
    """Mappings for old databases; excluded from the fresh target metadata."""


class SuperconductorRecord(LegacyBase):
    __tablename__ = "superconductor_records"

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, nullable=False, index=True)
    paper_id = Column(Integer, nullable=True, index=True)
    source_label = Column(String(255), nullable=False, index=True)
    pressure_gpa = Column(Float, nullable=False, index=True)
    space_group_symbol = Column(String(100))
    space_group_number = Column(Integer)
    crystal_structure = Column(String(255))
    thermodynamically_stable = Column(Boolean)
    dynamically_stable = Column(Boolean)
    energy_above_hull = Column(Float)
    mcmillan_tc = Column(Float)
    allen_dynes_tc = Column(Float)
    isotropic_eliashberg_tc = Column(Float)
    anisotropic_eliashberg_tc = Column(Float)
    experimental_tc = Column(Float)
    lambda_value = Column(Float)
    omega_log = Column(Float)
    n_ef_total = Column(Float)
    element_n_ef = Column(JSON)
    pseudopotential_type = Column(String(100))
    pseudopotential_name = Column(String(255))
    exchange_correlation_functional = Column(String(100))
    calculation_code = Column(String(100))
    k_grid = Column(String(100))
    q_grid = Column(String(100))
    energy_cutoff_value = Column(Float)
    energy_cutoff_unit = Column(String(50))
    show_in_chart = Column(Boolean, default=False, nullable=False, index=True)
    article_type = Column(String(10))
    superconductor_type = Column(String(20))
    s_factor = Column(Float)
    method = Column(String(255))
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class SuperconductorStructure(LegacyBase):
    __tablename__ = "superconductors_structures"

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, nullable=False, index=True)
    pressure_gpa = Column(Float, nullable=False, index=True)
    space_group_symbol = Column(String(100), index=True)
    space_group_number = Column(Integer, index=True)
    structure_format = Column(String(20), nullable=False, index=True)
    structure_text = Column(Text, nullable=False)
    structure_hash = Column(String(64), nullable=False, index=True)
    atom_count = Column(Integer)
    elements_list = Column(JSON)
    cell_parameters = Column(JSON)
    volume = Column(Float)
    review_status = Column(String(50), default="pending", nullable=False, index=True)
    is_default = Column(Boolean, default=False, nullable=False, index=True)
    source_type = Column(String(100), nullable=False, index=True)
    source_label = Column(String(255))
    created_by_user_id = Column(Integer, nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


# Temporary import compatibility for code that has not moved to the new name yet.
KeyProperty = SuperconductorProperty
