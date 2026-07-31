"""
KeyProperty — 通用物性记录表（v2 核心表，取代 SuperconductorRecord）。

源自 data/clean_results 的 key_properties：每行一条物性（Tc、λ、扩散系数…），
name 为规范物性名（backend/prop_names.py 归一），name_raw 保留原始写法，
范围值保真存 value_min/value_max，完整条件存 condition_json。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag.database import Base


class KeyProperty(Base):
    __tablename__ = "key_properties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── 归属 ────────────────────────────────────────────────────────────
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id"), nullable=False, index=True
    )
    superconductor_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("superconductors.id"), nullable=True, index=True,
        comment="材料可解析为化学式时关联；描述性名称（如 金属氢）为空",
    )
    material: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始材料名")

    # ── 物性名 ──────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="规范物性名，如 critical_temperature")
    name_raw: Mapped[str] = mapped_column(String(255), nullable=False, comment="LLM 原始物性名")
    name_note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # ── 数值（范围保真）────────────────────────────────────────────────
    value_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_max: Mapped[float | None] = mapped_column(Float, nullable=True)
    value_raw: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="无法解析为数值时的原始值")
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # ── 条件 ────────────────────────────────────────────────────────────
    pressure_gpa: Mapped[float | None] = mapped_column(Float, nullable=True, comment="condition.pressure (GPa)")
    temperature_k: Mapped[float | None] = mapped_column(Float, nullable=True, comment="condition.temperature (K)")
    condition_json: Mapped[str | None] = mapped_column(Text, nullable=True, comment="完整 condition 原样 JSON")
    condition_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── 分类与来源 ──────────────────────────────────────────────────────
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="论文主要物性")
    superconductor_type: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="规范全称: hydride/cuprate/…")
    article_type: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="e(实验) / t(理论)")
    source_label: Mapped[str] = mapped_column(String(50), nullable=False, default="clean_results")
    structure_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="CIF/POSCAR 结构文本")
    structure_format: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="cif / poscar / vasp")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    # ── 关系 ────────────────────────────────────────────────────────────
    superconductor = relationship("Superconductor", back_populates="key_properties")
    paper = relationship("Paper", back_populates="key_properties")

    def __repr__(self) -> str:
        return (
            f"<KeyProperty {self.material} {self.name}="
            f"{self.value_max}{self.unit or ''} P={self.pressure_gpa}GPa>"
        )
