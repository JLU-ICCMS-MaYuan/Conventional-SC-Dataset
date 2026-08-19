"""Redis-backed upload task and draft storage."""

from __future__ import annotations

import json
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from redis import Redis
from rq import Queue

from backend.rag.config import settings


TASK_TTL = settings.upload_task_ttl_seconds
QUEUE_NAME = "scwiki-upload"


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


def cleanup_upload_task(task_id: str, expected_updated_at: int) -> None:
    state = get_state(task_id)
    if state and int(state.get("updated_at", 0)) != int(expected_updated_at):
        upload_queue().enqueue_in(
            __import__("datetime").timedelta(seconds=TASK_TTL),
            cleanup_upload_task,
            task_id,
            int(state["updated_at"]),
        )
        return
    if not state or state.get("paper_id") is None:
        cleanup_task_files(task_id)


def schedule_cleanup(task_id: str) -> None:
    state = get_state(task_id)
    if state:
        upload_queue().enqueue_in(
            __import__("datetime").timedelta(seconds=TASK_TTL),
            cleanup_upload_task,
            task_id,
            int(state["updated_at"]),
        )
