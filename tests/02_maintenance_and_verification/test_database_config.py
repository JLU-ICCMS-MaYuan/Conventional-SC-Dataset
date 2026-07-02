import importlib
import sys
from pathlib import Path


MODULE_NAME = "backend.database"


def reload_database_module(monkeypatch, database_url=None):
    if database_url is None:
        monkeypatch.delenv("DATABASE_URL", raising=False)
    else:
        monkeypatch.setenv("DATABASE_URL", database_url)

    sys.modules.pop(MODULE_NAME, None)
    return importlib.import_module(MODULE_NAME)


def test_default_database_url_points_to_repo_dev_db(monkeypatch):
    database = reload_database_module(monkeypatch)

    expected_db_path = Path(__file__).resolve().parents[2] / "data" / "dev.db"

    assert database.DEFAULT_DATABASE_URL == f"sqlite:///{expected_db_path}"
    assert database.DATABASE_URL == database.DEFAULT_DATABASE_URL


def test_database_url_environment_variable_overrides_default(monkeypatch):
    override_url = "sqlite:///:memory:"

    database = reload_database_module(monkeypatch, override_url)

    assert database.DEFAULT_DATABASE_URL.endswith("/data/dev.db")
    assert database.DATABASE_URL == override_url
