"""Redis-backed upload task and draft storage."""

from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from redis import Redis
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job
from sqlalchemy.exc import SQLAlchemyError

from backend.rag.config import settings
from backend.ingest.upload_contracts import (
    FIXED_TERMINAL_STATUSES,
    RUNNING_STATUSES,
    CleanupContext,
    UPLOAD_STATE_SCHEMA_VERSION,
    apply_state_changes,
    apply_user_activity,
    public_task_state,
    validate_manifest,
)


TASK_TTL = settings.upload_task_ttl_seconds
QUEUE_NAME = "scwiki-upload"
TASK_LOCK_TIMEOUT = 120
ACTIVE_TASK_LIMIT = settings.upload_active_task_limit
TASK_ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")


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


def user_tasks_key(user_id: int) -> str:
    return f"upload:user:{user_id}:tasks"


def _encoded(state: dict[str, Any]) -> str:
    return json.dumps(state, ensure_ascii=False)


def _store_state(client: Redis, task_id: str, state: dict[str, Any]) -> None:
    cleanup_at = state.get("cleanup_at")
    if cleanup_at:
        ttl = max(1, int(cleanup_at) - int(time.time()))
        client.setex(task_key(task_id), ttl, _encoded(state))
    else:
        client.set(task_key(task_id), _encoded(state))


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


def create_task(
    user_id: int,
    filename: str | None = None,
    file_kind: str | None = None,
    *,
    files: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    task_id = uuid.uuid4().hex
    now = int(time.time())
    manifest = validate_manifest(files) if files is not None else []
    state = {
        "task_id": task_id,
        "user_id": user_id,
        "filename": filename or (manifest[0]["original_filename"] if manifest else ""),
        "file_kind": file_kind or (manifest[0]["kind"] if manifest else ""),
        "files": manifest,
        "status": "uploading",
        "stage": "saving_file",
        "stage_index": 1,
        "stage_total": 5,
        "processing_status": "processing",
        "processing_error": None,
        "completed_chunks": 0,
        "total_chunks": 0,
        "created_at": now,
        "updated_at": now,
        "last_progress_at": now,
        "cleanup_at": None,
        "revision": 1,
        "state_schema_version": UPLOAD_STATE_SCHEMA_VERSION,
    }
    client = redis_client()
    index_key = user_tasks_key(user_id)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(index_key)
                members = pipeline.zrange(index_key, 0, -1)
                existing = client.mget([task_key(item) for item in members]) if members else []
                stale = [item for item, raw in zip(members, existing) if not raw]
                if len(members) - len(stale) >= ACTIVE_TASK_LIMIT:
                    raise ValueError("活动上传任务已达到 100 个上限")
                pipeline.multi()
                if stale:
                    pipeline.zrem(index_key, *stale)
                pipeline.set(task_key(task_id), _encoded(state))
                pipeline.zadd(index_key, {task_id: now})
                pipeline.execute()
                break
            except Exception as exc:
                if exc.__class__.__name__ == "WatchError":
                    continue
                raise
    return state


def get_state(task_id: str) -> dict[str, Any] | None:
    raw = redis_client().get(task_key(task_id))
    return json.loads(raw) if raw else None


def save_state(task_id: str, state: dict[str, Any]) -> dict[str, Any]:
    state["updated_at"] = int(time.time())
    client = redis_client()
    _store_state(client, task_id, state)
    if state.get("user_id"):
        client.zadd(user_tasks_key(int(state["user_id"])), {task_id: state["updated_at"]})
    return state


def update_state(task_id: str, **changes: Any) -> dict[str, Any]:
    client = redis_client()
    key = task_key(task_id)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(key)
                raw = pipeline.get(key)
                if not raw:
                    raise KeyError("上传任务不存在或已过期")
                state = apply_state_changes(json.loads(raw), now=int(time.time()), **changes)
                pipeline.multi()
                cleanup_at = state.get("cleanup_at")
                if cleanup_at:
                    pipeline.setex(key, max(1, int(cleanup_at) - int(time.time())), _encoded(state))
                else:
                    pipeline.set(key, _encoded(state))
                if state.get("user_id"):
                    index_key = user_tasks_key(int(state["user_id"]))
                    if state.get("status") == "submitted":
                        pipeline.zrem(index_key, task_id)
                    else:
                        pipeline.zadd(index_key, {task_id: state["updated_at"]})
                pipeline.execute()
                return state
            except Exception as exc:
                if exc.__class__.__name__ == "WatchError":
                    continue
                raise


def list_user_tasks(user_id: int) -> list[dict[str, Any]]:
    """按最近活动返回用户任务，并顺手清除失效索引成员。"""
    client = redis_client()
    index_key = user_tasks_key(user_id)
    task_ids = client.zrevrange(index_key, 0, -1)
    raws = client.mget([task_key(item) for item in task_ids]) if task_ids else []
    stale = [task_id for task_id, raw in zip(task_ids, raws) if not raw]
    if stale:
        client.zrem(index_key, *stale)
    states: list[dict[str, Any]] = []
    now = int(time.time())
    for raw in raws:
        if not raw:
            continue
        state = json.loads(raw)
        if state.get("status") == "uploading" and now - int(
            state.get("last_progress_at") or state.get("updated_at") or now
        ) >= settings.upload_stale_seconds:
            state = update_state(
                state["task_id"], status="failed", processing_status="failed",
                error_code="upload_stalled", processing_error="上传连续 1 小时没有进度",
            )
            schedule_cleanup(state["task_id"])
        states.append(public_task_state(state))
    return states


def touch_user_activity(task_id: str) -> dict[str, Any]:
    client = redis_client()
    key = task_key(task_id)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(key)
                raw = pipeline.get(key)
                if not raw:
                    raise KeyError("上传任务不存在或已过期")
                state = apply_user_activity(json.loads(raw), now=int(time.time()))
                pipeline.multi()
                cleanup_at = state.get("cleanup_at")
                if cleanup_at:
                    pipeline.setex(key, max(1, int(cleanup_at) - int(time.time())), _encoded(state))
                else:
                    pipeline.set(key, _encoded(state))
                if state.get("user_id"):
                    pipeline.zadd(user_tasks_key(int(state["user_id"])), {task_id: state["updated_at"]})
                pipeline.execute()
                return state
            except Exception as exc:
                if exc.__class__.__name__ == "WatchError":
                    continue
                raise


def update_task_file(task_id: str, file_id: str, **changes: Any) -> dict[str, Any]:
    """原子更新一个 manifest 文件，避免并行上传相互覆盖。"""
    client = redis_client()
    key = task_key(task_id)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(key)
                raw = pipeline.get(key)
                if not raw:
                    raise KeyError("上传任务不存在或已过期")
                state = json.loads(raw)
                if state.get("status") != "uploading":
                    raise ValueError("文件清单已锁定")
                files = list(state.get("files") or [])
                target = next((item for item in files if item.get("file_id") == file_id), None)
                if target is None:
                    raise KeyError("上传文件不存在")
                candidate_hash = changes.get("sha256")
                if candidate_hash and any(
                    item is not target and item.get("sha256") == candidate_hash for item in files
                ):
                    raise ValueError("任务内存在内容完全相同的重复文件")
                target.update(changes)
                state = apply_state_changes(
                    state, now=int(time.time()), files=files, last_progress_at=int(time.time()),
                )
                pipeline.multi()
                pipeline.set(key, _encoded(state))
                pipeline.execute()
                return state
            except Exception as exc:
                if exc.__class__.__name__ == "WatchError":
                    continue
                raise


def lock_uploaded_manifest(task_id: str) -> tuple[dict[str, Any], bool]:
    """全部文件完成时只允许一个请求获得入队权。"""
    client = redis_client()
    key = task_key(task_id)
    while True:
        with client.pipeline(transaction=True) as pipeline:
            try:
                pipeline.watch(key)
                raw = pipeline.get(key)
                if not raw:
                    raise KeyError("上传任务不存在或已过期")
                state = json.loads(raw)
                if state.get("status") != "uploading":
                    return state, False
                if not state.get("files") or any(
                    item.get("upload_status") != "completed" for item in state["files"]
                ):
                    raise ValueError("仍有文件未上传完成")
                state = apply_state_changes(
                    state, now=int(time.time()), status="queued", stage="queued",
                    processing_status="processing",
                )
                pipeline.multi()
                pipeline.set(key, _encoded(state))
                pipeline.execute()
                return state, True
            except Exception as exc:
                if exc.__class__.__name__ == "WatchError":
                    continue
                raise


def get_draft(task_id: str) -> dict[str, Any] | None:
    raw = redis_client().get(draft_key(task_id))
    return json.loads(raw) if raw else None


def save_draft(task_id: str, draft: dict[str, Any]) -> dict[str, Any]:
    client = redis_client()
    raw_state = client.get(task_key(task_id))
    if not raw_state:
        raise KeyError("上传任务不存在或已过期")
    state = apply_user_activity(json.loads(raw_state), now=int(time.time()))
    ttl = max(1, int(state.get("cleanup_at") or (int(time.time()) + TASK_TTL)) - int(time.time()))
    with client.pipeline(transaction=True) as pipeline:
        pipeline.setex(task_key(task_id), ttl, _encoded(state))
        pipeline.setex(draft_key(task_id), ttl, json.dumps(draft, ensure_ascii=False))
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


def _validated_task_id(task_id: str) -> str:
    if not TASK_ID_PATTERN.fullmatch(task_id):
        raise ValueError("上传任务 ID 格式无效")
    return task_id


def _delete_processing_job(job_id: str) -> None:
    try:
        job = Job.fetch(job_id, connection=Redis.from_url(settings.redis_url))
    except NoSuchJobError:
        return
    job.delete()


def cleanup_transient_data(
    task_id: str,
    *,
    context: CleanupContext | None = None,
    preserve_review_snapshot: bool = False,
) -> None:
    """删除 Redis/RQ 和处理产物，可选择保留待审核快照。"""
    task_id = _validated_task_id(task_id)
    cleanup_context = context
    if cleanup_context is None:
        cleanup_context = CleanupContext.from_state(task_id, get_state(task_id) or {})
    if cleanup_context.task_id != task_id:
        raise ValueError("清理上下文与上传任务不匹配")

    artifact_root = data_path("review_artifacts") / task_id
    if artifact_root.is_dir():
        for child in artifact_root.iterdir():
            if preserve_review_snapshot and child.name == "result.json":
                continue
            if child.is_dir() and not child.is_symlink():
                shutil.rmtree(child, ignore_errors=True)
            else:
                child.unlink(missing_ok=True)
        try:
            artifact_root.rmdir()
        except OSError:
            pass

    if cleanup_context.processing_job_id:
        _delete_processing_job(cleanup_context.processing_job_id)
    client = redis_client()
    client.delete(task_key(task_id), draft_key(task_id))
    if cleanup_context.user_id is not None:
        client.zrem(user_tasks_key(cleanup_context.user_id), task_id)


def cleanup_unsubmitted_files(task_id: str) -> None:
    """删除未提交任务的上传文件和两类 Markdown 布局。"""
    task_id = _validated_task_id(task_id)
    shutil.rmtree(data_path("upload_PDFs") / task_id, ignore_errors=True)
    markdown_root = data_path("parsed_markdown")
    (markdown_root / f"{task_id}.md").unlink(missing_ok=True)
    shutil.rmtree(markdown_root / task_id, ignore_errors=True)


def cleanup_duplicate_candidate(task_id: str, existing_paper_id: int | None) -> None:
    """删除某个 duplicate 任务生成的候选文件，不影响同论文其他候选。"""
    task_id = _validated_task_id(task_id)
    if existing_paper_id is None:
        return
    paper_id = int(existing_paper_id)
    if paper_id <= 0:
        raise ValueError("已有论文 ID 格式无效")
    root = data_path("upload_PDFs") / "candidates" / str(paper_id)
    if not root.is_dir():
        return
    for candidate in root.glob(f"{task_id}.*"):
        if candidate.is_file() or candidate.is_symlink():
            candidate.unlink(missing_ok=True)
    try:
        root.rmdir()
    except OSError:
        pass


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
    """兼容旧调用方；新代码应按场景组合三个清理原语。"""
    state = get_state(task_id) or {}
    context = CleanupContext.from_state(task_id, state)
    cleanup_transient_data(task_id, context=context, preserve_review_snapshot=False)
    cleanup_unsubmitted_files(task_id)
    cleanup_duplicate_candidate(task_id, context.existing_paper_id)


def submitted_paper_id(task_id: str) -> int | None:
    """返回上传任务在数据库中的持久论文 ID。"""
    from sqlalchemy import select

    from backend.database import SessionLocal
    from backend.models import Paper

    with SessionLocal() as session:
        if hasattr(Paper, "upload_task_id"):
            paper_id = session.scalar(select(Paper.id).where(Paper.upload_task_id == task_id))
            if paper_id is not None:
                return paper_id
        if hasattr(Paper, "source_file_path"):
            prefix = f"upload_PDFs/{task_id}/%"
            return session.scalar(select(Paper.id).where(Paper.source_file_path.like(prefix)))
        return None


def _enqueue_cleanup(context: CleanupContext, delay: int = TASK_TTL) -> None:
    upload_queue().enqueue_in(
        __import__("datetime").timedelta(seconds=delay),
        cleanup_upload_task,
        context,
    )


def _cleanup_context(
    context_or_task_id: CleanupContext | dict[str, Any] | str,
    expected_updated_at: int | None,
) -> CleanupContext:
    if isinstance(context_or_task_id, CleanupContext):
        return context_or_task_id
    if isinstance(context_or_task_id, dict):
        return CleanupContext(**context_or_task_id)
    task_id = _validated_task_id(context_or_task_id)
    state = get_state(task_id) or {"updated_at": expected_updated_at or 0}
    return CleanupContext.from_state(task_id, state)


def cleanup_upload_task(
    context_or_task_id: CleanupContext | dict[str, Any] | str,
    expected_updated_at: int | None = None,
) -> None:
    context = _cleanup_context(context_or_task_id, expected_updated_at)
    task_id = context.task_id
    try:
        with upload_task_lock(task_id):
            state = get_state(task_id)
            if state and int(state.get("updated_at", 0)) != context.expected_updated_at:
                cleanup_at = state.get("cleanup_at")
                if cleanup_at:
                    _enqueue_cleanup(
                        CleanupContext.from_state(task_id, state),
                        delay=max(1, int(cleanup_at) - int(time.time())),
                    )
                return
            if state and (
                state.get("status") in RUNNING_STATUSES
                or state.get("submission_status") == "submitting"
            ):
                if state.get("submission_status") == "submitting" and not state.get("status"):
                    _enqueue_cleanup(CleanupContext.from_state(task_id, state))
                return
            try:
                persisted_paper_id = submitted_paper_id(task_id)
            except SQLAlchemyError:
                # 数据库不可用时宁可延期，也不能冒险删除可能已提交的论文。
                _enqueue_cleanup(context, delay=60)
                return
            if (state and state.get("paper_id") is not None) or persisted_paper_id is not None:
                cleanup_transient_data(
                    task_id,
                    context=context,
                    preserve_review_snapshot=True,
                )
                return
            cleanup_transient_data(
                task_id,
                context=context,
                preserve_review_snapshot=False,
            )
            cleanup_unsubmitted_files(task_id)
            cleanup_duplicate_candidate(task_id, context.existing_paper_id)
    except TimeoutError:
        # 提交请求持有生命周期锁时延期，避免在事务执行中删除文件。
        _enqueue_cleanup(context, delay=60)


def schedule_cleanup(task_id: str) -> None:
    state = get_state(task_id)
    if state and state.get("cleanup_at"):
        _enqueue_cleanup(
            CleanupContext.from_state(task_id, state),
            delay=max(1, int(state["cleanup_at"]) - int(time.time())),
        )
