"""仅在显式提供独立 MySQL/Redis 地址时运行，不读取生产配置。"""
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from redis import Redis
from rq import Queue, Worker
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from backend.news.domain import CollectionError, Record, SOURCES
from backend.news.models import NewsFeedItem, NewsFeedSource
from backend.news.scheduler import QUEUE_NAME, enqueue_due

pytestmark = pytest.mark.skipif(not os.getenv("NEWS_TEST_MYSQL_URL") or not os.getenv("NEWS_TEST_REDIS_URL"),
                                reason="需要明确的隔离 MySQL 与 Redis 地址")


def test_mysql_migration_rq_worker_and_recovery(monkeypatch):
    url = make_url(os.environ["NEWS_TEST_MYSQL_URL"])
    assert (url.database == "news_test" or url.database.startswith("news_test_")) and url.host in ("127.0.0.1", "localhost")
    redis_url = os.environ["NEWS_TEST_REDIS_URL"]
    assert make_url(redis_url).host in ("127.0.0.1", "localhost")
    engine = create_engine(url, pool_pre_ping=True)
    connection = Redis.from_url(redis_url)
    assert connection.dbsize() == 0, "拒绝清空或占用非空 Redis；请启动新的测试实例"
    assert inspect(engine).get_table_names() == [], "拒绝迁移非空数据库"
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            for filename in ("20260831_0063_news_feed.py", "20260903_0003_networked_news_discovery.py"):
                spec = importlib.util.spec_from_file_location("news_migration", Path(__file__).parents[2] / "alembic/versions" / filename)
                migration = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(migration)
                migration.upgrade()
    assert set(inspect(engine).get_table_names()) == {"news_feed_items", "news_feed_identities", "news_feed_sources"}
    assert {"content_type", "display_kind", "discovery_source", "original_source", "relevance_evidence"} <= {
        column["name"] for column in inspect(engine).get_columns("news_feed_items")
    }
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE papers (id INTEGER PRIMARY KEY, title VARCHAR(100))"))
        conn.execute(text("INSERT INTO papers VALUES (1, 'untouched')"))
    import backend.database
    import backend.news.sources
    monkeypatch.setattr(backend.database, "engine", engine)
    monkeypatch.setenv("REDIS_URL", redis_url)
    class FakeTransport:
        def close(self):
            pass
    fail_physorg = True
    class FixtureSources:
        transport = FakeTransport()
        def __init__(self, **kwargs):
            pass
        def fetch(self, source, since, until):
            if source == "physorg" and fail_physorg:
                raise CollectionError("http_error")
            if source == "arxiv":
                kind, content_type, display_kind = "preprint", "preprint", "preprint"
            elif source in ("physorg", "google_news"):
                kind, content_type, display_kind = "news", "research_report", "journal_article"
                if source == "google_news":
                    content_type, display_kind = "social_industry", "news"
            else:
                kind, content_type, display_kind = "journal_article", "peer_reviewed", "journal_article"
            return [Record(
                source=source, external_id=f"fixture:{source}", kind=kind,
                title=f"Superconductivity integration fixture for {source}", url=f"https://example.org/{source}",
                published_at="2026-08-30T00:00:00Z", content_type=content_type, display_kind=display_kind,
                discovery_source=source, relevance_evidence="title: superconductivity",
                summary="Integration abstract" if source == "arxiv" else "",
                summary_source="arxiv" if source == "arxiv" else "",
            )]
    monkeypatch.setattr(backend.news.sources, "Sources", FixtureSources)
    upload = Queue("pdf-test-sentinel", connection=connection)
    upload.enqueue("builtins.len", [1, 2], job_id="pdf-sentinel")
    now = datetime.now(timezone.utc)
    assert enqueue_due(engine, connection, now) == list(SOURCES)
    assert enqueue_due(engine, connection, now) == []
    worker = Worker([QUEUE_NAME], connection=connection)
    worker.work(burst=True, logging_level="WARNING")
    with Session(engine) as db:
        assert db.get(NewsFeedSource, "physorg").status == "failed"
        assert db.get(NewsFeedSource, "arxiv").status == "success"
        assert db.get(NewsFeedSource, "openalex").status == "success"
        assert db.get(NewsFeedSource, "google_news").status == "success"
        assert db.execute(text("SELECT title FROM papers WHERE id=1")).scalar_one() == "untouched"
        assert len(db.scalars(select(NewsFeedItem)).all()) == len(SOURCES) - 1
    assert upload.job_ids == ["pdf-sentinel"]
    assert enqueue_due(engine, connection, now + timedelta(hours=2)) == ["physorg"]
    fail_physorg = False
    worker.work(burst=True, logging_level="WARNING")
    assert upload.job_ids == ["pdf-sentinel"]
    with Session(engine) as db:
        assert db.get(NewsFeedSource, "physorg").status == "success"
        assert len(db.scalars(select(NewsFeedItem)).all()) == len(SOURCES)
    engine.dispose()
