"""
PaperChunk — 论文文本块表。

每篇论文按语义边界切成若干块，每块存完整文本内容。
向量存在 Chroma 中，通过 paper_chunk_id 关联。
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.rag.database import Base


class PaperChunk(Base):
    __tablename__ = "paper_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("papers.id"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="块编号，从 0 开始")
    section_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="所属章节名，如 Introduction / Results / Methods"
    )
    heading: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="小节标题原文"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="块文本内容"
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="近似 token 数（按 4 字符/token 估算）"
    )

    def __repr__(self) -> str:
        return f"<PaperChunk id={self.id} paper_id={self.paper_id} #{self.chunk_index}>"
