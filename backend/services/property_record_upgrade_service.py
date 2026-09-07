"""PropertyRecord 定义升级与回滚的事务服务。"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from backend import models
from backend.ingest.property_modules import record_checksum, validate_record, PropertyValidationError, PropertyIssue


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
    return {"before": before, "after": after, "source_checksum": record.record_checksum, "target_checksum": record_checksum(after)}


def apply_upgrade(db, record: models.PropertyRecord, target: models.FormDefinition, actor_id: int, expected_checksum: str, payload: dict[str, Any] | None = None) -> models.PropertyRecordDefinitionEvent:
    if record.record_checksum != expected_checksum:
        raise PropertyValidationError([PropertyIssue("record_checksum", "schema_checksum_mismatch", "记录已发生变化")])
    preview = preview_upgrade(record, target, payload)
    before = preview["before"]
    after = preview["after"]
    record.definition_id = target.id
    record.definition_key = target.definition_key
    record.definition_version = target.version
    record.payload_json = after["payload"]
    record.record_checksum = preview["target_checksum"]
    event = models.PropertyRecordDefinitionEvent(
        record_id=record.id, paper_id=record.paper_id, paper_revision=record.paper_revision, record_key=record.record_key,
        operation="upgrade", actor_user_id=actor_id, from_definition_key=before["definition_key"], from_definition_version=before["definition_version"],
        to_definition_key=target.definition_key, to_definition_version=target.version, before_snapshot=before, after_snapshot=after,
        request_checksum=expected_checksum,
    )
    db.add(event)
    db.flush()
    return event


def rollback(db, record: models.PropertyRecord, event: models.PropertyRecordDefinitionEvent, actor_id: int, expected_checksum: str) -> models.PropertyRecordDefinitionEvent:
    if record.record_checksum != expected_checksum or event.operation not in {"upgrade", "rollback"}:
        raise PropertyValidationError([PropertyIssue("record_checksum", "schema_checksum_mismatch", "记录或事件已过期")])
    snapshot = deepcopy(event.before_snapshot)
    record.definition_key = snapshot["definition_key"]
    record.definition_version = snapshot["definition_version"]
    record.payload_json = snapshot["payload"]
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

