"""
ChemicalSystem — 元素体系表。

搜索入口。例如 H-La、H-S、Ba-Cu-O-Y。
system_key 内部按元素符号字母排序存储，保证唯一性。
用户输入 La-H 时，系统存储为 H-La。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag.database import Base


class ChemicalSystem(Base):
    __tablename__ = "chemical_systems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    system_key: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="体系键，元素符号字母排序后拼接，如 H-La"
    )
    elements_list: Mapped[str] = mapped_column(
        Text, nullable=False, comment="元素列表 JSON，如 ['H', 'La']"
    )
    element_count: Mapped[int] = mapped_column(Integer, nullable=False, comment="元素个数")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    superconductors = relationship("Superconductor", back_populates="chemical_system")

    def __repr__(self) -> str:
        return f"<ChemicalSystem {self.system_key}>"
