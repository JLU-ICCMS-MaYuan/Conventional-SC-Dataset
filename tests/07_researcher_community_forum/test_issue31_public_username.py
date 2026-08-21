from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_username_migration_backfills_private_random_identifiers():
    source = (
        ROOT / "alembic/versions/20260821_0006_add_public_usernames.py"
    ).read_text(encoding="utf-8")

    assert 'revision = "20260821_0006"' in source
    assert 'down_revision = "20260820_0005"' in source
    assert '"username"' in source
    assert 'collation="ascii_bin"' in source
    assert "secrets.choice" in source
    assert '"sc_"' in source
    assert '"username_change_allowed"' in source
    assert '"username_change_audit_events"' in source
    assert 'unique=True' in source


def test_models_define_username_and_immutable_audit_contract():
    python_models = (ROOT / "backend/models.py").read_text(encoding="utf-8")
    go_models = (ROOT / "goserver/models/models.go").read_text(encoding="utf-8")

    for source in (python_models, go_models):
        assert "Username" in source or "username" in source
        assert "UsernameChangeAllowed" in source or "username_change_allowed" in source
        assert "UsernameChangeAuditEvent" in source


def test_auth_and_account_ui_use_username_without_displaying_real_name():
    auth = (ROOT / "frontend/src/context/AuthContext.tsx").read_text(encoding="utf-8")
    shell = (ROOT / "frontend/src/components/AppShell.tsx").read_text(encoding="utf-8")
    admin = (ROOT / "frontend/src/pages/AdminPage.tsx").read_text(encoding="utf-8")

    assert "username: string" in auth
    assert "username_change_allowed" in auth
    assert "username-availability" in (ROOT / "frontend/src/lib/username.ts").read_text(encoding="utf-8")
    assert "user.username" in shell
    assert "minmax(0, 1fr)" in shell
    assert "boxSizing: 'border-box'" in shell
    assert "u.username" in admin
    assert "replaceUser(result.user)" in admin
    assert "real_name" not in shell
    assert "real_name" not in admin


def test_go_routes_expose_username_workflows():
    routes = (ROOT / "goserver/main.go").read_text(encoding="utf-8")

    assert '"/api/auth/username-availability"' in routes
    assert '"/auth/username"' in routes
    assert '"/users/:id/username"' in routes
    assert '"/username-audit-events"' in routes


def test_contribution_api_uses_username_as_authoritative_identity():
    handler = (ROOT / "goserver/handlers/stats.go").read_text(encoding="utf-8")
    page = (ROOT / "frontend/src/pages/share.tsx").read_text(encoding="utf-8")

    ranking_loader = handler.split("func loadContributionSnapshot", 1)[1].split(
        "func contributionRankForUser", 1
    )[0]
    assert ranking_loader.count("u.username") >= 4
    assert "u.real_name" not in ranking_loader
    assert 'Username' in handler and 'json:"username"' in handler
    assert "row.username" in page
