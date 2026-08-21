"""Canonical multi-file upload task API."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from backend.ingest.upload_contracts import (
    MAX_UPLOAD_BYTES,
    UPLOAD_STATE_SCHEMA_VERSION,
    public_task_state,
)
from backend.models import User
from backend.security import get_current_user


router = APIRouter(prefix="/api/upload-tasks", tags=["upload-tasks"])


class FileDeclaration(BaseModel):
    client_id: str
    role: Literal["main", "supplementary", "attachment"]
    filename: str
    size: int = Field(ge=0, le=MAX_UPLOAD_BYTES)
    media_type: str | None = None


class CreateUploadTask(BaseModel):
    files: list[FileDeclaration] = Field(min_length=1)


def _error(status: int, code: str, message: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, "message": message})


def _owned_state(task_id: str, user: User) -> dict[str, Any]:
    from backend.ingest.upload_tasks import get_state

    state = get_state(task_id)
    if not state:
        raise _error(404, "UPLOAD_TASK_NOT_FOUND", "上传任务不存在或已过期")
    is_admin = user.role in {"admin", "superadmin"} and user.is_approved
    if int(state.get("user_id") or 0) != user.id and not is_admin:
        raise _error(403, "UPLOAD_TASK_FORBIDDEN", "无权访问该上传任务")
    return state


def _versioned_public_state(state: dict[str, Any]) -> dict[str, Any]:
    try:
        version = int(state.get("state_schema_version") or 0)
    except (TypeError, ValueError):
        version = 0
    if version != UPLOAD_STATE_SCHEMA_VERSION:
        raise _error(
            409,
            "UPLOAD_STATE_VERSION_UNSUPPORTED",
            "上传任务由旧版 Worker 生成，请先执行状态迁移",
        )
    return public_task_state(state)


@router.post("")
def create_upload_task(
    body: CreateUploadTask,
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_tasks import create_task

    try:
        state = create_task(
            current_user.id,
            files=[item.model_dump() for item in body.files],
        )
    except ValueError as exc:
        message = str(exc)
        code = "ACTIVE_TASK_LIMIT_REACHED" if "100" in message else "INVALID_MANIFEST"
        raise _error(409 if code.startswith("ACTIVE") else 400, code, message) from exc
    return JSONResponse(status_code=201, content={"ok": True, "data": public_task_state(state)})


@router.get("")
def get_upload_tasks(
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_tasks import list_user_tasks

    return {
        "ok": True,
        "data": [_versioned_public_state(state) for state in list_user_tasks(current_user.id)],
    }


@router.get("/{task_id}")
def get_upload_task(
    task_id: str,
    touch: bool = Query(False),
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_tasks import touch_user_activity

    state = _owned_state(task_id, current_user)
    if touch:
        state = touch_user_activity(task_id)
    return {"ok": True, "data": _versioned_public_state(state)}


@router.post("/{task_id}/activity")
def record_upload_activity(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import touch_user_activity

    _owned_state(task_id, current_user)
    return {"ok": True, "data": public_task_state(touch_user_activity(task_id))}


@router.put("/{task_id}/files/{file_id}")
async def upload_task_file(
    task_id: str,
    file_id: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import sha256_file
    from backend.ingest.upload_tasks import (
        enqueue_processing,
        lock_uploaded_manifest,
        task_directory,
        update_state,
        update_task_file,
    )

    state = _owned_state(task_id, current_user)
    declared = next((item for item in state.get("files") or [] if item.get("file_id") == file_id), None)
    if not declared:
        raise _error(404, "UPLOAD_FILE_NOT_FOUND", "上传文件不存在")
    if declared.get("upload_status") == "completed":
        raise _error(409, "UPLOAD_FILE_ALREADY_COMPLETED", "该文件已经上传完成")

    suffix = Path(declared["original_filename"]).suffix.lower()
    destination = task_directory(task_id) / f"{file_id}{suffix}"
    total = 0
    try:
        with destination.open("wb") as stream:
            while chunk := await file.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise _error(413, "FILE_TOO_LARGE", "文件超过 50 MB 限制")
                stream.write(chunk)
        digest = sha256_file(destination)
        state = update_task_file(
            task_id,
            file_id,
            upload_status="completed",
            size=total,
            sha256=digest,
            stored_path=str(destination),
            source_file_path=f"upload_PDFs/{task_id}/{destination.name}",
        )
        if declared.get("role") == "main":
            state = update_state(
                task_id,
                filename=declared["original_filename"],
                file_kind=declared["kind"],
                file_path=str(destination),
                source_file_path=f"upload_PDFs/{task_id}/{destination.name}",
                file_size=total,
                file_sha256=digest,
            )
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    queued = False
    if all(item.get("upload_status") == "completed" for item in state.get("files") or []):
        state, queued = lock_uploaded_manifest(task_id)
        if queued:
            try:
                enqueue_processing(task_id)
            except Exception as exc:
                update_state(
                    task_id, status="failed", processing_status="failed",
                    error_code="upload_queue_unavailable", processing_error=str(exc),
                )
                raise _error(503, "UPLOAD_QUEUE_UNAVAILABLE", "文件已保存，但解析任务暂时无法启动") from exc
    return {"ok": True, "queued": queued, "data": public_task_state(state)}


@router.post("/{task_id}/finalize")
def finalize_upload_task(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import enqueue_processing, lock_uploaded_manifest

    _owned_state(task_id, current_user)
    try:
        state, queued = lock_uploaded_manifest(task_id)
    except ValueError as exc:
        raise _error(409, "UPLOAD_INCOMPLETE", str(exc)) from exc
    if queued:
        enqueue_processing(task_id)
    return {"ok": True, "queued": queued, "data": public_task_state(state)}


@router.post("/{task_id}/cancel")
def cancel_upload_task(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import schedule_cleanup, update_state

    state = _owned_state(task_id, current_user)
    if state.get("status") in {"cancelled", "submitted"}:
        return {"ok": True, "data": public_task_state(state)}
    if state.get("status") in {"uploading", "queued"}:
        state = update_state(
            task_id, status="cancelled", processing_status="cancelled",
            cancel_requested_at=state.get("updated_at"),
        )
        schedule_cleanup(task_id)
    else:
        state = update_state(task_id, status="cancelling", cancel_requested_at=state.get("updated_at"))
    return JSONResponse(status_code=202, content={"ok": True, "data": public_task_state(state)})


@router.get("/{task_id}/parsing")
def get_parsing_detail(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_jobs import public_parsing_detail

    _owned_state(task_id, current_user)
    return {"ok": True, "data": public_parsing_detail(task_id)}


@router.get("/{task_id}/chunks")
def get_parsing_chunks(
    task_id: str,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
):
    from backend.ingest.upload_jobs import public_parsing_detail

    _owned_state(task_id, current_user)
    detail = public_parsing_detail(task_id)
    chunks = detail.pop("chunks")
    return {
        "ok": True,
        "data": chunks[offset:offset + limit],
        "total": len(chunks),
        "revision": detail["revision"],
        "next_poll_ms": detail["next_poll_ms"],
    }


@router.post("/{task_id}/retry")
def retry_upload_task(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import enqueue_processing, update_state

    state = _owned_state(task_id, current_user)
    if state.get("status") != "failed":
        raise _error(409, "RETRY_NOT_ALLOWED", "只有失败任务可以重试")
    state = update_state(
        task_id, status="queued", retry=True, processing_status="processing",
        processing_error=None, error_code=None,
    )
    enqueue_processing(task_id)
    return JSONResponse(status_code=202, content={"ok": True, "data": public_task_state(state)})


@router.delete("/{task_id}")
def delete_upload_task(task_id: str, current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import cleanup_task_files, submitted_paper_id

    state = _owned_state(task_id, current_user)
    if state.get("status") not in {"failed", "duplicate", "cancelled"}:
        raise _error(409, "UPLOAD_TASK_NOT_CLEARABLE", "运行中或待校对任务不能直接清理")
    if submitted_paper_id(task_id) is not None:
        raise _error(409, "UPLOAD_TASK_PERSISTED", "任务已经生成正式论文，不能删除文件")
    cleanup_task_files(task_id)
    return {"ok": True}


@router.post("/cleanup")
def cleanup_upload_tasks(current_user: User = Depends(get_current_user)):
    from backend.ingest.upload_tasks import cleanup_task_files, get_state, list_user_tasks, submitted_paper_id

    deleted: list[str] = []
    skipped: list[str] = []
    deferred: list[str] = []
    for item in list_user_tasks(current_user.id):
        task_id = item["task_id"]
        state = get_state(task_id)
        if not state or state.get("status") not in {"failed", "duplicate", "cancelled"}:
            skipped.append(task_id)
            continue
        try:
            if submitted_paper_id(task_id) is not None:
                skipped.append(task_id)
                continue
        except Exception:
            deferred.append(task_id)
            continue
        cleanup_task_files(task_id)
        deleted.append(task_id)
    return {"ok": True, "deleted": deleted, "skipped": skipped, "deferred": deferred}
