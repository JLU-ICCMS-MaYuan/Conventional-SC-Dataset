from pathlib import Path
import re


COMPOSE_PATH = Path(__file__).parents[2] / "docker" / "compose.yaml"
DEV_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "dev.sh"


def service_block(compose: str, name: str) -> str:
    marker = f"  {name}:\n"
    start = compose.index(marker)
    next_service = re.search(r"^  [a-z][a-z0-9-]*:\n", compose[start + len(marker):], re.MULTILINE)
    return compose[start:] if next_service is None else compose[start:start + len(marker) + next_service.start()]


def test_news_services_are_started_separately_from_upload_worker():
    compose = COMPOSE_PATH.read_text()
    scheduler = service_block(compose, "news-scheduler")
    worker = service_block(compose, "news-worker")
    upload_worker = service_block(compose, "worker")

    assert 'image: mayuanmark/scwiki-python:mayuan' in scheduler
    assert 'command: ["python", "-m", "backend.news", "schedule"]' in scheduler
    assert 'command: ["python", "-m", "backend.news", "worker"]' in worker
    assert 'command: ["python", "-m", "backend.scripts.run_upload_workers"]' in upload_worker

    for block in (scheduler, worker):
        for value in (
            'DATABASE_URL: ${DATABASE_URL}',
            'REDIS_URL: redis://redis:6379/0',
            'NEWS_DAILY_HOUR: "8"',
            'NEWS_TIMEZONE: Asia/Shanghai',
            'NEWS_INITIAL_DAYS: "7"',
            'NEWS_MAX_PAGES: "100"',
            'condition: service_completed_successfully',
            'condition: service_healthy',
            'restart: unless-stopped',
        ):
            assert value in block


def test_local_dev_starts_news_processes_by_default():
    dev_script = DEV_SCRIPT_PATH.read_text()

    assert "APP_SERVICES=(python worker news-worker news-scheduler goserver frontend)" in dev_script
    assert 'spawn worker env UPLOAD_LLM_CONCURRENCY=1' in dev_script
    assert '"$PY_BIN/python" -m backend.scripts.run_upload_workers' in dev_script
    assert 'spawn news-worker "$PY_BIN/python" -m backend.news worker' in dev_script
    assert 'spawn news-scheduler "$PY_BIN/python" -m backend.news schedule' in dev_script
