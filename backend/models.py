"""
数据库模型定义

当前数据主体采用 data/import_papers_to_sqlite.py 生成的新结构：
- papers 保存论文元数据
- compounds 保存具体化学式与组成
- paper_data 关联论文与化合物，并保存物理数据点
- paper_images 每篇论文一行，最多保存 fig1..fig40
"""
from sqlalchemy import Column, Integer, String, Text, BLOB, DateTime, ForeignKey, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import json

from backend.database import Base, ImageBase


class Element(Base):
    """元素表 - 存储118个化学元素"""
    __tablename__ = "elements"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(3), unique=True, nullable=False, index=True)
    name = Column(String(50), nullable=False)
    name_zh = Column(String(50))
    atomic_number = Column(Integer, unique=True, nullable=False)

    def __repr__(self):
        return f"<Element {self.symbol} ({self.name})>"


class Compound(Base):
    """具体化合物表 - 存储化学式与元素组成"""
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True, index=True)
    chemical_formula = Column(Text, unique=True, index=True)
    element_list = Column(Text)
    composition = Column(Text)
    element_id_list = Column(Text)
    element_ratio = Column(Text)

    physical_parameters = relationship("PaperData", back_populates="compound")

    @property
    def element_symbols(self) -> str:
        """兼容旧前端：把具体化合物的元素列表显示为 H-S 形式。"""
        import json

        try:
            values = json.loads(self.element_list or "[]")
        except Exception:
            values = []
        return "-".join(values) if values else (self.chemical_formula or "")

    def __repr__(self):
        return f"<Compound {self.chemical_formula}>"


class User(Base):
    """用户/管理员表，仍由网站认证系统使用"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    real_name = Column(String(100), nullable=False)
    is_admin = Column(Boolean, default=False)
    is_superadmin = Column(Boolean, default=False)
    is_approved = Column(Boolean, default=False)
    is_email_verified = Column(Boolean, default=False)
    verification_code = Column(String(10))
    verification_expires = Column(DateTime)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime)
    approved_by = Column(Integer, ForeignKey("users.id"))
    reviewed_papers = relationship("Paper", back_populates="reviewer", foreign_keys="Paper.reviewed_by")

    def __repr__(self):
        return f"<User {self.email} ({self.real_name})>"


class Paper(Base):
    """论文元数据表"""
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    doi = Column(Text, index=True)
    paper_images_id = Column(Integer)
    title = Column(Text)
    authors = Column(Text)
    journal = Column(Text)
    volume = Column(Text)
    pages = Column(Text)
    year = Column(Integer, index=True)
    abstract = Column(Text)
    imagetxts = Column(Text)
    imagetxts_cn = Column(Text)
    is_referenced_by_count = Column("is-referenced-by-count", Integer)

    # 网站业务字段：导入脚本只负责科研数据，网站启动时补齐这些列。
    contributor_name = Column(String(100), default="Data Import")
    contributor_affiliation = Column(String(200), default="System")
    notes = Column(Text)
    review_status = Column(String(20), default="unreviewed", nullable=False, index=True)
    reviewed_by = Column(Integer, ForeignKey("users.id"))
    reviewed_at = Column(DateTime)
    review_comment = Column(Text)
    show_in_chart = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    physical_parameters = relationship("PaperData", back_populates="paper", cascade="all, delete-orphan")
    reviewer = relationship("User", back_populates="reviewed_papers", foreign_keys=[reviewed_by])

    def __repr__(self):
        return f"<Paper {self.doi}>"


class PaperData(Base):
    """论文中的化合物/结构/条件数据点"""
    __tablename__ = "paper_data"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), index=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), index=True)
    article_type = Column(Text)
    superconductor_type = Column(Text)
    chemical_formula = Column(Text)
    crystal_structure = Column(Text)
    tc = Column(Text)
    tc_press = Column(Text)
    lambda_val = Column(Float)
    omega_log = Column(Float)
    n_ef = Column(Float)
    s_factor = Column(Float)
    structure_file_name = Column(Text)
    structure_file_data = Column(BLOB)
    sample_name = Column(Text)
    data_source_note = Column(Text)
    sequence_in_paper = Column(Integer)

    paper = relationship("Paper", back_populates="physical_parameters")
    compound = relationship("Compound", back_populates="physical_parameters")

    @staticmethod
    def _parse_range(value):
        try:
            parsed = json.loads(value) if value else None
        except Exception:
            return None
        if not isinstance(parsed, list):
            return None
        cleaned = []
        for item in parsed:
            if item is None:
                cleaned.append(None)
                continue
            try:
                cleaned.append(float(item))
            except (TypeError, ValueError):
                return None
        return cleaned[:2] if cleaned else None

    @staticmethod
    def _representative_value(values):
        if not values:
            return None
        numeric = [float(v) for v in values if v is not None]
        if not numeric:
            return None
        if len(numeric) == 1:
            return numeric[0]
        return sum(numeric[:2]) / min(len(numeric), 2)

    @property
    def tc_range(self):
        return self._parse_range(self.tc)

    @property
    def pressure_range(self):
        return self._parse_range(self.tc_press)

    @property
    def tc_value(self):
        return self._representative_value(self.tc_range)

    @property
    def pressure_value(self):
        return self._representative_value(self.pressure_range)

    def __repr__(self):
        return f"<PaperData paper_id={self.paper_id} compound_id={self.compound_id}>"


class PaperImage(ImageBase):
    """论文图片集合表，每行保存一篇论文最多40张图"""
    __tablename__ = "paper_images"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, index=True, nullable=False)
    figs = Column(Text)
    image_data = Column(BLOB)
    thumbnail_data = Column(BLOB)
    image_order = Column(Integer)
    file_size = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    fig1 = Column(BLOB)
    fig2 = Column(BLOB)
    fig3 = Column(BLOB)
    fig4 = Column(BLOB)
    fig5 = Column(BLOB)
    fig6 = Column(BLOB)
    fig7 = Column(BLOB)
    fig8 = Column(BLOB)
    fig9 = Column(BLOB)
    fig10 = Column(BLOB)
    fig11 = Column(BLOB)
    fig12 = Column(BLOB)
    fig13 = Column(BLOB)
    fig14 = Column(BLOB)
    fig15 = Column(BLOB)
    fig16 = Column(BLOB)
    fig17 = Column(BLOB)
    fig18 = Column(BLOB)
    fig19 = Column(BLOB)
    fig20 = Column(BLOB)
    fig21 = Column(BLOB)
    fig22 = Column(BLOB)
    fig23 = Column(BLOB)
    fig24 = Column(BLOB)
    fig25 = Column(BLOB)
    fig26 = Column(BLOB)
    fig27 = Column(BLOB)
    fig28 = Column(BLOB)
    fig29 = Column(BLOB)
    fig30 = Column(BLOB)
    fig31 = Column(BLOB)
    fig32 = Column(BLOB)
    fig33 = Column(BLOB)
    fig34 = Column(BLOB)
    fig35 = Column(BLOB)
    fig36 = Column(BLOB)
    fig37 = Column(BLOB)
    fig38 = Column(BLOB)
    fig39 = Column(BLOB)
    fig40 = Column(BLOB)

    def __repr__(self):
        return f"<PaperImage paper_id={self.paper_id}>"
