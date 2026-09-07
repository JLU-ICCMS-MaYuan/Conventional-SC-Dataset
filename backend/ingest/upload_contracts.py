"""上传任务的纯状态规则、manifest 校验与公开 DTO。"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any, Iterable, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

UPLOAD_STATE_SCHEMA_VERSION = 1
SCIENTIFIC_DRAFT_SCHEMA_VERSION = 2
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
    custom_property_key: str | None = None
    definition_key: str
    definition_version: int = Field(ge=1)
    name_raw: str
    value_kind: Literal["number", "range", "text", "boolean"]
    value_raw: str
    value_number: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    value_text: str | None = None
    value_boolean: bool | None = None
    uncertainty: float | None = Field(default=None, ge=0)
    unit_raw: str | None = None
    canonical_unit: str | None = None
    method_code: str | None = None
    method_raw: str | None = None
    criterion_code: str | None = None
    criterion_raw: str | None = None
    structure_key: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence: dict[str, Any] | None = None
    evidences: list[dict[str, Any]] = Field(default_factory=list)
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
    schema_version: Literal[SCIENTIFIC_DRAFT_SCHEMA_VERSION] = SCIENTIFIC_DRAFT_SCHEMA_VERSION


def _legacy_property_module(name: str) -> str:
    normalized = name.casefold().replace("-", "_").replace(" ", "_")
    if any(token in normalized for token in ("phonon", "frequency", "debye", "omega")):
        return "dynamical_properties"
    if any(token in normalized for token in ("enthalpy", "entropy", "heat", "stability", "thermo")):
        return "thermodynamical_properties"
    if any(token in normalized for token in ("dos", "density_of_states", "band", "fermi", "electronic", "gap")):
        return "electronic_properties"
    return "superconductive_properties"


def _legacy_custom_key(index: int, name: str) -> str:
    digest = hashlib.sha256(f"{index}:{name}".encode("utf-8")).hexdigest()[:16]
    return f"legacy-custom-{digest}"


def _legacy_value_raw(raw: Any, value: Any, value_min: Any = None, value_max: Any = None) -> str:
    if raw not in (None, ""):
        return str(raw)
    if value is not None:
        return str(value)
    if value_min is not None and value_max is not None:
        return f"{value_min}-{value_max}"
    return ""


def convert_legacy_state(state: dict[str, Any]) -> dict[str, Any]:
    """将旧 tc_results/properties 转为模块化结构，不修改输入对象。"""
    result = deepcopy(state)
    if "property_modules" in result:
        version = int(result.get("schema_version") or 0)
        if version not in {0, SCIENTIFIC_DRAFT_SCHEMA_VERSION}:
            raise UploadContractError(
                "unsupported_scientific_schema_version",
                f"不支持的科学草稿版本: {version}",
                "schema_version",
            )
        for legacy_key in ("tc_results", "properties", "calculation_contexts", "experimental_contexts"):
            result.pop(legacy_key, None)
        result["schema_version"] = SCIENTIFIC_DRAFT_SCHEMA_VERSION
        return result
    modules: dict[str, list[dict[str, Any]]] = {}
    for index, old in enumerate(result.get("tc_results") or []):
        if not isinstance(old, dict):
            raise UploadContractError(
                "legacy_scientific_conversion_failed", "旧 Tc 记录不是对象", f"tc_results[{index}]",
            )
        experimental = old.get("result_kind") == "experimental" or old.get("tc_method") == "experimental"
        method = old.get("tc_method") or ("resistivity" if experimental else "unknown")
        if method == "experimental":
            method = "resistivity"
        conditions = old.get("experimental_conditions" if experimental else "calculation_conditions")
        if not isinstance(conditions, dict):
            conditions = old.get("experimental_context" if experimental else "calculation_context")
        payload: dict[str, Any] = {
            "experimental_conditions" if experimental else "calculation_conditions": (
                deepcopy(conditions) if isinstance(conditions, dict) else {}
            ),
        }
        if not experimental and isinstance(old.get("parameters"), dict):
            payload["parameters"] = deepcopy(old["parameters"])
        record = {
            "record_key": f"legacy-tc-{index}",
            "module_code": "superconductive_properties",
            "record_type": "measured_tc" if experimental else "predicted_tc",
            "property_code": "tc",
            "definition_key": f"record.superconductive_properties.{'measured_tc' if experimental else 'predicted_tc'}.{method}",
            "definition_version": 1,
            "name_raw": "critical temperature",
            "value_kind": "number" if old.get("tc_value_k") is not None else "range",
            "value_raw": _legacy_value_raw(
                old.get("value_raw"), old.get("tc_value_k"),
                old.get("tc_min_k"), old.get("tc_max_k"),
            ),
            "value_number": old.get("tc_value_k"),
            "value_min": old.get("tc_min_k"), "value_max": old.get("tc_max_k"),
            "unit_raw": old.get("unit_raw") or "K", "canonical_unit": "K",
            "method_code": method,
            "method_raw": old.get("tc_method_custom"),
            "uncertainty": old.get("uncertainty_k"),
            "criterion_code": old.get("criterion_code"),
            "criterion_raw": old.get("criterion_raw"),
            "is_representative": bool(old.get("is_representative")),
            "structure_key": old.get("structure_key"),
            "payload": payload,
            "evidence": deepcopy(old.get("evidence")) if isinstance(old.get("evidence"), dict) else None,
            "evidences": deepcopy(old.get("evidences") or []),
        }
        modules.setdefault("superconductive_properties", []).append(record)
    for index, old in enumerate(result.get("properties") or []):
        if not isinstance(old, dict):
            raise UploadContractError(
                "legacy_scientific_conversion_failed", "旧普通物性记录不是对象", f"properties[{index}]",
            )
        name = str(old.get("name_raw") or old.get("name") or "").strip()
        if not name:
            raise UploadContractError(
                "legacy_scientific_conversion_failed", "旧普通物性缺少名称", f"properties[{index}].name_raw",
            )
        value = old.get("value", old.get("value_number"))
        if old.get("value_min") is not None or old.get("value_max") is not None:
            if old.get("value_min") is None or old.get("value_max") is None:
                raise UploadContractError(
                    "legacy_scientific_conversion_failed", "旧范围物性必须同时具有上下界", f"properties[{index}]",
                )
            kind = "range"
        elif isinstance(value, bool):
            kind = "boolean"
        elif isinstance(value, (int, float)):
            kind = "number"
        else:
            kind = "text"
        module_code = _legacy_property_module(str(old.get("name") or name))
        modules.setdefault(module_code, []).append({
            "record_key": f"legacy-property-{index}", "module_code": module_code,
            "record_type": "property", "property_code": "custom",
            "custom_property_key": _legacy_custom_key(index, name),
            "definition_key": f"record.{module_code}.custom", "definition_version": 1,
            "name_raw": name, "value_kind": kind,
            "value_raw": _legacy_value_raw(
                old.get("value_raw"), value, old.get("value_min"), old.get("value_max"),
            ),
            "value_number": value if kind == "number" else None,
            "value_min": old.get("value_min") if kind == "range" else None,
            "value_max": old.get("value_max") if kind == "range" else None,
            "value_text": str(value) if kind == "text" and value is not None else None,
            "value_boolean": value if kind == "boolean" else None,
            "unit_raw": old.get("unit_raw") or old.get("unit"),
            "canonical_unit": old.get("canonical_unit"),
            "payload": deepcopy(old.get("payload") or {}),
            "evidence": deepcopy(old.get("evidence")) if isinstance(old.get("evidence"), dict) else None,
            "evidences": deepcopy(old.get("evidences") or []),
        })
    for legacy_key in ("tc_results", "properties", "calculation_contexts", "experimental_contexts"):
        result.pop(legacy_key, None)
    result["property_modules"] = [
        {
            "module_key": f"module-{code}", "module_code": code,
            "definition_key": f"module.{code}", "definition_version": 1,
            "display_order": order, "records": records,
        }
        for order, (code, records) in enumerate(modules.items())
        if records
    ]
    result["schema_version"] = SCIENTIFIC_DRAFT_SCHEMA_VERSION
    return result


def convert_legacy_scientific_draft(draft: dict[str, Any]) -> dict[str, Any]:
    """把草稿中的所有材料状态升级到当前模块化契约。"""
    result = deepcopy(draft)
    states = result.get("material_states")
    if states is None:
        return result
    if not isinstance(states, list):
        raise UploadContractError(
            "legacy_scientific_conversion_failed", "材料状态必须是数组", "material_states",
        )
    converted: list[dict[str, Any]] = []
    for index, state in enumerate(states):
        if not isinstance(state, dict):
            raise UploadContractError(
                "legacy_scientific_conversion_failed",
                "材料状态不是对象",
                f"material_states[{index}]",
            )
        converted.append(convert_legacy_state(state))
    result["material_states"] = converted
    result["scientific_schema_version"] = SCIENTIFIC_DRAFT_SCHEMA_VERSION
    return result
