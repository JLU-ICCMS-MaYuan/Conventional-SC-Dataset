"""上传任务的纯状态规则、manifest 校验与公开 DTO。"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable
from uuid import uuid4


TASK_TTL = 24 * 60 * 60
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
RUNNING_STATUSES = {
    "uploading", "queued", "extracting", "reading", "summarizing",
    "submitting", "cancelling",
}
FIXED_TERMINAL_STATUSES = {"failed", "duplicate", "cancelled"}
FINAL_STATUSES = FIXED_TERMINAL_STATUSES | {"submitted"}
FILE_ROLES = {"main", "supplementary", "attachment"}
FILE_SUFFIXES = {".pdf", ".txt", ".md"}

PUBLIC_TASK_FIELDS = {
    "task_id", "status", "stage", "progress", "processing_status",
    "processing_error", "error_code", "created_at", "updated_at",
    "cleanup_at", "filename", "file_kind", "files", "revision",
    "duplicate", "existing_paper_id", "existing_paper_status", "allowed_actions",
    "duplicate_reason", "paper_id",
    "consistency", "completed_chunks", "total_chunks", "stage_index", "stage_total",
}
PUBLIC_FILE_FIELDS = {
    "file_id", "role", "original_filename", "media_type", "kind", "size",
    "sha256", "sort_order", "upload_status", "extraction_status", "error",
}


def apply_state_changes(
    state: dict[str, Any], *, now: int, **changes: Any,
) -> dict[str, Any]:
    """按状态机规则返回新快照；普通进度更新绝不续期。"""
    current = str(state.get("status") or "uploading")
    target = str(changes.get("status") or current)
    retrying_failed = current == "failed" and target == "queued" and bool(changes.pop("retry", False))
    if current in FINAL_STATUSES and target not in {current, "submitted"} and not retrying_failed:
        raise ValueError("终态任务不能恢复为运行状态")

    result = {**state, **changes, "updated_at": now}
    if target != current:
        result["revision"] = int(state.get("revision") or 0) + 1
        if target == "ready":
            result["last_user_activity_at"] = now
            result["cleanup_at"] = now + TASK_TTL
            result.pop("terminal_at", None)
        elif target in FIXED_TERMINAL_STATUSES:
            result["terminal_at"] = now
            result["cleanup_at"] = now + TASK_TTL
        elif target in RUNNING_STATUSES:
            result["cleanup_at"] = None
            result.pop("terminal_at", None)
        elif target == "submitted":
            result["cleanup_at"] = None
    return result


def apply_user_activity(state: dict[str, Any], *, now: int) -> dict[str, Any]:
    """只让 ready 的显式用户操作滑动续期。"""
    result = dict(state)
    result["updated_at"] = now
    if result.get("status") == "ready":
        result["last_user_activity_at"] = now
        result["cleanup_at"] = now + TASK_TTL
    return result


def validate_manifest(files: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """验证并标准化客户端声明的完整文件清单。"""
    normalized: list[dict[str, Any]] = []
    for index, item in enumerate(files):
        role = str(item.get("role") or "")
        filename = Path(str(item.get("filename") or "")).name
        size = int(item.get("size") or 0)
        if role not in FILE_ROLES:
            raise ValueError("文件角色不支持")
        if Path(filename).suffix.lower() not in FILE_SUFFIXES:
            raise ValueError("文件类型不支持")
        if size < 0 or size > MAX_UPLOAD_BYTES:
            raise ValueError("文件超过 50 MB 限制")
        normalized.append({
            "file_id": uuid4().hex,
            "client_id": str(item.get("client_id") or index),
            "role": role,
            "original_filename": filename,
            "media_type": item.get("media_type"),
            "kind": Path(filename).suffix.lower().lstrip("."),
            "size": size,
            "sort_order": index,
            "upload_status": "waiting",
            "extraction_status": "waiting",
            "error": None,
        })
    if sum(item["role"] == "main" for item in normalized) != 1:
        raise ValueError("文件清单必须恰好一个正文")
    return normalized


def public_task_state(state: dict[str, Any]) -> dict[str, Any]:
    """构造对外白名单 DTO，内部路径即使嵌套也不得透出。"""
    public = {key: state[key] for key in PUBLIC_TASK_FIELDS if key in state}
    public["files"] = [
        {key: item[key] for key in PUBLIC_FILE_FIELDS if key in item}
        for item in state.get("files") or []
        if isinstance(item, dict)
    ]
    return public


def compare_file_identities(identities: list[dict[str, Any]]) -> dict[str, Any]:
    """比较已提取的文件身份；缺失信息只标 unknown，明确冲突才 warning。"""
    main = next((item for item in identities if item.get("role") == "main"), None)
    if not main:
        return {"status": "unknown", "conflicts": []}
    conflicts: list[dict[str, Any]] = []
    comparable = False
    for item in identities:
        if item is main:
            continue
        for field in ("doi", "title", "authors"):
            left, right = main.get(field), item.get(field)
            if not left or not right:
                continue
            comparable = True
            normalize = lambda value: " ".join(str(value).lower().split())
            if normalize(left) != normalize(right):
                conflicts.append({
                    "file_id": item.get("file_id"), "field": field,
                    "main_value": left, "file_value": right,
                })
    return {"status": "warning" if conflicts else ("ok" if comparable else "unknown"), "conflicts": conflicts}
