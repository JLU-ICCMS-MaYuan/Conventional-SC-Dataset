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
BIGINT_ID = BigInteger().with_variant(Integer, "sqlite")


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
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"], ["papers.id", "papers.content_revision"],
            name="fk_chemical_systems_paper_revision", ondelete="RESTRICT", onupdate="CASCADE",
        ),
        UniqueConstraint("id", "paper_id", "paper_revision", name="uq_chemical_systems_identity_revision"),
        UniqueConstraint("paper_id", "paper_revision", "system_key", name="uq_chemical_systems_scope"),
        Index("ix_chemical_systems_system_key", "system_key"),
    )

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, nullable=False, index=True)
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
        ForeignKeyConstraint(
            ["chemical_system_id", "paper_id", "paper_revision"],
            ["chemical_systems.id", "chemical_systems.paper_id", "chemical_systems.paper_revision"],
            name="fk_superconductors_system_revision", ondelete="RESTRICT", onupdate="CASCADE",
        ),
        UniqueConstraint("id", "paper_id", "paper_revision", name="uq_superconductors_identity_revision"),
        UniqueConstraint("paper_id", "paper_revision", "composition_key", name="uq_superconductors_scope"),
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
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, nullable=False, index=True)
    chemical_system_id = Column(Integer, nullable=False, index=True)
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
    material_states = relationship(
        "MaterialState",
        back_populates="superconductor",
        overlaps="material_states,paper",
    )


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
    history_events = relationship("PaperHistoryEvent", back_populates="actor")
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
        CheckConstraint(
            "superconductor_kind IN ('conventional', 'unconventional', 'unknown')",
            name="ck_papers_superconductor_kind",
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
    year = Column(Integer, index=True, nullable=False)
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
    superconductor_kind = Column(
        String(32),
        nullable=False,
        default="unknown",
        server_default="unknown",
    )
    keywords_tags = Column(Text)
    methodology = Column(Text)
    knowledge_graph_title = Column(String(200), nullable=True)
    key_finding = Column(Text)
    research_motivation = Column(Text)
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
    history_events = relationship("PaperHistoryEvent", back_populates="paper")
    material_family_links = relationship(
        "PaperMaterialFamily",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    reference_extractions = relationship(
        "PaperReferenceExtraction",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    outgoing_references = relationship(
        "PaperReference",
        back_populates="citing_paper",
        foreign_keys="PaperReference.paper_id",
        cascade="all, delete-orphan",
    )
    graph_marks = relationship(
        "PaperGraphMark",
        back_populates="paper",
        cascade="all, delete-orphan",
    )
    material_states = relationship(
        "MaterialState",
        back_populates="paper",
        overlaps="material_states,superconductor",
    )


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


class PaperHistoryEvent(Base):
    """Append-only upload, modification, or review action for one paper revision."""

    __tablename__ = "paper_history_events"
    __table_args__ = (
        CheckConstraint(
            """
            (event_type = 'reviewed' AND review_status IN ('approved', 'rejected', 'pending'))
            OR
            (event_type IN ('uploaded', 'modified') AND review_status IS NULL AND review_comment IS NULL)
            """,
            name="ck_paper_history_events_shape",
        ),
        CheckConstraint(
            "paper_revision >= 1",
            name="ck_paper_history_events_revision",
        ),
        Index(
            "ix_paper_history_events_paper_time",
            "paper_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_paper_history_events_actor_time",
            "actor_user_id",
            "occurred_at",
            "id",
        ),
        Index(
            "ix_paper_history_events_paper_revision",
            "paper_id",
            "paper_revision",
        ),
        UniqueConstraint("operation_id", name="uq_paper_history_events_operation_id"),
    )

    id = Column(Integer, primary_key=True)
    paper_id = Column(
        Integer,
        ForeignKey("papers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    paper_revision = Column(Integer, nullable=False, default=1, server_default="1")
    event_type = Column(String(20), nullable=False)
    actor_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    actor_username_snapshot = Column(String(32))
    review_status = Column(String(50))
    review_comment = Column(Text)
    occurred_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    operation_id = Column(String(64), nullable=True)
    classification_snapshot = Column(JSON)

    paper = relationship("Paper", back_populates="history_events")
    actor = relationship("User", back_populates="history_events")


class MaterialFamily(Base):
    __tablename__ = "material_families"
    __table_args__ = (
        UniqueConstraint("code", name="uq_material_families_code"),
        UniqueConstraint("name_zh", name="uq_material_families_name_zh"),
        UniqueConstraint("normalized_name", name="uq_material_families_normalized_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name_zh = Column(String(100), nullable=False)
    name_en = Column(String(160))
    normalized_name = Column(String(160), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases = relationship("MaterialFamilyAlias", back_populates="material_family")
    paper_links = relationship("PaperMaterialFamily", back_populates="material_family")


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


class PaperMaterialFamily(Base):
    __tablename__ = "paper_material_families"
    __table_args__ = (
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_material_families_paper_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
    )

    paper_id = Column(Integer, primary_key=True)
    paper_revision = Column(Integer, primary_key=True)
    material_family_id = Column(
        Integer,
        ForeignKey("material_families.id", ondelete="RESTRICT"),
        primary_key=True,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    paper = relationship("Paper", back_populates="material_family_links")
    material_family = relationship("MaterialFamily", back_populates="paper_links")


class PaperReferenceExtraction(Base):
    """GROBID 对一篇论文当前内容版本的整次参考文献解析。"""

    __tablename__ = "paper_reference_extractions"
    __table_args__ = (
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_reference_extractions_paper_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        CheckConstraint(
            "status IN ('succeeded', 'partial', 'failed', 'unavailable')",
            name="ck_paper_reference_extractions_status",
        ),
    )

    paper_id = Column(Integer, primary_key=True)
    paper_revision = Column(Integer, primary_key=True)
    status = Column(String(20), nullable=False)
    parser_name = Column(String(32), nullable=False, default="grobid", server_default="grobid")
    parser_version = Column(String(64))
    error_message = Column(Text)
    processed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    paper = relationship("Paper", back_populates="reference_extractions")


class PaperReference(Base):
    """一条可复核的原始引文，以及它到 SC-Wiki Paper 的保守匹配结果。"""

    __tablename__ = "paper_references"
    __table_args__ = (
        ForeignKeyConstraint(
            ["paper_id", "paper_revision"],
            ["papers.id", "papers.content_revision"],
            name="fk_paper_references_citing_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        CheckConstraint("reference_index >= 0", name="ck_paper_references_index"),
        CheckConstraint(
            "match_status IN ('matched', 'unmatched', 'ambiguous')",
            name="ck_paper_references_match_status",
        ),
        CheckConstraint(
            "match_method IS NULL OR match_method IN ('doi', 'title_year', 'manual')",
            name="ck_paper_references_match_method",
        ),
        CheckConstraint(
            "(match_status = 'matched' AND cited_paper_id IS NOT NULL AND match_method IS NOT NULL) "
            "OR (match_status IN ('unmatched', 'ambiguous') AND cited_paper_id IS NULL AND match_method IS NULL)",
            name="ck_paper_references_match_consistency",
        ),
        UniqueConstraint(
            "paper_id",
            "paper_revision",
            "reference_index",
            name="uq_paper_references_source_index",
        ),
        Index("ix_paper_references_source_revision", "paper_id", "paper_revision"),
        Index("ix_paper_references_doi", "doi"),
        Index("ix_paper_references_normalized_title", "normalized_title"),
        Index("ix_paper_references_year", "year"),
        Index("ix_paper_references_cited_paper", "cited_paper_id"),
    )

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    reference_index = Column(Integer, nullable=False)
    raw_citation = Column(LONG_TEXT, nullable=False)
    doi = Column(String(255))
    title = Column(Text)
    normalized_title = Column(String(512))
    authors = Column(JSON)
    year = Column(Integer)
    cited_paper_id = Column(Integer, ForeignKey("papers.id", ondelete="RESTRICT"), nullable=True)
    match_status = Column(String(20), nullable=False, default="unmatched", server_default="unmatched")
    match_method = Column(String(20))
    match_checked_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    citing_paper = relationship(
        "Paper",
        back_populates="outgoing_references",
        foreign_keys=[paper_id],
    )
    cited_paper = relationship("Paper", foreign_keys=[cited_paper_id])


class PaperGraphMark(Base):
    """由管理员确认的领域里程碑，不参与自动引用匹配。"""

    __tablename__ = "paper_graph_marks"
    __table_args__ = (
        CheckConstraint(
            "mark_type IN ('origin', 'breakthrough')",
            name="ck_paper_graph_marks_type",
        ),
    )

    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="RESTRICT"), primary_key=True)
    mark_type = Column(String(20), primary_key=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    paper = relationship("Paper", back_populates="graph_marks")


class StructureFamily(Base):
    __tablename__ = "structure_families"
    __table_args__ = (
        UniqueConstraint("code", name="uq_structure_families_code"),
        UniqueConstraint("name_zh", name="uq_structure_families_name_zh"),
        UniqueConstraint("normalized_name", name="uq_structure_families_normalized_name"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), nullable=False)
    name_zh = Column(String(100), nullable=False)
    name_en = Column(String(160))
    normalized_name = Column(String(160), nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    aliases = relationship("StructureFamilyAlias", back_populates="structure_family")


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
        ForeignKeyConstraint(
            ["superconductor_id", "paper_id", "paper_revision"],
            ["superconductors.id", "superconductors.paper_id", "superconductors.paper_revision"],
            name="fk_material_states_superconductor_revision", ondelete="RESTRICT", onupdate="CASCADE",
        ),
        CheckConstraint(
            "state_kind IN ('theoretical', 'experimental', 'mixed', 'unknown')",
            name="ck_material_states_kind",
        ),
        CheckConstraint(
            """
            pressure_min_gpa IS NULL
            OR pressure_max_gpa IS NULL
            OR pressure_min_gpa <= pressure_max_gpa
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
        CheckConstraint(
            "crystal_system IN ('triclinic', 'monoclinic', 'orthorhombic', "
            "'tetragonal', 'trigonal', 'hexagonal', 'cubic', 'unknown')",
            name="ck_material_states_crystal_system",
        ),
        UniqueConstraint(
            "id",
            "paper_id",
            "paper_revision",
            name="uq_material_states_identity_revision",
        ),
        UniqueConstraint("paper_id", "paper_revision", "state_key", name="uq_material_states_paper_state_key"),
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

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    state_key = Column(String(96), nullable=False)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    superconductor_id = Column(Integer, nullable=False)
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
    crystal_system = Column(
        String(32),
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

    paper = relationship(
        "Paper",
        back_populates="material_states",
        overlaps="material_states,superconductor",
    )
    superconductor = relationship(
        "Superconductor",
        back_populates="material_states",
        overlaps="material_states,paper",
    )
    structure_family_links = relationship(
        "MaterialStateStructureFamily",
        back_populates="material_state",
    )
    property_modules = relationship(
        "PropertyModule",
        back_populates="material_state",
        cascade="all, delete-orphan",
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
            persisted=False,
        ),
    )
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    material_state = relationship("MaterialState", back_populates="structure_family_links")
    structure_family = relationship("StructureFamily")


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
                'mcmillan', 'scdft', 'other', 'unknown'
            )
            """,
            name="ck_tc_results_method",
        ),
        CheckConstraint(
            """
            (
                tc_method = 'experimental'
                AND result_kind = 'experimental'
                AND calculation_context_id IS NULL
                AND experimental_context_id IS NOT NULL
            )
            OR
            (
                tc_method <> 'experimental'
                AND result_kind = 'theoretical'
                AND calculation_context_id IS NOT NULL
                AND experimental_context_id IS NULL
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
    tc_method_custom = Column(String(128))
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


# Issue #90: unified, schema-driven material properties.  These models are
# additive during the migration window; legacy tables remain available until
# the contract migration has been verified in production.
PROPERTY_MODULE_CODES = (
    "superconductive_properties",
    "dynamical_properties",
    "thermodynamical_properties",
    "electronic_properties",
)
PROPERTY_RECORD_VALUE_KINDS = ("number", "range", "text", "boolean")


class PropertyModule(Base):
    __tablename__ = "property_modules"
    __table_args__ = (
        ForeignKeyConstraint(
            ["material_state_id", "paper_id", "paper_revision"],
            ["material_states.id", "material_states.paper_id", "material_states.paper_revision"],
            name="fk_property_modules_state_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        CheckConstraint(
            "module_code IN ('superconductive_properties','dynamical_properties','thermodynamical_properties','electronic_properties')",
            name="ck_property_modules_code",
        ),
        CheckConstraint("display_order >= 0", name="ck_property_modules_order"),
        UniqueConstraint("material_state_id", "module_code", name="uq_property_modules_state_code"),
        UniqueConstraint(
            "material_state_id",
            "module_key",
            name="uq_property_modules_state_key",
        ),
        UniqueConstraint("id", "material_state_id", "paper_id", "paper_revision", name="uq_property_modules_identity_rev"),
        Index("ix_property_modules_state", "material_state_id"),
    )

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    module_key = Column(String(96), nullable=False)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, nullable=False, index=True)
    material_state_id = Column(BIGINT_ID, nullable=False)
    module_code = Column(String(64), nullable=False)
    definition_key = Column(String(255), nullable=False, default="module.property", server_default="module.property")
    definition_version = Column(Integer, nullable=False, default=1, server_default="1")
    display_order = Column(Integer, nullable=False, default=0, server_default="0")
    metadata_json = Column(JSON, nullable=False, default=dict, server_default="{}")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    material_state = relationship("MaterialState", back_populates="property_modules")
    records = relationship("PropertyRecord", back_populates="module", cascade="all, delete-orphan")


class FormDefinition(Base):
    __tablename__ = "form_definitions"
    __table_args__ = (
        CheckConstraint("target_kind IN ('property_module','property_record')", name="ck_form_definitions_target"),
        CheckConstraint("status IN ('draft','published','retired')", name="ck_form_definitions_status"),
        CheckConstraint("version >= 1", name="ck_form_definitions_version"),
        UniqueConstraint("definition_key", "version", name="uq_form_definitions_key_version"),
        Index("ix_form_definitions_lookup", "definition_key", "status"),
        Index("ix_form_definitions_module", "module_code", "target_kind", "status"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    definition_key = Column(String(255), nullable=False)
    version = Column(Integer, nullable=False)
    target_kind = Column(String(32), nullable=False)
    module_code = Column(String(64), nullable=False)
    record_type = Column(String(64))
    method_code = Column(String(64))
    property_code = Column(String(100))
    core_schema = Column(JSON, nullable=False, default=dict, server_default="{}")
    json_schema = Column(JSON, nullable=False, default=dict, server_default="{}")
    ui_schema = Column(JSON, nullable=False, default=dict, server_default="{}")
    status = Column(String(20), nullable=False, default="draft", server_default="draft")
    checksum = Column(String(64), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    published_by = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    published_at = Column(DateTime(timezone=True))


class PropertyRecord(Base):
    __tablename__ = "property_records"
    __table_args__ = (
        ForeignKeyConstraint(
            ["module_id", "material_state_id", "paper_id", "paper_revision"],
            ["property_modules.id", "property_modules.material_state_id", "property_modules.paper_id", "property_modules.paper_revision"],
            name="fk_property_records_module_revision",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        ForeignKeyConstraint(
            ["definition_id"], ["form_definitions.id"],
            name="fk_property_records_definition", ondelete="RESTRICT",
        ),
        CheckConstraint("record_type IN ('predicted_tc','measured_tc','property')", name="ck_property_records_type"),
        CheckConstraint("value_kind IN ('number','range','text','boolean')", name="ck_property_records_value_kind"),
        CheckConstraint("(value_min IS NULL AND value_max IS NULL) OR (value_min IS NOT NULL AND value_max IS NOT NULL AND value_min <= value_max)", name="ck_property_records_range"),
        CheckConstraint("uncertainty IS NULL OR uncertainty >= 0", name="ck_property_records_uncertainty"),
        CheckConstraint("(value_kind <> 'number' OR value_number IS NOT NULL) AND (value_kind <> 'range' OR (value_min IS NOT NULL AND value_max IS NOT NULL)) AND (value_kind <> 'text' OR value_text IS NOT NULL) AND (value_kind <> 'boolean' OR value_boolean IS NOT NULL)", name="ck_property_records_value_shape"),
        CheckConstraint("(record_type NOT IN ('predicted_tc','measured_tc')) OR (property_code = 'tc' AND method_code IS NOT NULL)", name="ck_property_records_tc_identity"),
        CheckConstraint("(property_code = 'custom' AND record_type = 'property' AND custom_property_key IS NOT NULL) OR (property_code <> 'custom' AND custom_property_key IS NULL)", name="ck_property_records_custom_identity"),
        CheckConstraint("(record_type <> 'predicted_tc' OR (payload_json IS NOT NULL AND JSON_EXTRACT(payload_json, '$.calculation_conditions') IS NOT NULL AND JSON_EXTRACT(payload_json, '$.experimental_conditions') IS NULL)) AND (record_type <> 'measured_tc' OR (payload_json IS NOT NULL AND JSON_EXTRACT(payload_json, '$.experimental_conditions') IS NOT NULL AND JSON_EXTRACT(payload_json, '$.calculation_conditions') IS NULL))", name="ck_property_records_condition_type"),
        UniqueConstraint("module_id", "record_key", name="uq_property_records_module_key"),
        UniqueConstraint("paper_id", "paper_revision", "source_fingerprint", name="uq_property_records_source"),
        UniqueConstraint("id", "paper_id", "paper_revision", name="uq_property_records_identity_rev"),
        Index("ix_property_records_state_type_method", "material_state_id", "record_type", "method_code"),
        Index("ix_property_records_tc_value", "property_code", "value_number"),
    )

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    record_key = Column(String(96), nullable=False)
    paper_id = Column(Integer, nullable=False, index=True)
    paper_revision = Column(Integer, nullable=False, index=True)
    material_state_id = Column(BIGINT_ID, nullable=False, index=True)
    module_id = Column(BIGINT_ID, nullable=False, index=True)
    record_type = Column(String(64), nullable=False)
    property_code = Column(String(100), nullable=False)
    custom_property_key = Column(String(96))
    definition_id = Column(Integer, nullable=False)
    definition_key = Column(String(255), nullable=False)
    definition_version = Column(Integer, nullable=False)
    name_raw = Column(String(255), nullable=False)
    value_kind = Column(String(20), nullable=False)
    value_raw = Column(Text, nullable=False)
    value_number = Column(Numeric(30, 12))
    value_min = Column(Numeric(30, 12))
    value_max = Column(Numeric(30, 12))
    value_text = Column(Text)
    value_boolean = Column(Boolean)
    uncertainty = Column(Numeric(30, 12))
    unit_raw = Column(String(100))
    canonical_unit = Column(String(50))
    method_code = Column(String(100))
    method_raw = Column(String(255))
    criterion_code = Column(String(64))
    criterion_raw = Column(String(255))
    is_representative = Column(Boolean, nullable=False, default=False, server_default="0")
    structure_key = Column(String(96))
    payload_json = Column(JSON, nullable=False, default=dict, server_default="{}")
    source_fingerprint = Column(String(64), nullable=False)
    record_checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    module = relationship("PropertyModule", back_populates="records")
    definition = relationship("FormDefinition")
    evidences = relationship("PropertyRecordEvidence", back_populates="record", cascade="all, delete-orphan")


class PropertyRecordDefinitionEvent(Base):
    __tablename__ = "property_record_definition_events"
    __table_args__ = (Index("ix_property_record_definition_events_record", "record_id", "created_at"),)

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    record_id = Column(BIGINT_ID, ForeignKey("property_records.id", ondelete="RESTRICT"), nullable=False)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    record_key = Column(String(96), nullable=False)
    operation = Column(String(20), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"))
    from_definition_key = Column(String(255), nullable=False)
    from_definition_version = Column(Integer, nullable=False)
    to_definition_key = Column(String(255), nullable=False)
    to_definition_version = Column(Integer, nullable=False)
    before_snapshot = Column(JSON, nullable=False)
    after_snapshot = Column(JSON, nullable=False)
    request_checksum = Column(String(64), nullable=False)
    previous_event_id = Column(BIGINT_ID)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PropertyDefinitionPromotionEvent(Base):
    __tablename__ = "property_definition_promotion_events"
    __table_args__ = (
        UniqueConstraint("operation_id", name="uq_property_promotion_operation"),
        UniqueConstraint("source_paper_id", "source_paper_revision", "source_record_key", name="uq_property_promotion_source"),
        Index("ix_property_promotion_target", "target_definition_key"),
    )

    id = Column(BIGINT_ID, primary_key=True, autoincrement=True)
    operation_id = Column(String(64), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_paper_id = Column(Integer, nullable=False)
    source_paper_revision = Column(Integer, nullable=False)
    source_record_key = Column(String(96), nullable=False)
    source_snapshot = Column(JSON, nullable=False)
    target_definition_key = Column(String(255), nullable=False)
    target_definition_version = Column(Integer, nullable=False)
    target_checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class PropertyRecordEvidence(Base):
    __tablename__ = "property_record_evidences"
    __table_args__ = (
        ForeignKeyConstraint(
            ["record_id", "paper_id", "paper_revision"],
            ["property_records.id", "property_records.paper_id", "property_records.paper_revision"],
            name="fk_property_record_evidences_record", ondelete="CASCADE", onupdate="CASCADE",
        ),
        ForeignKeyConstraint(
            ["paper_evidence_id"],
            ["paper_evidences.id"],
            name="fk_property_record_evidences_evidence", ondelete="CASCADE",
        ),
        UniqueConstraint("record_id", "paper_evidence_id", name="uq_property_record_evidences"),
    )

    record_id = Column(BIGINT_ID, primary_key=True)
    paper_evidence_id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False)
    paper_revision = Column(Integer, nullable=False)
    field_path = Column(String(255), nullable=False, default="", server_default="")
    evidence_role = Column(String(32), nullable=False, default="primary", server_default="primary")
    record = relationship("PropertyRecord", back_populates="evidences")


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
