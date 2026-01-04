"""
数据库模型定义
"""
from sqlalchemy import Column, Integer, String, Text, BLOB, DateTime, ForeignKey, UniqueConstraint, Boolean, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.database import Base
import datetime


class Element(Base):
    """元素表 - 存储118个化学元素"""
    __tablename__ = "elements"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(3), unique=True, nullable=False, index=True)  # 元素符号，如 "Cu"
    name = Column(String(50), nullable=False)  # 英文名，如 "Copper"
    name_zh = Column(String(50))  # 中文名，如 "铜"
    atomic_number = Column(Integer, unique=True, nullable=False)  # 原子序数

    # 关系
    compound_elements = relationship("CompoundElement", back_populates="element")

    def __repr__(self):
        return f"<Element {self.symbol} ({self.name})>"


class Compound(Base):
    """元素组合表 - 存储元素组合（如Y-Ba-Cu-O系统）"""
    __tablename__ = "compounds"

    id = Column(Integer, primary_key=True, index=True)
    element_symbols = Column(String(200), unique=True, nullable=False, index=True)  # 如 "Ba-Cu-O-Y"（按字母排序）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    papers = relationship("Paper", back_populates="compound", cascade="all, delete-orphan")
    compound_elements = relationship("CompoundElement", back_populates="compound", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Compound {self.element_symbols}>"


class User(Base):
    """用户/管理员表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(200), unique=True, nullable=False, index=True)  # 邮箱（登录账号）
    password_hash = Column(String(200), nullable=False)  # 密码哈希
    real_name = Column(String(100), nullable=False)  # 真实姓名

    # 管理员权限
    is_admin = Column(Boolean, default=False)  # 是否为管理员
    is_superadmin = Column(Boolean, default=False)  # 是否为超级管理员
    is_approved = Column(Boolean, default=False)  # 是否已被超级管理员批准

    # 邮箱验证
    is_email_verified = Column(Boolean, default=False)  # 邮箱是否已验证
    verification_code = Column(String(10))  # 验证码
    verification_expires = Column(DateTime)  # 验证码过期时间

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    approved_at = Column(DateTime)  # 批准时间
    approved_by = Column(Integer, ForeignKey("users.id"))  # 批准人ID

    # 关系
    reviewed_papers = relationship("Paper", back_populates="reviewer", foreign_keys="Paper.reviewed_by")

    def __repr__(self):
        return f"<User {self.email} ({self.real_name})>"


class Paper(Base):
    """文献表 - 存储超导文献信息"""
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True, index=True)
    compound_id = Column(Integer, ForeignKey("compounds.id"), nullable=False, index=True)
    doi = Column(String(200), nullable=False, index=True)  # DOI标识符
    title = Column(Text, nullable=False)  # 文章标题
    authors = Column(Text)  # 作者列表（JSON格式）
    journal = Column(String(200))  # 期刊名称
    volume = Column(String(50))  # 卷号
    pages = Column(String(50))  # 页码
    year = Column(Integer, index=True)  # 发表年份
    abstract = Column(Text)  # 摘要
    citation_aps = Column(Text)  # APS引用格式
    citation_bibtex = Column(Text)  # BibTeX引用格式

    # 用户必填的分类字段
    article_type = Column(String(20), nullable=False)  # 文章类型: 'theoretical' 或 'experimental'
    superconductor_type = Column(String(20), nullable=False)  # 超导体类型: 'conventional', 'unconventional', 'unknown'

    # 用户可选填写的字段
    chemical_formula = Column(String(200))  # 化学式，如 "YBa₂Cu₃O₇"
    crystal_structure = Column(String(200))  # 晶体结构类型，如 "钙钛矿型"
    contributor_name = Column(String(100), default="匿名贡献者")  # 贡献者姓名
    contributor_affiliation = Column(String(200), default="未提供单位")  # 贡献者单位
    notes = Column(Text)  # 备注说明

    # 审核相关字段
    review_status = Column(String(20), default="unreviewed", nullable=False, index=True)  # 审核状态: 'reviewed' 或 'unreviewed'
    reviewed_by = Column(Integer, ForeignKey("users.id"))  # 审核人ID
    reviewed_at = Column(DateTime)  # 审核时间

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    compound = relationship("Compound", back_populates="papers")
    data = relationship("PaperData", back_populates="paper", cascade="all, delete-orphan")
    images = relationship("PaperImage", back_populates="paper", cascade="all, delete-orphan")
    reviewer = relationship("User", back_populates="reviewed_papers", foreign_keys=[reviewed_by])

    # 唯一约束：同一元素组合不能有重复的DOI
    __table_args__ = (
        UniqueConstraint('compound_id', 'doi', name='uix_compound_doi'),
    )

    def __repr__(self):
        return f"<Paper {self.doi}>"

class PaperData(Base):
    __tablename__ = "paper_data"
    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    pressure = Column(Float)  # 压强 (GPa)
    tc = Column(Float)        # 超导温度 Tc (K)
    lambda_val = Column(Float) # λ (lambda)
    omega_log = Column(Float)  # ω_log
    n_ef = Column(Float)       # N(E_F)
    # 关系
    paper = relationship("Paper", back_populates="data")
    def __repr__(self):
        return f"<PaperData paper_id={self.paper_id} P={self.pressure} Tc={self.tc}>"

class PaperImage(Base):
    """文献截图表 - 存储文献相关的图片"""
    __tablename__ = "paper_images"

    id = Column(Integer, primary_key=True, index=True)
    paper_id = Column(Integer, ForeignKey("papers.id", ondelete="CASCADE"), nullable=False, index=True)
    image_data = Column(BLOB, nullable=False)  # 原图二进制数据
    thumbnail_data = Column(BLOB, nullable=False)  # 缩略图二进制数据
    image_order = Column(Integer, nullable=False)  # 图片顺序（1-5）
    file_size = Column(Integer)  # 文件大小（字节）
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    paper = relationship("Paper", back_populates="images")

    def __repr__(self):
        return f"<PaperImage paper_id={self.paper_id} order={self.image_order}>"


class CompoundElement(Base):
    """元素组合-元素关联表 - 多对多关系"""
    __tablename__ = "compound_elements"

    id = Column(Integer, primary_key=True, index=True)
    compound_id = Column(Integer, ForeignKey("compounds.id", ondelete="CASCADE"), nullable=False, index=True)
    element_id = Column(Integer, ForeignKey("elements.id"), nullable=False, index=True)

    # 关系
    compound = relationship("Compound", back_populates="compound_elements")
    element = relationship("Element", back_populates="compound_elements")

    # 唯一约束：同一元素组合不能有重复元素
    __table_args__ = (
        UniqueConstraint('compound_id', 'element_id', name='uix_compound_element'),
    )

    def __repr__(self):
        return f"<CompoundElement compound_id={self.compound_id} element_id={self.element_id}>"
