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

from backend.news.domain import CollectionError, Record
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
    spec = importlib.util.spec_from_file_location("news_migration", Path(__file__).parents[2] / "alembic/versions/20260831_0063_news_feed.py")
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as conn:
        with Operations.context(MigrationContext.configure(conn)):
            migration.upgrade()
    assert set(inspect(engine).get_table_names()) == {"news_feed_items", "news_feed_identities", "news_feed_sources"}
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
            if source == "physorg":
                return [Record(source=source, external_id="https://phys.org/news/test.html", kind="news",
                               title="Superconductivity recovery fixture", url="https://phys.org/news/test.html",
                               published_at="2026-08-30T00:00:00Z")]
            return [Record(source=source, external_id="10.1234/integration" if source == "crossref" else "2608.00001",
                           kind="journal_article" if source == "crossref" else "preprint",
                           title="Superconductivity integration fixture", url="https://doi.org/10.1234/integration",
                           doi="10.1234/integration", published_at="2026-08-30T00:00:00Z",
                           summary="Integration abstract" if source == "arxiv" else "",
                           summary_source="arxiv" if source == "arxiv" else "")]
    monkeypatch.setattr(backend.news.sources, "Sources", FixtureSources)
    upload = Queue("pdf-test-sentinel", connection=connection)
    upload.enqueue("builtins.len", [1, 2], job_id="pdf-sentinel")
    now = datetime.now(timezone.utc)
    assert enqueue_due(engine, connection, now) == ["arxiv", "crossref", "physorg"]
    assert enqueue_due(engine, connection, now) == []
    worker = Worker([QUEUE_NAME], connection=connection)
    worker.work(burst=True, logging_level="WARNING")
    with Session(engine) as db:
        assert len(db.scalars(select(NewsFeedItem)).all()) == 1
        assert db.get(NewsFeedSource, "physorg").status == "failed"
        assert db.get(NewsFeedSource, "arxiv").status == "success"
        assert db.execute(text("SELECT title FROM papers WHERE id=1")).scalar_one() == "untouched"
    assert upload.job_ids == ["pdf-sentinel"]
    assert enqueue_due(engine, connection, now + timedelta(hours=2)) == ["physorg"]
    fail_physorg = False
    worker.work(burst=True, logging_level="WARNING")
    assert upload.job_ids == ["pdf-sentinel"]
    with Session(engine) as db:
        assert db.get(NewsFeedSource, "physorg").status == "success"
        assert len(db.scalars(select(NewsFeedItem)).all()) == 2
    engine.dispose()
