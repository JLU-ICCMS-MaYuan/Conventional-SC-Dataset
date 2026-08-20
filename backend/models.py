"""
SQLAlchemy models for the redesigned superconducting dataset schema.
"""
from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.database import Base


class PeriodicTableElement(Base):
    __tablename__ = "periodic_table_elements"

    id = Column(Integer, primary_key=True)
    atomic_number = Column(Integer, unique=True, index=True, nullable=False)
    symbol = Column(String(8), unique=True, index=True, nullable=False)
    english_name = Column(String(100), nullable=False)
    chinese_name = Column(String(100))
    atomic_mass = Column(Float)
    period_number = Column(Integer)
    group_number = Column(Integer)
    category = Column(String(100))


class ChemicalSystem(Base):
    __tablename__ = "chemical_systems"

    id = Column(Integer, primary_key=True)
    system_key = Column(String(255), unique=True, index=True, nullable=False)
    elements_list = Column(JSON, nullable=False)
    element_count = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    superconductors = relationship("Superconductor", back_populates="chemical_system")


class Superconductor(Base):
    __tablename__ = "superconductors"

    id = Column(Integer, primary_key=True)
    chemical_system_id = Column(Integer, ForeignKey("chemical_systems.id"), nullable=False, index=True)
    chemical_formula = Column(String(255), nullable=False)
    formula_normalized = Column(String(255), unique=True, index=True, nullable=False)
    display_name = Column(String(255), nullable=False)
    elements_list = Column(JSON, nullable=False)
    composition = Column(JSON, nullable=False)
    element_ratio = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    chemical_system = relationship("ChemicalSystem", back_populates="superconductors")
    records = relationship("SuperconductorRecord", back_populates="superconductor")
    structures = relationship("SuperconductorStructure", back_populates="superconductor")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    real_name = Column(String(100), nullable=False)
    affiliation = Column(String(255))
    role = Column(String(50), default="user", nullable=False, index=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)
    verification_code = Column(String(16))
    verification_expires = Column(DateTime(timezone=True))
    approved_at = Column(DateTime(timezone=True))
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    created_structures = relationship(
        "SuperconductorStructure",
        back_populates="created_by_user",
        foreign_keys="SuperconductorStructure.created_by_user_id",
    )


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    doi = Column(String(255), unique=True, index=True, nullable=True)
    title = Column(Text, nullable=True)
    journal = Column(String(255))
    volume = Column(String(100))
    pages = Column(String(100))
    year = Column(Integer, index=True)
    abstract = Column(Text)
    authors = Column(JSON, nullable=True)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    review_status = Column(String(50), default="pending", nullable=False, index=True)
    reviewed_at = Column(DateTime(timezone=True))
    review_comment = Column(Text)
    # LLM 富化列（旧库 alembic 演进列 + clean_results 结构化列）
    summary = Column(Text)
    paper_type = Column(String(20))
    theoretical_subtype = Column(String(20), nullable=True)
    keywords_tags = Column(Text)
    source_file_path = Column(String(500))
    methodology = Column(Text)
    key_finding = Column(Text)
    rationale = Column(Text)
    research_materials = Column(JSON)
    referenced_materials = Column(JSON)
    material_relations = Column(JSON)
    builds_on = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

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
    records = relationship("SuperconductorRecord", back_populates="paper")
    key_properties = relationship("KeyProperty", back_populates="paper")


class PaperReviewEvent(Base):
    """一次不可变的论文审核动作，用于审计与贡献统计。"""

    __tablename__ = "paper_review_events"

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, nullable=False, index=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(50), nullable=False)
    review_comment = Column(Text)
    reviewed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    request_id = Column(String(64), unique=True, nullable=True)
    source = Column(String(20), nullable=False, default="single")

    reviewer = relationship("User", back_populates="review_events")


class KeyProperty(Base):
    """通用物性记录（源自 data/clean_results 的 key_properties，v2 库替代 SuperconductorRecord）

    name 为规范物性名（backend/prop_names.py 归一），name_raw 保留 LLM 原始写法；
    范围值保真存 value_min/value_max（单值时两者相等），condition 原样存 JSON，
    高频检索条件（压强/温度）提升为独立列。
    """
    __tablename__ = "key_properties"

    id = Column(Integer, primary_key=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    superconductor_id = Column(Integer, ForeignKey("superconductors.id"), nullable=True, index=True)
    material = Column(String(255), nullable=False, index=True)   # 原始材料名（含无法解析为化学式者）
    name = Column(String(100), nullable=False, index=True)       # 规范物性名
    name_raw = Column(String(255), nullable=False)               # 原始物性名
    name_note = Column(String(500))
    value_min = Column(Float, index=True)
    value_max = Column(Float)
    value_raw = Column(String(255))                              # 无法解析为数值时的原始值
    unit = Column(String(50))
    pressure_gpa = Column(Float, index=True)                     # condition.pressure（GPa）
    temperature_k = Column(Float)                                # condition.temperature（K）
    condition_json = Column(JSON)                                # 完整 condition 原样
    condition_note = Column(Text)
    is_primary = Column(Boolean, default=False, nullable=False, index=True)
    superconductor_type = Column(String(20), index=True)
    article_type = Column(String(10))
    source_label = Column(String(50), nullable=False, default="clean_results")
    structure_text = Column(Text)          # CIF/POSCAR 结构文本
    structure_format = Column(String(20))  # cif / poscar / vasp
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    paper = relationship("Paper", back_populates="key_properties")
    superconductor = relationship("Superconductor")


class ChartGroup(Base):
    """散点图数据点组合"""
    __tablename__ = "chart_groups"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    is_preset = Column(Boolean, default=False, nullable=False, index=True)
    is_public = Column(Boolean, default=False, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    creator = relationship("User")
    items = relationship("ChartGroupItem", back_populates="group", cascade="all, delete-orphan",
                         order_by="ChartGroupItem.sort_order")


class ChartGroupItem(Base):
    """组合内的数据点（kp 引用或自定义点）"""
    __tablename__ = "chart_group_items"

    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("chart_groups.id"), nullable=False, index=True)
    key_property_id = Column(Integer, ForeignKey("key_properties.id"), nullable=True, index=True)
    sort_order = Column(Integer, default=0)
    # 自定义点字段（key_property_id 为空时生效）
    custom_label = Column(String(255))
    custom_tc = Column(Float)
    custom_pressure = Column(Float)
    custom_type = Column(String(20))
    custom_article_type = Column(String(10))
    custom_year = Column(Integer)

    group = relationship("ChartGroup", back_populates="items")
    key_property = relationship("KeyProperty")


class SuperconductorRecord(Base):
    __tablename__ = "superconductor_records"

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, ForeignKey("superconductors.id"), nullable=False, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True, index=True)
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
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    superconductor = relationship("Superconductor", back_populates="records")
    paper = relationship("Paper", back_populates="records")


class SuperconductorStructure(Base):
    __tablename__ = "superconductors_structures"
    __table_args__ = (
        Index(
            "ix_superconductors_structures_identity",
            "superconductor_id",
            "space_group_symbol",
            "space_group_number",
            "pressure_gpa",
        ),
    )

    id = Column(Integer, primary_key=True)
    superconductor_id = Column(Integer, ForeignKey("superconductors.id"), nullable=False, index=True)
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
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    superconductor = relationship("Superconductor", back_populates="structures")
    created_by_user = relationship(
        "User",
        back_populates="created_structures",
        foreign_keys=[created_by_user_id],
    )


class PaperChunk(Base):
    """论文文本块（向量检索用，向量存 Qdrant，文本存 MySQL）"""
    __tablename__ = "paper_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, comment="块编号，从 0 开始")
    section_name = Column(String(500), nullable=True, comment="章节名如 Introduction/Results")
    heading = Column(String(500), nullable=True, comment="小节标题原文")
    content = Column(Text, nullable=False, comment="块文本内容")
    token_count = Column(Integer, nullable=True, comment="近似 token 数")
