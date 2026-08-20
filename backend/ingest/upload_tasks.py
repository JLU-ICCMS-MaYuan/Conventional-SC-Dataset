"""Redis-backed upload task and draft storage."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from redis import Redis
from rq import Queue
from sqlalchemy.exc import SQLAlchemyError

from backend.rag.config import settings


TASK_TTL = settings.upload_task_ttl_seconds
QUEUE_NAME = "scwiki-upload"
TASK_LOCK_TIMEOUT = 120


def redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def upload_queue() -> Queue:
    return Queue(QUEUE_NAME, connection=Redis.from_url(settings.redis_url))


def data_path(name: str) -> Path:
    path = settings.sc_wiki_data_dir / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def task_key(task_id: str) -> str:
    return f"upload:{task_id}:state"


def draft_key(task_id: str) -> str:
    return f"upload:{task_id}:draft"


def lock_key(task_id: str) -> str:
    return f"upload:{task_id}:lock"


@contextmanager
def upload_task_lock(task_id: str) -> Iterator[None]:
    """串行处理同一上传任务的提交和清理判断。"""
    lock = redis_client().lock(
        lock_key(task_id), timeout=TASK_LOCK_TIMEOUT, blocking_timeout=5,
    )
    if not lock.acquire():
        raise TimeoutError("上传任务正由其他请求处理")
    try:
        yield
    finally:
        try:
            lock.release()
        except Exception:
            # 锁超时只是兜底，不能覆盖已经完成的数据库提交或清理结果。
            pass


def create_task(user_id: int, filename: str, file_kind: str) -> dict[str, Any]:
    task_id = uuid.uuid4().hex
    now = int(time.time())
    state = {
        "task_id": task_id,
        "user_id": user_id,
        "filename": filename,
        "file_kind": file_kind,
        "stage": "saving_file",
        "stage_index": 1,
        "stage_total": 5,
        "processing_status": "processing",
        "processing_error": None,
        "completed_chunks": 0,
        "total_chunks": 0,
        "created_at": now,
        "updated_at": now,
    }
    save_state(task_id, state)
    return state


def get_state(task_id: str) -> dict[str, Any] | None:
    raw = redis_client().get(task_key(task_id))
    return json.loads(raw) if raw else None


def save_state(task_id: str, state: dict[str, Any]) -> dict[str, Any]:
    state["updated_at"] = int(time.time())
    redis_client().setex(task_key(task_id), TASK_TTL, json.dumps(state, ensure_ascii=False))
    return state


def update_state(task_id: str, **changes: Any) -> dict[str, Any]:
    state = get_state(task_id)
    if not state:
        raise KeyError("上传任务不存在或已过期")
    state.update(changes)
    return save_state(task_id, state)


def get_draft(task_id: str) -> dict[str, Any] | None:
    raw = redis_client().get(draft_key(task_id))
    return json.loads(raw) if raw else None


def save_draft(task_id: str, draft: dict[str, Any]) -> dict[str, Any]:
    client = redis_client()
    raw_state = client.get(task_key(task_id))
    if not raw_state:
        raise KeyError("上传任务不存在或已过期")
    state = json.loads(raw_state)
    state["updated_at"] = int(time.time())
    with client.pipeline(transaction=True) as pipeline:
        pipeline.setex(task_key(task_id), TASK_TTL, json.dumps(state, ensure_ascii=False))
        pipeline.setex(draft_key(task_id), TASK_TTL, json.dumps(draft, ensure_ascii=False))
        pipeline.execute()
    return draft


def task_directory(task_id: str) -> Path:
    path = data_path("upload_PDFs") / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def markdown_path(task_id: str) -> Path:
    return data_path("parsed_markdown") / f"{task_id}.md"


def artifact_directory(task_id: str) -> Path:
    path = data_path("review_artifacts") / task_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def artifact_path(task_id: str) -> Path:
    return artifact_directory(task_id) / "result.json"


def enqueue_processing(task_id: str) -> str:
    from backend.ingest.upload_jobs import process_upload_task

    job = upload_queue().enqueue(
        process_upload_task,
        task_id,
        job_timeout=-1,
        result_ttl=TASK_TTL,
        failure_ttl=TASK_TTL,
    )
    update_state(task_id, job_id=job.id, processing_status="processing", processing_error=None)
    return job.id


def cleanup_task_files(task_id: str) -> None:
    shutil.rmtree(data_path("upload_PDFs") / task_id, ignore_errors=True)
    shutil.rmtree(data_path("review_artifacts") / task_id, ignore_errors=True)
    markdown_path(task_id).unlink(missing_ok=True)
    client = redis_client()
    client.delete(task_key(task_id), draft_key(task_id))


def submitted_paper_id(task_id: str) -> int | None:
    """返回上传任务在数据库中的持久论文 ID。"""
    from sqlalchemy import select

    from backend.database import SessionLocal
    from backend.models import Paper

    prefix = f"upload_PDFs/{task_id}/%"
    with SessionLocal() as session:
        return session.scalar(select(Paper.id).where(Paper.source_file_path.like(prefix)))


def _enqueue_cleanup(task_id: str, expected_updated_at: int, delay: int = TASK_TTL) -> None:
    upload_queue().enqueue_in(
        __import__("datetime").timedelta(seconds=delay),
        cleanup_upload_task,
        task_id,
        expected_updated_at,
    )


def cleanup_upload_task(task_id: str, expected_updated_at: int) -> None:
    try:
        with upload_task_lock(task_id):
            state = get_state(task_id)
            if state and int(state.get("updated_at", 0)) != int(expected_updated_at):
                _enqueue_cleanup(task_id, int(state["updated_at"]))
                return
            if state and state.get("submission_status") == "submitting":
                _enqueue_cleanup(task_id, int(state["updated_at"]))
                return
            try:
                persisted_paper_id = submitted_paper_id(task_id)
            except SQLAlchemyError:
                # 数据库不可用时宁可延期，也不能冒险删除可能已提交的论文。
                _enqueue_cleanup(task_id, expected_updated_at, delay=60)
                return
            if (state and state.get("paper_id") is not None) or persisted_paper_id is not None:
                return
            cleanup_task_files(task_id)
    except TimeoutError:
        # 提交请求持有生命周期锁时延期，避免在事务执行中删除文件。
        _enqueue_cleanup(task_id, expected_updated_at, delay=60)


def schedule_cleanup(task_id: str) -> None:
    state = get_state(task_id)
    if state:
        _enqueue_cleanup(task_id, int(state["updated_at"]))
