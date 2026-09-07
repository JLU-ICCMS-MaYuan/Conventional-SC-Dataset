"""PropertyRecord 定义升级与回滚的事务服务。"""

from __future__ import annotations

from copy import deepcopy
import hashlib
from typing import Any

from backend import models
from backend.ingest.form_definitions import definition_checksum, definition_payload
from backend.ingest.property_modules import canonical_json, record_checksum, validate_record, PropertyValidationError, PropertyIssue


def record_snapshot(record: models.PropertyRecord) -> dict[str, Any]:
    return {
        "record_key": record.record_key, "module_code": record.module.module_code if record.module else None,
        "record_type": record.record_type, "property_code": record.property_code,
        "custom_property_key": record.custom_property_key, "definition_key": record.definition_key,
        "definition_version": record.definition_version, "name_raw": record.name_raw, "value_kind": record.value_kind,
        "value_raw": record.value_raw, "value_number": record.value_number, "value_min": record.value_min,
        "value_max": record.value_max, "value_text": record.value_text, "value_boolean": record.value_boolean,
        "uncertainty": record.uncertainty, "unit_raw": record.unit_raw, "canonical_unit": record.canonical_unit,
        "method_code": record.method_code, "method_raw": record.method_raw, "criterion_code": record.criterion_code,
        "criterion_raw": record.criterion_raw, "is_representative": record.is_representative,
        "structure_key": record.structure_key, "payload": deepcopy(record.payload_json or {}),
    }


def preview_upgrade(record: models.PropertyRecord, target: models.FormDefinition, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if target.status != "published" or target.definition_key != record.definition_key:
        raise PropertyValidationError([PropertyIssue("definition_key", "definition_not_available", "目标必须是同一键的已发布版本")])
    if target.version <= record.definition_version:
        raise PropertyValidationError([PropertyIssue("version", "definition_not_available", "只能升级到更高版本")])
    before = record_snapshot(record)
    after = deepcopy(before)
    after["definition_version"] = target.version
    if payload is not None:
        after["payload"] = deepcopy(payload)
    candidate = {**after, "module_code": record.module.module_code if record.module else "", "record_checksum": record_checksum(after)}
    validate_record(candidate, target)
    source_definition = record.definition
    if source_definition is None or source_definition.checksum != definition_checksum(definition_payload(source_definition)):
        raise PropertyValidationError([PropertyIssue("definition_key", "schema_checksum_mismatch", "来源定义校验和不匹配")])
    if target.checksum != definition_checksum(definition_payload(target)):
        raise PropertyValidationError([PropertyIssue("definition_key", "schema_checksum_mismatch", "目标定义校验和不匹配")])
    target_checksum = record_checksum(after)
    preview_material = {
        "paper_id": record.paper_id, "paper_revision": record.paper_revision,
        "record_key": record.record_key, "source_checksum": record.record_checksum,
        "source_definition_checksum": source_definition.checksum, "target_definition_checksum": target.checksum,
        "after": after,
    }
    preview_checksum = hashlib.sha256(canonical_json(preview_material).encode("utf-8")).hexdigest()
    before_keys = set((before.get("payload") or {}).keys())
    after_keys = set((after.get("payload") or {}).keys())
    return {"before": before, "after": after, "removed_fields": sorted(before_keys - after_keys), "source_checksum": record.record_checksum, "target_checksum": target_checksum, "preview_checksum": preview_checksum}


def apply_upgrade(db, record: models.PropertyRecord, target: models.FormDefinition, actor_id: int, expected_checksum: str, expected_preview_checksum: str, payload: dict[str, Any] | None = None) -> models.PropertyRecordDefinitionEvent:
    if record.record_checksum != expected_checksum:
        raise PropertyValidationError([PropertyIssue("record_checksum", "schema_checksum_mismatch", "记录已发生变化")])
    preview = preview_upgrade(record, target, payload)
    if preview["preview_checksum"] != expected_preview_checksum:
        raise PropertyValidationError([PropertyIssue("preview_checksum", "definition_upgrade_stale", "升级预览已过期")])
    before = preview["before"]
    after = preview["after"]
    record.definition_id = target.id
    record.definition = target
    record.definition_key = target.definition_key
    record.definition_version = target.version
    record.payload_json = after["payload"]
    record.record_checksum = preview["target_checksum"]
    previous = db.query(models.PropertyRecordDefinitionEvent).filter_by(record_id=record.id).order_by(models.PropertyRecordDefinitionEvent.id.desc()).first()
    event = models.PropertyRecordDefinitionEvent(
        record_id=record.id, paper_id=record.paper_id, paper_revision=record.paper_revision, record_key=record.record_key,
        operation="upgrade", actor_user_id=actor_id, from_definition_key=before["definition_key"], from_definition_version=before["definition_version"],
        to_definition_key=target.definition_key, to_definition_version=target.version, before_snapshot=before, after_snapshot=after,
        request_checksum=expected_preview_checksum, previous_event_id=previous.id if previous else None,
    )
    db.add(event)
    db.flush()
    return event


def rollback(db, record: models.PropertyRecord, event: models.PropertyRecordDefinitionEvent, actor_id: int, expected_checksum: str) -> models.PropertyRecordDefinitionEvent:
    latest = db.query(models.PropertyRecordDefinitionEvent).filter_by(record_id=record.id).order_by(models.PropertyRecordDefinitionEvent.id.desc()).first()
    if record.record_checksum != expected_checksum or event.operation != "upgrade" or latest is None or latest.id != event.id:
        raise PropertyValidationError([PropertyIssue("record_checksum", "definition_rollback_stale", "记录或事件已过期")])
    snapshot = deepcopy(event.before_snapshot)
    source_definition = db.query(models.FormDefinition).filter_by(definition_key=snapshot["definition_key"], version=snapshot["definition_version"]).first()
    if source_definition is None:
        raise PropertyValidationError([PropertyIssue("definition_key", "unknown_definition_version", "来源定义版本不存在")])
    validate_record(snapshot, source_definition, allow_retired=True)
    for key in ("record_type", "property_code", "custom_property_key", "definition_key", "definition_version", "name_raw", "value_kind", "value_raw", "value_number", "value_min", "value_max", "value_text", "value_boolean", "uncertainty", "unit_raw", "canonical_unit", "method_code", "method_raw", "criterion_code", "criterion_raw", "is_representative", "structure_key"):
        setattr(record, key, snapshot.get(key))
    record.definition_id = source_definition.id
    record.definition = source_definition
    record.payload_json = deepcopy(snapshot["payload"])
    record.record_checksum = record_checksum(snapshot)
    reverse = models.PropertyRecordDefinitionEvent(
        record_id=record.id, paper_id=record.paper_id, paper_revision=record.paper_revision, record_key=record.record_key,
        operation="rollback", actor_user_id=actor_id, from_definition_key=event.to_definition_key, from_definition_version=event.to_definition_version,
        to_definition_key=event.from_definition_key, to_definition_version=event.from_definition_version,
        before_snapshot=event.after_snapshot, after_snapshot=snapshot, request_checksum=expected_checksum, previous_event_id=event.id,
    )
    db.add(reverse)
    db.flush()
    return reverse
