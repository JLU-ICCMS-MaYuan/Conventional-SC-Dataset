"""版本化 FormDefinition 的校验工具。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
import hashlib
import json
from typing import Any

from sqlalchemy import select

from backend import models
from backend.ingest.property_modules import canonical_json, validate_record, PropertyValidationError, PropertyIssue


def definition_checksum(data: dict[str, Any]) -> str:
    content = {key: data.get(key) for key in (
        "definition_key", "version", "target_kind", "module_code", "record_type", "method_code",
        "property_code", "core_schema", "json_schema", "ui_schema",
    )}
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def validate_definition_payload(data: dict[str, Any]) -> None:
    allowed = {"type", "properties", "required", "additionalProperties", "items", "enum", "const", "minimum", "maximum", "minItems", "maxItems", "minLength", "maxLength", "if", "then", "else", "allOf", "anyOf", "oneOf"}
    issues: list[PropertyIssue] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            unsupported = set(value) - allowed
            if unsupported:
                issues.append(PropertyIssue(path, "unsupported_schema_keyword", f"不支持 Schema 关键字: {', '.join(sorted(unsupported))}"))
            for key, child in value.items():
                walk(child, f"{path}.{key}")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    for key in ("core_schema", "json_schema", "ui_schema"):
        walk(data.get(key) or {}, key)
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

