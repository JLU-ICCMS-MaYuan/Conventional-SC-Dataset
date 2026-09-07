"""上传任务的纯状态规则、manifest 校验与公开 DTO。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

UPLOAD_STATE_SCHEMA_VERSION = 1
TASK_TTL = 24 * 60 * 60
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
RUNNING_STATUSES = {"uploading", "queued", "extracting", "reading", "summarizing", "submitting", "cancelling"}
FIXED_TERMINAL_STATUSES = {"failed", "duplicate", "cancelled"}
FINAL_STATUSES = FIXED_TERMINAL_STATUSES | {"submitted"}
FILE_ROLES = {"main", "supplementary", "attachment"}
FILE_SUFFIXES = {".pdf", ".txt", ".md", ".cif", ".poscar", ".vasp"}
PUBLIC_TASK_FIELDS = {"task_id", "status", "stage", "progress", "processing_status", "processing_error", "error_code", "created_at", "updated_at", "cleanup_at", "filename", "file_kind", "files", "revision", "state_schema_version", "duplicate", "existing_paper_id", "existing_paper_status", "allowed_actions", "duplicate_reason", "paper_id", "llm_provider", "consistency", "completed_chunks", "total_chunks", "stage_index", "stage_total"}
PUBLIC_FILE_FIELDS = {"file_id", "role", "original_filename", "media_type", "kind", "size", "sha256", "sort_order", "upload_status", "extraction_status", "error"}

@dataclass(frozen=True)
class CleanupContext:
    task_id: str
    user_id: int | None
    processing_job_id: str | None
    existing_paper_id: int | None
    expected_updated_at: int
    state_schema_version: int

    @classmethod
    def from_state(cls, task_id: str, state: dict[str, Any]) -> "CleanupContext":
        return cls(task_id, int(state["user_id"]) if state.get("user_id") is not None else None, str(state.get("job_id") or "") or None, int(state["existing_paper_id"]) if state.get("existing_paper_id") is not None else None, int(state.get("updated_at") or 0), int(state.get("state_schema_version") or 0))

def apply_state_changes(state: dict[str, Any], *, now: int, **changes: Any) -> dict[str, Any]:
    current = str(state.get("status") or "uploading")
    target = str(changes.get("status") or current)
    retrying_failed = current == "failed" and target == "queued" and bool(changes.pop("retry", False))
    if current in FINAL_STATUSES and target not in {current, "submitted"} and not retrying_failed:
        raise ValueError("终态任务不能恢复为运行状态")
    result = {**state, **changes, "updated_at": now}
    if target != current:
        result["revision"] = int(state.get("revision") or 0) + 1
        if target == "ready":
            result["last_user_activity_at"] = now; result["cleanup_at"] = now + TASK_TTL; result.pop("terminal_at", None)
        elif target in FIXED_TERMINAL_STATUSES:
            result["terminal_at"] = now; result["cleanup_at"] = now + TASK_TTL
        elif target in RUNNING_STATUSES:
            result["cleanup_at"] = None; result.pop("terminal_at", None)
        elif target == "submitted": result["cleanup_at"] = None
    return result

def apply_user_activity(state: dict[str, Any], *, now: int) -> dict[str, Any]:
    result = dict(state); result["updated_at"] = now
    if result.get("status") == "ready": result["last_user_activity_at"] = now; result["cleanup_at"] = now + TASK_TTL
    return result

def structure_format_for_filename(filename: str) -> str | None:
    path = Path(filename)
    if path.name.upper() in {"POSCAR", "CONTCAR"} or path.suffix.lower() in {".poscar", ".vasp"}: return "poscar"
    if path.suffix.lower() == ".cif": return "cif"
    return None

def validate_manifest(files: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for index, item in enumerate(files):
        role = str(item.get("role") or ""); filename = Path(str(item.get("filename") or "")).name; size = int(item.get("size") or 0)
        if role not in FILE_ROLES: raise ValueError("文件角色不支持")
        suffix = Path(filename).suffix.lower(); structure_format = structure_format_for_filename(filename)
        if suffix not in FILE_SUFFIXES and structure_format is None: raise ValueError("文件类型不支持")
        if size < 0 or size > MAX_UPLOAD_BYTES: raise ValueError("文件超过 50 MB 限制")
        normalized.append({"file_id": uuid4().hex, "client_id": str(item.get("client_id") or index), "role": role, "original_filename": filename, "media_type": item.get("media_type"), "kind": structure_format or suffix.lstrip("."), "size": size, "sort_order": index, "upload_status": "waiting", "extraction_status": "waiting", "error": None})
    if sum(item["role"] == "main" for item in normalized) != 1: raise ValueError("文件清单必须恰好一个正文")
    return normalized

def public_task_state(state: dict[str, Any]) -> dict[str, Any]:
    public = {key: state[key] for key in PUBLIC_TASK_FIELDS if key in state}
    public["files"] = [{key: item[key] for key in PUBLIC_FILE_FIELDS if key in item} for item in state.get("files") or [] if isinstance(item, dict)]
    return public

def compare_file_identities(identities: list[dict[str, Any]]) -> dict[str, Any]:
    main = next((item for item in identities if item.get("role") == "main"), None)
    if not main: return {"status": "unknown", "conflicts": []}
    conflicts = []; comparable = False
    for item in identities:
        if item is main: continue
        for field in ("doi", "title", "authors"):
            left, right = main.get(field), item.get(field)
            if not left or not right: continue
            comparable = True
            if " ".join(str(left).lower().split()) != " ".join(str(right).lower().split()): conflicts.append({"file_id": item.get("file_id"), "field": field, "main_value": left, "file_value": right})
    return {"status": "warning" if conflicts else ("ok" if comparable else "unknown"), "conflicts": conflicts}


class UploadContractError(ValueError):
    def __init__(self, code: str, message: str, field: str | None = None):
        self.code, self.field = code, field
        super().__init__(message)

    def as_detail(self) -> dict[str, Any]:
        issue = {"field": self.field or "", "code": self.code, "message": str(self)}
        return {"detail": "科学数据校验失败", "issues": [issue]}


class PropertyRecordInput(BaseModel):
    record_key: str
    module_code: str
    record_type: Literal["predicted_tc", "measured_tc", "property"] = "property"
    property_code: str
    definition_key: str
    definition_version: int = Field(ge=1)
    name_raw: str
    value_kind: Literal["number", "range", "text", "boolean"]
    value_raw: str
    payload: dict[str, Any] = Field(default_factory=dict)
    is_representative: bool = False


class PropertyModuleInput(BaseModel):
    module_key: str
    module_code: str
    definition_key: str = "module.property"
    definition_version: int = Field(default=1, ge=1)
    display_order: int = Field(default=0, ge=0)
    records: list[PropertyRecordInput] = Field(default_factory=list)


class MaterialStatePropertiesInput(BaseModel):
    property_modules: list[PropertyModuleInput] = Field(default_factory=list)
    deleted_record_keys: list[str] = Field(default_factory=list)
    deleted_module_keys: list[str] = Field(default_factory=list)
    schema_version: int = Field(default=1, ge=1)


def convert_legacy_state(state: dict[str, Any]) -> dict[str, Any]:
    """将旧 tc_results/properties 转为模块化结构，不修改输入对象。"""
    result = deepcopy(state)
    if "property_modules" in result:
        return result
    records: list[dict[str, Any]] = []
    for index, old in enumerate(result.get("tc_results") or []):
        if not isinstance(old, dict):
            continue
        experimental = old.get("result_kind") == "experimental" or old.get("tc_method") == "experimental"
        record = {
            "record_key": f"legacy-tc-{index}",
            "module_code": "superconductive_properties",
            "record_type": "measured_tc" if experimental else "predicted_tc",
            "property_code": "tc",
            "definition_key": f"record.superconductive_properties.{'measured_tc' if experimental else 'predicted_tc'}.{old.get('tc_method') or 'unknown'}",
            "definition_version": 1,
            "name_raw": "critical temperature",
            "value_kind": "number" if old.get("tc_value_k") is not None else "range",
            "value_raw": str(old.get("value_raw") or old.get("tc_value_k") or ""),
            "value_number": old.get("tc_value_k"),
            "value_min": old.get("tc_min_k"), "value_max": old.get("tc_max_k"),
            "unit_raw": old.get("unit_raw") or "K", "canonical_unit": "K",
            "method_code": old.get("tc_method") or ("resistivity" if experimental else "unknown"),
            "is_representative": bool(old.get("is_representative")),
            "payload": ({"experimental_conditions": {}} if experimental else {"calculation_conditions": {}}),
        }
        records.append(record)
    for index, old in enumerate(result.get("properties") or []):
        if not isinstance(old, dict):
            continue
        value = old.get("value")
        kind = "number" if isinstance(value, (int, float)) and not isinstance(value, bool) else "text"
        records.append({
            "record_key": f"legacy-property-{index}", "module_code": "superconductive_properties",
            "record_type": "property", "property_code": old.get("name") or "custom",
            "definition_key": "record.superconductive_properties.custom", "definition_version": 1,
            "name_raw": old.get("name_raw") or old.get("name") or "legacy property", "value_kind": kind,
            "value_raw": str(old.get("value_raw") or value or ""), "value_number": value if kind == "number" else None,
            "value_text": value if kind == "text" else None, "unit_raw": old.get("unit"), "payload": {},
        })
    result["property_modules"] = [{"module_key": "module-superconductive", "module_code": "superconductive_properties", "display_order": 0, "records": records}]
    result["schema_version"] = 1
    return result
