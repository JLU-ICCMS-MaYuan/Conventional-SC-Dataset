from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_rankings_use_unique_username_not_role_or_real_name():
    source = (ROOT / "goserver/handlers/stats.go").read_text(encoding="utf-8")

    assert source.count("u.username AS username") >= 2
    ranking_section = source.split("func loadContributionSnapshot", 1)[1].split(
        "func contributionRankForUser", 1
    )[0]
    assert "u.role AS display_name" not in ranking_section
    assert "u.email AS display_name" not in ranking_section
    assert "u.real_name" not in ranking_section


def test_both_rankings_render_horizontal_contribution_bars():
    source = (ROOT / "frontend/src/pages/share.tsx").read_text(encoding="utf-8")

    assert "const contributionBarWidth" in source
    assert "Math.max(...rows.map" in source
    assert 'data-testid={`contribution-bar-${row.user_id}`}' in source
    assert "width: `${contributionBarWidth" in source
    assert source.count("renderLeaderboard(") == 2
    assert "flex: { xs: '1 1 100%', md: 1 }" in source
    assert "minWidth: { xs: 0, md: 280 }" in source
    assert "贡献上传榜 Top 20" in source
    assert "贡献审核榜 Top 20" in source


def test_personal_ranking_uses_one_responsive_row():
    source = (ROOT / "frontend/src/pages/share.tsx").read_text(encoding="utf-8")

    assert 'data-testid="current-user-ranking"' in source
    assert "flexWrap: { xs: 'wrap', md: 'nowrap' }" in source
    assert "flexShrink: 0" in source
    assert "width: '100%'" not in source.split(
        'data-testid="current-user-ranking"', 1
    )[1].split("</Box>", 1)[0]
