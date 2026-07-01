"""
User — 用户表。

网站用户、管理员和超级管理员。
使用单个 role 字段替代旧设计中的 is_admin + is_superadmin 两个布尔值。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.rag.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, comment="邮箱")
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码哈希")
    real_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="真实姓名")
    affiliation: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="所属单位")
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default="user", comment="角色: user / admin / superadmin"
    )
    is_approved: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否已批准")
    is_email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="邮箱是否已验证")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User {self.email} role={self.role}>"
