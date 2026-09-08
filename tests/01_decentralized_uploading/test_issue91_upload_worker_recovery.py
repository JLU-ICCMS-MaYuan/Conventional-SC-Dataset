"""Issue #91: RQ 入口失败必须收敛上传状态，本地 Worker 必须刷新源码。"""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse

import pytest
from redis import Redis
from rq import Queue, SimpleWorker

from backend.ingest import upload_tasks
from backend.rq_runtime import run_worker_forever
from backend.scripts import run_upload_workers


REPO_ROOT = Path(__file__).parents[2]


def _job(task_id: object) -> SimpleNamespace:
    return SimpleNamespace(args=(task_id,))


def test_worker_failure_handler_marks_only_running_upload_tasks(monkeypatch):
    state = {
        "task_id": "a" * 32,
        "status": "queued",
        "stage": "queued",
        "processing_status": "processing",
    }
    updates = []
    scheduled = []
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: dict(state))
    monkeypatch.setattr(
        upload_tasks,
        "update_state",
        lambda task_id, **changes: updates.append((task_id, changes)) or {**state, **changes},
    )
    monkeypatch.setattr(upload_tasks, "schedule_cleanup", scheduled.append)

    fallthrough = upload_tasks.handle_upload_job_failure(
        _job(state["task_id"]), ImportError, ImportError("secret=/tmp/private"), None,
    )

    assert fallthrough is True
    assert updates == [(state["task_id"], {
        "status": "failed",
        "processing_status": "failed",
        "processing_error": "后台解析任务未能启动，请重新解析",
        "error_code": "upload_worker_execution_failed",
        "failed_stage": "queued",
        "partial_draft": None,
    })]
    assert "secret" not in updates[0][1]["processing_error"]
    assert scheduled == [state["task_id"]]


@pytest.mark.parametrize("task_id", [None, "not-a-task-id", 42])
def test_worker_failure_handler_ignores_invalid_jobs(monkeypatch, task_id):
    monkeypatch.setattr(
        upload_tasks,
        "get_state",
        lambda _task_id: pytest.fail("非法 job 不得查询上传任务"),
    )

    assert upload_tasks.handle_upload_job_failure(
        _job(task_id), ValueError, ValueError("broken"), None,
    ) is True


def test_worker_failure_handler_preserves_terminal_business_error(monkeypatch):
    state = {
        "task_id": "b" * 32,
        "status": "failed",
        "stage": "reading",
        "error_code": "paper_processing_failed",
        "processing_error": "第二段 LLM 失败",
    }
    monkeypatch.setattr(upload_tasks, "get_state", lambda _task_id: dict(state))
    monkeypatch.setattr(
        upload_tasks,
        "update_state",
        lambda *_args, **_kwargs: pytest.fail("既有终态不得被覆盖"),
    )
    monkeypatch.setattr(
        upload_tasks,
        "schedule_cleanup",
        lambda _task_id: pytest.fail("既有终态不得重复排程"),
    )

    assert upload_tasks.handle_upload_job_failure(
        _job(state["task_id"]), RuntimeError, RuntimeError("outer"), None,
    ) is True


def test_upload_worker_registers_queue_failure_handler(monkeypatch):
    captured = {}

    class FakeWorker:
        def __init__(self, _queues, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(run_upload_workers, "Worker", FakeWorker)
    monkeypatch.setattr(run_upload_workers.Redis, "from_url", lambda _url: object())
    monkeypatch.setattr(
        run_upload_workers,
        "run_worker_forever",
        lambda create_worker, _work, **_kwargs: create_worker(),
    )

    run_upload_workers._run_worker(with_scheduler=False)

    assert captured["exception_handlers"] == [upload_tasks.handle_upload_job_failure]


def test_worker_runtime_does_not_restart_after_idle_warm_shutdown():
    workers = []

    class FakeWorker:
        _stop_requested = False

        def __init__(self):
            self._shutdown_requested_date = object() if not workers else None
            self._stop_requested = bool(workers)
            workers.append(self)

    run_worker_forever(
        FakeWorker,
        lambda _worker: None,
        label="test worker",
        sleep=lambda _seconds: None,
    )

    assert len(workers) == 1


def test_local_dev_worker_is_supervised_by_python_file_watcher():
    script = (REPO_ROOT / "scripts/dev.sh").read_text(encoding="utf-8")

    assert '"$PY_BIN/watchfiles" --filter python --target-type command' in script
    assert 'worker_command=("$PY_BIN/python" -m backend.scripts.run_upload_workers)' in script
    assert '"${worker_command[*]}" "$REPO_ROOT/backend"' in script


def test_real_rq_import_failure_marks_task_failed(tmp_path, monkeypatch):
    redis_url = os.getenv("UPLOAD_TEST_REDIS_URL")
    if not redis_url:
        pytest.skip("需要明确的隔离 Redis 地址")
    parsed = urlparse(redis_url)
    assert parsed.hostname in {"127.0.0.1", "localhost"}
    assert parsed.path not in {"", "/", "/0"}, "拒绝使用默认 Redis DB"

    connection = Redis.from_url(redis_url, decode_responses=False)
    assert connection.dbsize() == 0, "拒绝清空或占用非空 Redis DB"
    task_id = "c" * 32
    queue_name = "scwiki-upload-issue91-test"
    state = {
        "task_id": task_id,
        "user_id": 1,
        "status": "queued",
        "stage": "queued",
        "processing_status": "processing",
        "revision": 1,
        "updated_at": 1,
        "state_schema_version": 1,
    }
    connection.set(upload_tasks.task_key(task_id), json.dumps(state, ensure_ascii=False))
    monkeypatch.setattr(upload_tasks.settings, "redis_url", redis_url)
    broken_module = tmp_path / "issue91_broken_entry.py"
    broken_module.write_text(
        "from issue91_dependency_that_does_not_exist import missing_symbol\n"
        "def process_upload_task(task_id):\n"
        "    raise AssertionError('业务入口不应执行')\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))

    try:
        queue = Queue(queue_name, connection=connection)
        job = queue.enqueue("issue91_broken_entry.process_upload_task", task_id)
        worker = SimpleWorker(
            [queue], connection=connection,
            exception_handlers=[upload_tasks.handle_upload_job_failure],
        )

        worker.work(burst=True, logging_level="WARNING")

        failed = upload_tasks.get_state(task_id)
        assert str(job.get_status(refresh=True)).endswith("FAILED")
        assert failed["status"] == "failed"
        assert failed["processing_status"] == "failed"
        assert failed["error_code"] == "upload_worker_execution_failed"
        assert failed["processing_error"] == "后台解析任务未能启动，请重新解析"
        assert failed["failed_stage"] == "queued"
    finally:
        connection.flushdb()
