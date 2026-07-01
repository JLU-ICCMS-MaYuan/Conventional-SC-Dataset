"""
Superconductor — 超导体表。

具体超导体或化合物，例如 LaH10、LaH6、H3S。
formula_normalized 按元素符号字母排序生成（如 LaH10 → H10La），保证唯一性。
是页面聚合对象：搜索 H-La 后，先展示 LaH10、LaH6 等化合物。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag.database import Base


class Superconductor(Base):
    __tablename__ = "superconductors"
    __table_args__ = (
        UniqueConstraint("chemical_system_id", "formula_normalized"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    chemical_system_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("chemical_systems.id"), nullable=False, comment="所属元素体系"
    )
    chemical_formula: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="原始化学式，如 LaH10"
    )
    formula_normalized: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="归一化化学式，元素符号字母排序，如 H10La"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="展示名称，可用于 HTML 下标渲染"
    )
    elements_list: Mapped[str] = mapped_column(
        Text, nullable=False, comment="元素列表 JSON，如 ['H', 'La']"
    )
    composition: Mapped[str] = mapped_column(
        Text, nullable=False, comment="元素组分 JSON，如 {'La': 1, 'H': 10}"
    )
    element_ratio: Mapped[str] = mapped_column(
        Text, nullable=False, comment="元素比例 JSON，如 {'La': 0.0909, 'H': 0.9091}"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    chemical_system = relationship("ChemicalSystem", back_populates="superconductors")
    records = relationship("SuperconductorRecord", back_populates="superconductor")

    def __repr__(self) -> str:
        return f"<Superconductor {self.display_name or self.chemical_formula}>"
