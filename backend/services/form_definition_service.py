"""FormDefinition 管理服务（同步 SQLAlchemy 会话版本）。"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func

from backend import models
from backend.ingest.form_definitions import definition_checksum, validate_definition_payload
from backend.ingest.property_modules import PropertyValidationError, PropertyIssue


def create_definition(db, payload: dict[str, Any], actor_id: int | None = None) -> models.FormDefinition:
    validate_definition_payload(payload)
    key = str(payload.get("definition_key") or "").strip()
    latest = db.query(func.max(models.FormDefinition.version)).filter(models.FormDefinition.definition_key == key).scalar() or 0
    data = {**payload, "definition_key": key, "version": int(latest) + 1}
    checksum = definition_checksum(data)
    item = models.FormDefinition(
        definition_key=key, version=data["version"], target_kind=data.get("target_kind", "property_record"),
        module_code=data.get("module_code", ""), record_type=data.get("record_type"), method_code=data.get("method_code"),
        property_code=data.get("property_code"), core_schema=data.get("core_schema", {}), json_schema=data.get("json_schema", {}),
        ui_schema=data.get("ui_schema", {}), checksum=checksum, created_by=actor_id,
    )
    db.add(item)
    db.flush()
    return item


def publish_definition(db, item: models.FormDefinition, actor_id: int) -> models.FormDefinition:
    if item.status != "draft":
        raise PropertyValidationError([PropertyIssue("status", "definition_not_available", "已发布定义不可重复发布")])
    item.status = "published"
    item.published_by = actor_id
    item.published_at = datetime.utcnow()
    db.flush()
    return item


def retire_definition(db, item: models.FormDefinition) -> models.FormDefinition:
    if item.status != "published":
        raise PropertyValidationError([PropertyIssue("status", "definition_not_available", "只有已发布定义可停用")])
    item.status = "retired"
    db.flush()
    return item


def promote_custom_property(db, *, paper_id: int, record_key: str, actor_id: int, operation_id: str, target_property_code: str, display_name: str, description: str | None = None) -> dict[str, Any]:
    record = db.query(models.PropertyRecord).filter(models.PropertyRecord.paper_id == paper_id, models.PropertyRecord.record_key == record_key, models.PropertyRecord.property_code == "custom").first()
    if record is None:
        raise PropertyValidationError([PropertyIssue("record_key", "schema_validation_failed", "自定义性质记录不存在")])
    if not target_property_code or target_property_code.lower() in {"tc", "custom", "critical_temperature"}:
        raise PropertyValidationError([PropertyIssue("target_property_code", "custom_property_conflict", "目标代码不可用")])
    existing = db.query(models.PropertyDefinitionPromotionEvent).filter_by(operation_id=operation_id).first()
    if existing:
        return {"definition_key": existing.target_definition_key, "version": existing.target_definition_version, "checksum": existing.target_checksum, "event_id": existing.id}
    definition_key = f"record.property.{target_property_code}"
    if db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=1).first():
        raise PropertyValidationError([PropertyIssue("target_property_code", "custom_property_conflict", "目标代码已存在")])
    payload = {"definition_key": definition_key, "version": 1, "target_kind": "property_record", "module_code": record.module.module_code if record.module else "superconductive_properties", "record_type": "property", "property_code": target_property_code, "core_schema": {}, "json_schema": {"type": "object", "additionalProperties": True}, "ui_schema": {}}
    item = models.FormDefinition(definition_key=definition_key, version=1, target_kind="property_record", module_code=payload["module_code"], record_type="property", property_code=target_property_code, core_schema={}, json_schema=payload["json_schema"], ui_schema={}, status="published", checksum=definition_checksum(payload), created_by=actor_id, published_by=actor_id, published_at=datetime.utcnow())
    db.add(item); db.flush()
    event = models.PropertyDefinitionPromotionEvent(operation_id=operation_id, actor_user_id=actor_id, source_paper_id=paper_id, source_paper_revision=record.paper_revision, source_record_key=record_key, source_snapshot={"record_checksum": record.record_checksum, "name_raw": record.name_raw, "value_kind": record.value_kind, "unit_raw": record.unit_raw}, target_definition_key=definition_key, target_definition_version=1, target_checksum=item.checksum)
    db.add(event); db.flush()
    return {"definition_key": definition_key, "version": 1, "checksum": item.checksum, "event_id": event.id}
