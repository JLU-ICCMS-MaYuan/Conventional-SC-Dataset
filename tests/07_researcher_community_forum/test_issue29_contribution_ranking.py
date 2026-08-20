from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_community_page_contains_contribution_ranking_contract():
    source = (ROOT / "frontend/src/pages/share.tsx").read_text(encoding="utf-8")

    assert "/api/community/contributions" in source
    assert "?refresh=true" in source
    assert "60 * 60 * 1000" in source
    assert "贡献上传榜 Top 20" in source
    assert "贡献审核榜 Top 20" in source
    assert "我的排名" in source
    assert "暂无排名 · 0 篇" in source
    assert "暂无排名 · 0 次" in source
    assert "最后更新" in source


def test_admin_review_requests_send_idempotency_keys():
    source = (ROOT / "frontend/src/pages/AdminPage.tsx").read_text(encoding="utf-8")

    assert source.count("review_request_id: crypto.randomUUID()") >= 2


def test_review_event_migration_defines_history_and_backfill_contract():
    migration = (
        ROOT / "alembic/versions/20260820_0004_add_paper_review_events.py"
    ).read_text(encoding="utf-8")

    assert '"paper_review_events"' in migration
    assert 'sa.UniqueConstraint("request_id"' in migration
    assert "ck_paper_review_events_status" in migration
    assert "INSERT INTO paper_review_events" in migration
    assert "backfill-paper-" in migration
    assert "reviewed_by_user_id IS NOT NULL" in migration
