"""跨 Python/Go 共享的资讯表；不引用正式论文表。"""
from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from backend.database import Base


class NewsFeedItem(Base):
    __tablename__ = "news_feed_items"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text, default="")
    summary_source: Mapped[str] = mapped_column(String(16), default="")
    source: Mapped[str] = mapped_column(String(16))
    url: Mapped[str] = mapped_column(Text)
    doi: Mapped[str] = mapped_column(String(500), default="")
    arxiv_id: Mapped[str] = mapped_column(String(100), default="")
    version: Mapped[int] = mapped_column(Integer, default=0)
    authors: Mapped[str] = mapped_column(Text, default="[]")
    journal: Mapped[str] = mapped_column(Text, default="")
    links: Mapped[str] = mapped_column(Text, default="[]")
    published_at: Mapped[str] = mapped_column(String(20), default="")
    date_precision: Mapped[str] = mapped_column(String(10), default="unknown")
    source_updated_at: Mapped[str] = mapped_column(String(20), default="")
    content_type: Mapped[str] = mapped_column(String(24), default="")
    display_kind: Mapped[str] = mapped_column(String(24), default="")
    discovery_source: Mapped[str] = mapped_column(String(64), default="")
    original_source: Mapped[str] = mapped_column(String(64), default="")
    relevance_evidence: Mapped[str] = mapped_column(String(500), default="")
    first_seen_at: Mapped[str] = mapped_column(String(20))
    last_seen_at: Mapped[str] = mapped_column(String(20))
    __table_args__ = (
        Index("ix_news_feed_published", "published_at"),
        Index("ix_news_feed_kind_published", "kind", "published_at"),
    )


class NewsFeedIdentity(Base):
    __tablename__ = "news_feed_identities"
    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    item_id: Mapped[str] = mapped_column(ForeignKey("news_feed_items.id"), index=True)


class NewsFeedSource(Base):
    __tablename__ = "news_feed_sources"
    source: Mapped[str] = mapped_column(String(16), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    last_started_at: Mapped[str] = mapped_column(String(20), default="")
    last_finished_at: Mapped[str] = mapped_column(String(20), default="")
    last_success_at: Mapped[str] = mapped_column(String(20), default="")
    error_code: Mapped[str] = mapped_column(String(40), default="")
    fetched: Mapped[int] = mapped_column(Integer, default=0)
    accepted: Mapped[int] = mapped_column(Integer, default=0)
