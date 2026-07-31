"""
Paper — 论文表。

保存论文元信息、作者列表、上传审核信息。
authors 用 JSON 保存，不建立全局 authors 表（同名作者不一定是同一人）。
review_status 可选值: pending / approved / rejected / needs_revision。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.rag.database import Base


class Paper(Base):
    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doi: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True, comment="DOI 标识符"
    )
    title: Mapped[str | None] = mapped_column(Text, nullable=True, comment="论文标题")
    journal: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="期刊名称")
    volume: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="卷号")
    pages: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="页码")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="发表年份")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    authors: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="作者 JSON，保留顺序和单位："
        "[{'name': 'A. Smith', 'affiliation': 'University A'}]"
    )

    # ── RAG 增强字段 ────────────────────────────────────────────────────
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="AI 生成的结构化总结，用于 RAG 粗筛"
    )
    keywords_tags: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="关键词标签 JSON，如 ['LaH10', 'Fm-3m', '200 GPa']"
    )
    source_file_path: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="mineru/ 中的相对路径，用于追溯原始文件"
    )
    paper_type: Mapped[str | None] = mapped_column(
        String(20), nullable=True, comment="论文类型: theoretical / experimental / review / unknown"
    )

    # ── 审核字段 ────────────────────────────────────────────────────────
    uploaded_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, comment="上传者"
    )
    reviewed_by_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True, comment="审核者"
    )
    review_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending", comment="审核状态: pending / approved / rejected / needs_revision"
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, comment="审核时间")
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True, comment="审核意见")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now())

    records = relationship("SuperconductorRecord", back_populates="paper")
    key_properties = relationship("KeyProperty", back_populates="paper")

    def __repr__(self) -> str:
        return f"<Paper id={self.id} doi={self.doi}>"
