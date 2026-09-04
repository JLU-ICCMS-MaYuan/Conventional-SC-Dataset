from datetime import datetime, timezone
from backend.news.scheduler import due, redis_connection, scheduled_at
from backend.news.models import NewsFeedSource
from backend.news.__main__ import run_worker


def test_daily_cutoff_and_recovery():
    now = datetime(2026, 8, 31, 1, tzinfo=timezone.utc)
    cutoff = scheduled_at(now, 8, "Asia/Shanghai")
    assert cutoff.isoformat() == "2026-08-31T00:00:00+00:00"
    assert due(None, cutoff, now)
    state = NewsFeedSource(source="arxiv", status="success",
                          last_success_at="2026-08-31T00:10:00Z",
                          last_started_at="", last_finished_at="")
    assert not due(state, cutoff, now)
    state.status = "failed"
    state.last_success_at = "2026-08-30T00:00:00Z"
    state.last_finished_at = "2026-08-31T00:30:00Z"
    assert not due(state, cutoff, now)
    state.last_finished_at = "2026-08-30T23:30:00Z"
    assert due(state, cutoff, now)
    state.status = "running"
    state.last_started_at = "2026-08-30T23:00:00Z"
    assert due(state, cutoff, now)


def test_worker_redis_connection_has_no_read_timeout(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    connection = redis_connection()
    assert connection.connection_pool.connection_kwargs["socket_timeout"] is None


def test_worker_restarts_after_rq_returns_from_idle_timeout():
    calls = []
    sleeps = []

    class FakeWorker:
        def __init__(self, queues, connection):
            calls.append((queues, connection))
            self._stop_requested = len(calls) > 1

        def work(self):
            return False

    run_worker(FakeWorker, connection_factory=lambda: object(), sleep=sleeps.append)

    assert len(calls) == 2
    assert sleeps == [5]
