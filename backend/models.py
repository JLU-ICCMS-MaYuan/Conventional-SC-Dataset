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
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    created_structures = relationship(
        "SuperconductorStructure",
        back_populates="created_by_user",
        foreign_keys="SuperconductorStructure.created_by_user_id",
    )


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    doi = Column(String(255), unique=True, index=True, nullable=False)
    title = Column(Text, nullable=False)
    journal = Column(String(255))
    volume = Column(String(100))
    pages = Column(String(100))
    year = Column(Integer, index=True)
    abstract = Column(Text)
    authors = Column(JSON, nullable=False)
    uploaded_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    reviewed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    review_status = Column(String(50), default="pending", nullable=False, index=True)
    reviewed_at = Column(DateTime(timezone=True))
    review_comment = Column(Text)
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
