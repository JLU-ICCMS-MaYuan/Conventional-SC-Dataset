"""
PeriodicTableElement — 周期表元素字典表。

这是一张参考表，不保存论文数据或超导数据。
元素的基本信息只维护一份，避免在业务数据中重复写周期表信息。
"""

from __future__ import annotations

from sqlalchemy import Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.rag.database import Base


class PeriodicTableElement(Base):
    __tablename__ = "periodic_table_elements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    atomic_number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, comment="原子序数")
    symbol: Mapped[str] = mapped_column(String(3), unique=True, nullable=False, comment="元素符号，如 H、La")
    english_name: Mapped[str] = mapped_column(String(30), nullable=False, comment="英文名称")
    chinese_name: Mapped[str] = mapped_column(String(10), nullable=False, comment="中文名称")
    atomic_mass: Mapped[float | None] = mapped_column(Float, nullable=True, comment="原子量")
    period_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="周期数")
    group_number: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="族数")
    category: Mapped[str | None] = mapped_column(String(30), nullable=True, comment="元素类别，如 alkali metal、transition metal")

    def __repr__(self) -> str:
        return f"<PeriodicTableElement {self.symbol} ({self.chinese_name})>"
