"""版本化 FormDefinition 的校验工具。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from typing import Any

from sqlalchemy import select

from backend import models
from backend.ingest.property_modules import (
    EXPERIMENTAL_METHODS,
    THEORETICAL_METHODS,
    PropertyIssue,
    PropertyValidationError,
    canonical_json,
    validate_record,
)


def definition_checksum(data: dict[str, Any]) -> str:
    content = {key: data.get(key) for key in (
        "definition_key", "version", "target_kind", "module_code", "record_type", "method_code",
        "property_code", "core_schema", "json_schema", "ui_schema",
    )}
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def definition_payload(item: models.FormDefinition | Any) -> dict[str, Any]:
    return {
        key: getattr(item, key)
        for key in (
            "definition_key", "version", "target_kind", "module_code", "record_type",
            "method_code", "property_code", "core_schema", "json_schema", "ui_schema",
        )
    }


def _json_pointer_segments(pointer: Any) -> tuple[str, ...] | None:
    if not isinstance(pointer, str) or not pointer.startswith("/"):
        return None
    segments: list[str] = []
    for raw_segment in pointer[1:].split("/"):
        index = 0
        while index < len(raw_segment):
            if raw_segment[index] == "~":
                if index + 1 >= len(raw_segment) or raw_segment[index + 1] not in {"0", "1"}:
                    return None
                index += 2
            else:
                index += 1
        segments.append(raw_segment.replace("~1", "/").replace("~0", "~"))
    return tuple(segments) if segments else None


def _schema_declares_path(schema: Any, segments: tuple[str, ...]) -> bool:
    current = schema
    for segment in segments:
        if not isinstance(current, dict):
            return False
        properties = current.get("properties")
        if isinstance(properties, dict) and segment in properties:
            current = properties[segment]
            continue
        items = current.get("items")
        if isinstance(items, dict) and (segment.isdigit() or segment in {"-", "*"}):
            current = items
            continue
        return False
    return bool(segments)


def validate_definition_payload(data: dict[str, Any]) -> None:
    allowed = {"type", "title", "properties", "required", "additionalProperties", "items", "enum", "const", "minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "if", "then", "else", "allOf", "anyOf", "oneOf"}
    allowed_types = {"object", "array", "string", "number", "integer", "boolean", "null"}
    issues: list[PropertyIssue] = []

    def walk_schema(schema: Any, path: str) -> None:
        if not isinstance(schema, dict):
            issues.append(PropertyIssue(path, "definition_invalid", "Schema 必须是对象"))
            return
        unsupported = set(schema) - allowed
        if unsupported:
            issues.append(PropertyIssue(path, "unsupported_schema_keyword", f"不支持 Schema 关键字: {', '.join(sorted(unsupported))}"))
        declared_type = schema.get("type")
        declared_types = declared_type if isinstance(declared_type, list) else [declared_type]
        if declared_type is not None and any(item not in allowed_types for item in declared_types):
            issues.append(PropertyIssue(f"{path}.type", "definition_invalid", "Schema 类型不受支持"))
        properties = schema.get("properties", {})
        if properties is not None and not isinstance(properties, dict):
            issues.append(PropertyIssue(f"{path}.properties", "definition_invalid", "properties 必须是对象"))
        elif isinstance(properties, dict):
            for name, child in properties.items():
                walk_schema(child, f"{path}.properties.{name}")
        if isinstance(schema.get("items"), dict):
            walk_schema(schema["items"], f"{path}.items")
        if isinstance(schema.get("additionalProperties"), dict):
            walk_schema(schema["additionalProperties"], f"{path}.additionalProperties")
        for keyword in ("if", "then", "else"):
            if keyword in schema:
                walk_schema(schema[keyword], f"{path}.{keyword}")
        for keyword in ("allOf", "anyOf", "oneOf"):
            if keyword in schema:
                if not isinstance(schema[keyword], list) or not schema[keyword]:
                    issues.append(PropertyIssue(f"{path}.{keyword}", "definition_invalid", f"{keyword} 必须是非空数组"))
                else:
                    for index, child in enumerate(schema[keyword]):
                        walk_schema(child, f"{path}.{keyword}[{index}]")

    for key in ("core_schema", "json_schema"):
        walk_schema(data.get(key) or {}, key)

    target_kind = data.get("target_kind")
    module_code = data.get("module_code")
    record_type = data.get("record_type")
    property_code = data.get("property_code")
    method_code = data.get("method_code")
    if target_kind not in {"property_module", "property_record"}:
        issues.append(PropertyIssue("target_kind", "definition_invalid", "定义目标类型无效"))
    if module_code not in models.PROPERTY_MODULE_CODES:
        issues.append(PropertyIssue("module_code", "definition_invalid", "定义模块无效"))
    if target_kind == "property_record":
        if record_type not in {"predicted_tc", "measured_tc", "property"}:
            issues.append(PropertyIssue("record_type", "definition_invalid", "记录类型无效"))
        if record_type in {"predicted_tc", "measured_tc"} and property_code != "tc":
            issues.append(PropertyIssue("property_code", "definition_invalid", "Tc 定义必须绑定 property_code=tc"))
        if record_type in {"predicted_tc", "measured_tc"} and not method_code:
            issues.append(PropertyIssue("method_code", "definition_invalid", "Tc 定义必须绑定方法"))
        if record_type == "predicted_tc" and method_code not in THEORETICAL_METHODS:
            issues.append(PropertyIssue("method_code", "definition_invalid", "预测 Tc 方法无效"))
        if record_type == "measured_tc" and method_code not in EXPERIMENTAL_METHODS:
            issues.append(PropertyIssue("method_code", "definition_invalid", "测量 Tc 方法无效"))
        key = str(data.get("definition_key") or "")
        if method_code and not key.endswith(f".{method_code}"):
            issues.append(PropertyIssue("definition_key", "definition_invalid", "方法定义键必须包含方法代码"))

    ui_schema = data.get("ui_schema") or {}
    if not isinstance(ui_schema, dict):
        issues.append(PropertyIssue("ui_schema", "definition_invalid", "UI Schema 必须是对象"))
    else:
        for index, field in enumerate(ui_schema.get("fields", [])):
            pointer = field.get("pointer") if isinstance(field, dict) else None
            segments = _json_pointer_segments(pointer)
            if segments and segments[0] == "payload":
                declared = _schema_declares_path(data.get("json_schema") or {}, segments[1:])
            else:
                declared = bool(segments) and any(
                    _schema_declares_path(data.get(schema_key) or {}, segments)
                    for schema_key in ("core_schema", "json_schema")
                )
            if not declared:
                issues.append(PropertyIssue(f"ui_schema.fields[{index}].pointer", "definition_invalid", "UI 字段未在 Schema 中声明"))
    if issues:
        raise PropertyValidationError(issues)


async def get_definition(session: Any, definition_key: str, version: int | None = None, *, current: bool = False) -> models.FormDefinition | None:
    query = select(models.FormDefinition).where(models.FormDefinition.definition_key == definition_key)
    if version is not None:
        query = query.where(models.FormDefinition.version == version)
    if current:
        query = query.where(models.FormDefinition.status == "published").order_by(models.FormDefinition.version.desc())
    else:
        query = query.order_by(models.FormDefinition.version.desc())
    result = await session.execute(query)
    return result.scalars().first() if hasattr(result, "scalars") else None


async def create_draft(session: Any, payload: dict[str, Any], actor_id: int | None = None) -> models.FormDefinition:
    validate_definition_payload(payload)
    key = str(payload.get("definition_key") or "").strip()
    if not key:
        raise PropertyValidationError([PropertyIssue("definition_key", "schema_validation_failed", "定义键不能为空")])
    result = await session.execute(select(models.FormDefinition.version).where(models.FormDefinition.definition_key == key).order_by(models.FormDefinition.version.desc()))
    latest = result.scalars().first() if hasattr(result, "scalars") else None
    version = int(latest or 0) + 1
    data = {**payload, "definition_key": key, "version": version, "status": "draft"}
    data["checksum"] = definition_checksum(data)
    item = models.FormDefinition(
        definition_key=key, version=version, target_kind=data.get("target_kind") or "property_record",
        module_code=data.get("module_code") or "", record_type=data.get("record_type"), method_code=data.get("method_code"),
        property_code=data.get("property_code"), core_schema=data.get("core_schema") or {}, json_schema=data.get("json_schema") or {},
        ui_schema=data.get("ui_schema") or {}, status="draft", checksum=data["checksum"], created_by=actor_id,
    )
    session.add(item)
    await session.flush()
    return item


async def publish(session: Any, item: models.FormDefinition, actor_id: int | None = None) -> models.FormDefinition:
    if item.status != "draft":
        raise PropertyValidationError([PropertyIssue("status", "definition_not_available", "只有草稿定义可以发布")])
    validate_definition_payload({"core_schema": item.core_schema, "json_schema": item.json_schema, "ui_schema": item.ui_schema})
    item.checksum = definition_checksum({
        "definition_key": item.definition_key, "version": item.version, "target_kind": item.target_kind,
        "module_code": item.module_code, "record_type": item.record_type, "method_code": item.method_code,
        "property_code": item.property_code, "core_schema": item.core_schema, "json_schema": item.json_schema, "ui_schema": item.ui_schema,
    })
    item.status = "published"
    item.published_by = actor_id
    item.published_at = datetime.utcnow()
    await session.flush()
    return item


async def retire(item: models.FormDefinition) -> models.FormDefinition:
    if item.status != "published":
        raise PropertyValidationError([PropertyIssue("status", "definition_not_available", "只有已发布定义可以停用")])
    item.status = "retired"
    return item


def definition_to_dict(item: models.FormDefinition) -> dict[str, Any]:
    return {
        "id": item.id, "definition_key": item.definition_key, "version": item.version,
        "target_kind": item.target_kind, "module_code": item.module_code, "record_type": item.record_type,
        "method_code": item.method_code, "property_code": item.property_code, "core_schema": item.core_schema,
        "json_schema": item.json_schema, "ui_schema": item.ui_schema, "status": item.status, "checksum": item.checksum,
    }
