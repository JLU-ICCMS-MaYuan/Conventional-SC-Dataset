"""FormDefinition 管理服务（同步 SQLAlchemy 会话版本）。"""

from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from sqlalchemy import func

from backend import models
from backend.ingest.form_definitions import definition_checksum, definition_payload, validate_definition_payload
from backend.ingest.property_modules import PropertyValidationError, PropertyIssue


def create_definition(db, payload: dict[str, Any], actor_id: int | None = None) -> models.FormDefinition:
    key = str(payload.get("definition_key") or "").strip()
    if not key:
        raise PropertyValidationError([PropertyIssue("definition_key", "definition_invalid", "定义键不能为空")])
    payload = {**payload, "definition_key": key}
    validate_definition_payload(payload)
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
    payload = definition_payload(item)
    validate_definition_payload(payload)
    item.checksum = definition_checksum(payload)
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


def promote_custom_property(
    db,
    *,
    paper_id: int,
    record_key: str,
    actor_id: int,
    operation_id: str,
    expected_paper_revision: int,
    source_checksum: str,
    target_property_code: str,
    display_name: str,
    module_code: str,
    value_kind: str,
    canonical_unit: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    target_property_code = target_property_code.strip().lower()
    request_snapshot = {
        "paper_id": paper_id, "record_key": record_key, "expected_paper_revision": expected_paper_revision,
        "source_checksum": source_checksum, "target_property_code": target_property_code,
        "display_name": display_name.strip(), "module_code": module_code, "value_kind": value_kind,
        "canonical_unit": canonical_unit, "description": description,
    }
    existing = db.query(models.PropertyDefinitionPromotionEvent).filter_by(operation_id=operation_id).first()
    if existing:
        if (existing.source_snapshot or {}).get("request") != request_snapshot:
            raise PropertyValidationError([PropertyIssue("operation_id", "property_promotion_conflict", "幂等键已用于不同请求")])
        return {"definition_key": existing.target_definition_key, "version": existing.target_definition_version, "checksum": existing.target_checksum, "event_id": existing.id}

    paper = db.query(models.Paper).filter(models.Paper.id == paper_id).with_for_update().first()
    if paper is None or paper.review_status != "approved" or paper.content_revision != expected_paper_revision or paper.approved_revision != expected_paper_revision:
        raise PropertyValidationError([PropertyIssue("expected_paper_revision", "property_promotion_stale", "来源论文不是已批准的当前 revision")])
    record = db.query(models.PropertyRecord).filter(
        models.PropertyRecord.paper_id == paper_id,
        models.PropertyRecord.paper_revision == expected_paper_revision,
        models.PropertyRecord.record_key == record_key,
        models.PropertyRecord.property_code == "custom",
    ).with_for_update().first()
    if record is None:
        raise PropertyValidationError([PropertyIssue("record_key", "property_promotion_stale", "自定义性质记录不存在")])
    if record.record_checksum != source_checksum:
        raise PropertyValidationError([PropertyIssue("source_checksum", "property_promotion_stale", "来源记录已变化")])
    if not record.module or record.module.module_code != module_code or record.value_kind != value_kind:
        raise PropertyValidationError([PropertyIssue("record_key", "property_promotion_invalid", "模块或值类型与来源记录不一致")])
    if canonical_unit is not None and canonical_unit != record.canonical_unit:
        raise PropertyValidationError([PropertyIssue("canonical_unit", "property_promotion_invalid", "规范单位与来源记录不一致")])
    if not re.fullmatch(r"[a-z][a-z0-9_]{1,99}", target_property_code) or target_property_code in {"tc", "custom", "critical_temperature"}:
        raise PropertyValidationError([PropertyIssue("target_property_code", "property_promotion_invalid", "目标代码不可用")])
    if not display_name.strip():
        raise PropertyValidationError([PropertyIssue("display_name", "property_promotion_invalid", "显示名称不能为空")])
    definition_key = f"record.property.{target_property_code}"
    if db.query(models.FormDefinition).filter_by(definition_key=definition_key, version=1).first():
        raise PropertyValidationError([PropertyIssue("target_property_code", "property_promotion_conflict", "目标代码已存在")])
    prior_events = db.query(models.PropertyDefinitionPromotionEvent).filter_by(
        source_paper_id=paper_id, source_paper_revision=expected_paper_revision,
    ).all()
    if any((event.source_snapshot or {}).get("module_code") == module_code and (event.source_snapshot or {}).get("custom_property_key") == record.custom_property_key for event in prior_events):
        raise PropertyValidationError([PropertyIssue("record_key", "property_promotion_conflict", "该自定义性质已提升")])
    core_properties: dict[str, Any] = {
        "record_type": {"const": "property"},
        "property_code": {"const": target_property_code},
        "value_kind": {"const": value_kind},
    }
    if canonical_unit is not None:
        core_properties["canonical_unit"] = {"const": canonical_unit}
    payload = {
        "definition_key": definition_key, "version": 1, "target_kind": "property_record",
        "module_code": module_code, "record_type": "property", "method_code": None,
        "property_code": target_property_code,
        "core_schema": {"type": "object", "properties": core_properties},
        "json_schema": {"type": "object", "additionalProperties": False},
        "ui_schema": {},
    }
    validate_definition_payload(payload)
    item = models.FormDefinition(
        **payload, status="published", checksum=definition_checksum(payload), created_by=actor_id,
        published_by=actor_id, published_at=datetime.utcnow(),
    )
    db.add(item); db.flush()
    event = models.PropertyDefinitionPromotionEvent(operation_id=operation_id, actor_user_id=actor_id, source_paper_id=paper_id, source_paper_revision=record.paper_revision, source_record_key=record_key, source_snapshot={"request": request_snapshot, "record_checksum": record.record_checksum, "module_code": module_code, "custom_property_key": record.custom_property_key, "name_raw": record.name_raw, "value_kind": record.value_kind, "unit_raw": record.unit_raw, "canonical_unit": record.canonical_unit}, target_definition_key=definition_key, target_definition_version=1, target_checksum=item.checksum)
    db.add(event); db.flush()
    return {"definition_key": definition_key, "version": 1, "checksum": item.checksum, "event_id": event.id}
