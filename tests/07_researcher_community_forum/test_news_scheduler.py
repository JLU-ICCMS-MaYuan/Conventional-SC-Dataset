from datetime import datetime, timezone
from backend.news.scheduler import due, scheduled_at
from backend.news.models import NewsFeedSource


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
