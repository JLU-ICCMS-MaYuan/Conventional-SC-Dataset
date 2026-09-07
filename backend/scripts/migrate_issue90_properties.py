"""Repeatable Copy/Reconcile/cutover runner for Issue #90."""

from __future__ import annotations

import argparse
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import MetaData, Table, and_, delete, insert, inspect, select, text, update

from backend.database import engine
from backend.services.issue90_migration import (
    MigrationBlocked, MigrationPhase, advance_persisted, load_checkpoint, persist_checkpoint,
)

TARGET_COLUMNS = (
    "record_key", "paper_id", "paper_revision", "material_state_id", "module_id",
    "record_type", "property_code", "custom_property_key", "definition_id", "definition_key",
    "definition_version", "name_raw", "value_kind", "value_raw", "value_number", "value_min",
    "value_max", "value_text", "value_boolean", "uncertainty", "unit_raw", "canonical_unit",
    "method_code", "method_raw", "criterion_code", "criterion_raw", "is_representative",
    "structure_key", "payload_json", "source_fingerprint", "record_checksum",
)


def _plain(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, float):
        decimal_value = Decimal(str(value))
        return int(decimal_value) if decimal_value == decimal_value.to_integral_value() else float(decimal_value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _checksum(value: Any) -> str:
    return hashlib.sha256(json.dumps(_plain(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _first(conn, table: Table, **filters):
    return conn.execute(select(table).where(and_(*[table.c[key] == value for key, value in filters.items()]))).mappings().first()


def _reflect(conn) -> dict[str, Table]:
    metadata = MetaData()
    metadata.reflect(bind=conn)
    required = {
        "property_modules", "property_records", "form_definitions", "property_record_evidences",
        "issue90_property_migration_map", "issue90_migration_anomalies",
        "issue90_migration_checkpoint", "issue90_chemical_systems", "issue90_superconductors",
    }
    missing = required - set(metadata.tables)
    if missing:
        raise RuntimeError(f"Expand 尚未执行，缺少目标表: {', '.join(sorted(missing))}")
    return metadata.tables


def _mapping_key(source_table: str, source_id: int, paper_id: int, revision: int, target_table: str) -> dict[str, Any]:
    return {"source_table": source_table, "source_id": source_id, "paper_id": paper_id, "paper_revision": revision, "target_table": target_table}


def _put_mapping(conn, table: Table, key: dict[str, Any], values: dict[str, Any]) -> None:
    current = _first(conn, table, **key)
    payload = {**values, "updated_at": datetime.utcnow()}
    if current:
        conn.execute(update(table).where(table.c.id == current["id"]).values(**payload))
    else:
        conn.execute(insert(table).values(**key, **payload))


def _previous_revision_mapping(
    conn,
    table: Table,
    key: dict[str, Any],
) -> dict[str, Any] | None:
    return conn.execute(
        select(table)
        .where(
            and_(
                table.c.source_table == key["source_table"],
                table.c.source_id == key["source_id"],
                table.c.paper_id == key["paper_id"],
                table.c.paper_revision != key["paper_revision"],
                table.c.target_table == key["target_table"],
                table.c.status != "archived",
            )
        )
        .order_by(table.c.paper_revision.desc(), table.c.id.desc())
    ).mappings().first()


def _archive_superseded_mapping(conn, table: Table, previous: dict[str, Any] | None) -> None:
    if previous is None:
        return
    conn.execute(
        update(table)
        .where(table.c.id == previous["id"])
        .values(
            status="archived",
            error_message="source_revision_superseded",
            updated_at=datetime.utcnow(),
        )
    )


def _put_anomaly(conn, table: Table, *, source_table: str, source_id: int, paper_id: int, revision: int, code: str, details: dict[str, Any]) -> dict[str, Any]:
    key = {"source_table": source_table, "source_id": source_id, "paper_id": paper_id, "paper_revision": revision, "code": code}
    current = _first(conn, table, **key)
    if current:
        conn.execute(update(table).where(table.c.id == current["id"]).values(details=details, resolved=False))
    else:
        conn.execute(insert(table).values(**key, details=details, resolved=False))
    return {**key, "details": details}


def _definition(conn, definitions: Table, key: str):
    return conn.execute(select(definitions).where(and_(definitions.c.definition_key == key, definitions.c.version == 1))).mappings().first()


def _material_copy(conn, tables: dict[str, Table], state: dict[str, Any], *, dry_run: bool, report: dict[str, Any]) -> None:
    source_sc = _first(conn, tables["superconductors"], id=state["superconductor_id"])
    if not source_sc:
        report["errors"].append({"source_table": "superconductors", "source_id": state["superconductor_id"], "error": "missing_material"})
        return
    source_system = _first(conn, tables["chemical_systems"], id=source_sc["chemical_system_id"])
    if not source_system:
        report["errors"].append({"source_table": "chemical_systems", "source_id": source_sc["chemical_system_id"], "error": "missing_system"})
        return
    paper_id, revision = state["paper_id"], state["paper_revision"]
    target_systems, target_scs, mapping = tables["issue90_chemical_systems"], tables["issue90_superconductors"], tables["issue90_property_migration_map"]
    system_values = {"paper_id": paper_id, "paper_revision": revision, "system_key": source_system["system_key"], "elements_list": source_system["elements_list"], "element_count": source_system["element_count"]}
    system_checksum = _checksum(system_values)
    target_system = _first(conn, target_systems, paper_id=paper_id, paper_revision=revision, system_key=source_system["system_key"])
    if not dry_run:
        if target_system:
            conn.execute(update(target_systems).where(target_systems.c.id == target_system["id"]).values(**system_values))
        else:
            target_id = conn.execute(insert(target_systems).values(**system_values)).inserted_primary_key[0]
            target_system = _first(conn, target_systems, id=target_id)
        system_map_key = _mapping_key("chemical_systems", source_system["id"], paper_id, revision, "issue90_chemical_systems")
        previous_system_map = _previous_revision_mapping(conn, mapping, system_map_key)
        _put_mapping(conn, mapping, system_map_key, {"target_id": target_system["id"], "target_record_key": None, "source_checksum": system_checksum, "target_checksum": system_checksum, "field_map": {"system_key": "system_key", "elements_list": "elements_list", "element_count": "element_count"}, "status": "copied", "error_message": None})
        _archive_superseded_mapping(conn, mapping, previous_system_map)
    target_system_id = target_system["id"] if target_system else -int(source_system["id"])
    sc_values = {key: source_sc[key] for key in ("chemical_formula", "formula_normalized", "composition_key", "isotope_signature", "display_name", "elements_list", "composition", "element_ratio")}
    sc_values.update(paper_id=paper_id, paper_revision=revision, chemical_system_id=target_system_id)
    sc_checksum = _checksum({**sc_values, "chemical_system_id": source_system["id"]})
    target_sc = _first(conn, target_scs, paper_id=paper_id, paper_revision=revision, composition_key=source_sc["composition_key"])
    if not dry_run:
        if target_sc:
            conn.execute(update(target_scs).where(target_scs.c.id == target_sc["id"]).values(**sc_values))
        else:
            target_id = conn.execute(insert(target_scs).values(**sc_values)).inserted_primary_key[0]
            target_sc = _first(conn, target_scs, id=target_id)
        sc_map_key = _mapping_key("superconductors", source_sc["id"], paper_id, revision, "issue90_superconductors")
        previous_sc_map = _previous_revision_mapping(conn, mapping, sc_map_key)
        _put_mapping(conn, mapping, sc_map_key, {"target_id": target_sc["id"], "target_record_key": state.get("state_key"), "source_checksum": sc_checksum, "target_checksum": sc_checksum, "field_map": {"chemical_system_id": target_system_id, "material_state_id": state["id"]}, "status": "copied", "error_message": None})
        _archive_superseded_mapping(conn, mapping, previous_sc_map)


def _conditions(context: dict[str, Any] | None, *, experimental: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    if not context:
        return {}, {}
    skip = {"id", "paper_id", "paper_revision", "material_state_id", "created_at", "updated_at", "lambda_ep", "omega_log_k", "mu_star"}
    condition = {key: _plain(value) for key, value in context.items() if key not in skip and value is not None}
    parameters = {}
    if not experimental:
        for key, unit in (("lambda_ep", "1"), ("omega_log_k", "K"), ("mu_star", "1")):
            if context.get(key) is not None:
                parameters[key] = {"value_raw": str(context[key]), "value_number": _plain(context[key]), "unit": unit}
    return condition, parameters


def _evidence_rows(conn, table: Table | None, source_key: str, source_id: int) -> list[dict[str, Any]]:
    if table is None:
        return []
    return [dict(row) for row in conn.execute(select(table).where(table.c[source_key] == source_id)).mappings()]


def _target_checksum(record: dict[str, Any], evidence_ids: list[int]) -> str:
    return _checksum({"record": {key: record.get(key) for key in TARGET_COLUMNS if key not in {"record_checksum"}}, "evidence_ids": sorted(evidence_ids)})


def _scientific_snapshot(record: dict[str, Any]) -> dict[str, Any]:
    return _plain({
        "record_type": record.get("record_type"), "property_code": record.get("property_code"),
        "custom_property_key": record.get("custom_property_key"), "name_raw": record.get("name_raw"),
        "value_kind": record.get("value_kind"), "value_raw": record.get("value_raw"),
        "value_number": record.get("value_number"), "value_min": record.get("value_min"),
        "value_max": record.get("value_max"), "value_text": record.get("value_text"),
        "value_boolean": record.get("value_boolean"), "uncertainty": record.get("uncertainty"),
        "unit_raw": record.get("unit_raw"), "canonical_unit": record.get("canonical_unit"),
        "method_code": record.get("method_code"), "method_raw": record.get("method_raw"),
        "criterion_code": record.get("criterion_code"), "criterion_raw": record.get("criterion_raw"),
        "is_representative": bool(record.get("is_representative")),
        "structure_key": record.get("structure_key"), "payload": record.get("payload_json") or {},
    })


def _json_value(value: Any, default: Any) -> Any:
    if value in (None, ""):
        return default
    return json.loads(value) if isinstance(value, str) else value


def _mismatches(expected: Any, actual: Any, path: str = "") -> list[dict[str, Any]]:
    if isinstance(expected, dict) and isinstance(actual, dict):
        result = []
        for key in sorted(set(expected) | set(actual)):
            child = f"{path}.{key}" if path else key
            result.extend(_mismatches(expected.get(key), actual.get(key), child))
        return result
    if _plain(expected) != _plain(actual):
        return [{"field": path, "expected": _plain(expected), "actual": _plain(actual)}]
    return []


def _copy_record(conn, tables: dict[str, Table], source_table: str, source: dict[str, Any], state: dict[str, Any], record: dict[str, Any], definition_key: str, payload: dict[str, Any], evidence_rows: list[dict[str, Any]], *, dry_run: bool, report: dict[str, Any]) -> None:
    definitions, modules, records = tables["form_definitions"], tables["property_modules"], tables["property_records"]
    mapping, target_evidence = tables["issue90_property_migration_map"], tables["property_record_evidences"]
    definition = _definition(conn, definitions, definition_key)
    if not definition:
        report["errors"].append({"source_table": source_table, "source_id": source["id"], "error": "missing_definition", "definition_key": definition_key})
        return
    module_code = definition["module_code"]
    module = _first(conn, modules, material_state_id=state["id"], module_code=module_code)
    if not module and not dry_run:
        module_key = f"legacy-{module_code}-{state['id']}"
        module_id = conn.execute(insert(modules).values(module_key=module_key, paper_id=state["paper_id"], paper_revision=state["paper_revision"], material_state_id=state["id"], module_code=module_code, definition_key=f"module.{module_code}", definition_version=1, display_order=0, metadata_json={"source": "issue90"})).inserted_primary_key[0]
        module = _first(conn, modules, id=module_id)
    module_id = module["id"] if module else -int(state["id"])
    record.update(module_id=module_id, definition_id=definition["id"], definition_key=definition_key, definition_version=1, payload_json=payload)
    record["record_checksum"] = _checksum({key: record.get(key) for key in TARGET_COLUMNS if key != "record_checksum"})
    evidence_ids = [int(row["paper_evidence_id"]) for row in evidence_rows]
    source_snapshot = {"source": source, "payload": payload, "evidence_ids": evidence_ids}
    source_checksum = _checksum(source_snapshot)
    map_key = _mapping_key(source_table, source["id"], state["paper_id"], state["paper_revision"], "property_records")
    current_map = _first(conn, mapping, **map_key)
    previous_map = None if current_map else _previous_revision_mapping(conn, mapping, map_key)
    old_map = current_map or previous_map
    if dry_run:
        report["copied"] += 1
        return
    target = _first(conn, records, id=old_map["target_id"]) if old_map and old_map.get("target_id") else None
    if target is None:
        target = _first(conn, records, record_key=record["record_key"])
    current_evidence_ids = [] if target is None else [
        int(row[0])
        for row in conn.execute(
            select(target_evidence.c.paper_evidence_id).where(
                target_evidence.c.record_id == target["id"]
            )
        )
    ]
    target_is_current = (
        target is not None
        and current_map is not None
        and current_map["status"] != "error"
        and current_map["source_checksum"] == source_checksum
        and current_map["target_checksum"] == _target_checksum(dict(target), current_evidence_ids)
    )
    if target_is_current:
        report["skipped"] += 1
        return
    values = {key: record.get(key) for key in TARGET_COLUMNS}
    if target:
        conn.execute(update(records).where(records.c.id == target["id"]).values(**values))
        conn.execute(delete(target_evidence).where(target_evidence.c.record_id == target["id"]))
        target_id = target["id"]
        report["updated"] += 1
    else:
        target_id = conn.execute(insert(records).values(**values)).inserted_primary_key[0]
        report["copied"] += 1
    for evidence in evidence_rows:
        conn.execute(insert(target_evidence).values(record_id=target_id, paper_evidence_id=evidence["paper_evidence_id"], paper_id=state["paper_id"], paper_revision=state["paper_revision"], field_path=evidence.get("field_path") or "", evidence_role=evidence.get("evidence_role") or "primary"))
    persisted = dict(_first(conn, records, id=target_id))
    target_checksum = _target_checksum(persisted, evidence_ids)
    field_map = {
        "mapping": {"value": "value_number|value_min|value_max|value_text", "unit_raw": "unit_raw", "context": "payload", "evidence": "property_record_evidences"},
        "expected": _scientific_snapshot(persisted), "evidence": sorted(evidence_ids),
    }
    _put_mapping(conn, mapping, map_key, {"target_id": target_id, "target_record_key": record["record_key"], "source_checksum": source_checksum, "target_checksum": target_checksum, "field_map": field_map, "status": "copied", "error_message": None})
    _archive_superseded_mapping(conn, mapping, previous_map)


def _archive_deleted(conn, tables: dict[str, Table], report: dict[str, Any]) -> None:
    mapping, records = tables["issue90_property_migration_map"], tables["property_records"]
    for item in conn.execute(select(mapping).where(and_(mapping.c.target_table == "property_records", mapping.c.status != "archived"))).mappings():
        source = tables.get(item["source_table"])
        exists = source is not None and _first(conn, source, id=item["source_id"], paper_id=item["paper_id"], paper_revision=item["paper_revision"])
        if exists:
            continue
        if item["target_id"]:
            conn.execute(delete(records).where(records.c.id == item["target_id"]))
        conn.execute(update(mapping).where(mapping.c.id == item["id"]).values(status="archived", error_message="source_deleted", updated_at=datetime.utcnow()))
        report["deleted"] += 1


def copy_legacy_data(conn, *, dry_run: bool = False, final_sync: bool = False) -> dict[str, Any]:
    tables = _reflect(conn)
    report: dict[str, Any] = {"copied": 0, "updated": 0, "deleted": 0, "skipped": 0, "errors": []}
    states = tables.get("material_states")
    if states is None:
        return report
    for state_row in conn.execute(select(states)).mappings():
        state = dict(state_row)
        _material_copy(conn, tables, state, dry_run=dry_run, report=report)
        tcs = tables.get("tc_results")
        if tcs is not None:
            for row_value in conn.execute(select(tcs).where(tcs.c.material_state_id == state["id"])).mappings():
                row = dict(row_value)
                experimental = row.get("result_kind") == "experimental" or row.get("tc_method") == "experimental"
                context_table = tables.get("experimental_contexts" if experimental else "calculation_contexts")
                context_id = row.get("experimental_context_id" if experimental else "calculation_context_id")
                context = dict(_first(conn, context_table, id=context_id) or {}) if context_table is not None and context_id else None
                condition, parameters = _conditions(context, experimental=experimental)
                payload = {"experimental_conditions" if experimental else "calculation_conditions": condition}
                if parameters:
                    payload["parameters"] = parameters
                method = row.get("tc_method") or "unknown"
                if experimental and method == "experimental":
                    method = "resistivity"
                definition_key = f"record.superconductive_properties.{'measured_tc' if experimental else 'predicted_tc'}.{method}"
                if not _definition(conn, tables["form_definitions"], definition_key):
                    definition_key = "record.superconductive_properties.measured_tc.resistivity" if experimental else "record.superconductive_properties.predicted_tc.unknown"
                    method = "resistivity" if experimental else "unknown"
                record = {"record_key": f"legacy-tc-{row['id']}", "paper_id": state["paper_id"], "paper_revision": state["paper_revision"], "material_state_id": state["id"], "record_type": "measured_tc" if experimental else "predicted_tc", "property_code": "tc", "custom_property_key": None, "name_raw": "critical temperature", "value_kind": "number" if row.get("tc_value_k") is not None else "range", "value_raw": row.get("value_raw") or str(row.get("tc_value_k") or ""), "value_number": row.get("tc_value_k"), "value_min": row.get("tc_min_k"), "value_max": row.get("tc_max_k"), "value_text": None, "value_boolean": None, "uncertainty": row.get("uncertainty_k"), "unit_raw": row.get("unit_raw") or "K", "canonical_unit": "K", "method_code": method, "method_raw": row.get("tc_method_custom"), "criterion_code": None, "criterion_raw": None, "is_representative": bool(row.get("is_representative")), "structure_key": None, "source_fingerprint": row.get("source_fingerprint") or _checksum(["tc", row["id"]])}
                evidence = _evidence_rows(conn, tables.get("tc_result_evidences"), "tc_result_id", row["id"])
                _copy_record(conn, tables, "tc_results", row, state, record, definition_key, payload, evidence, dry_run=dry_run, report=report)
        props = tables.get("superconductor_properties")
        if props is not None:
            for row_value in conn.execute(select(props).where(props.c.material_state_id == state["id"])).mappings():
                row = dict(row_value)
                kind = "range" if row.get("value_min") is not None and row.get("value_max") is not None else "number" if row.get("value_number") is not None else "text"
                definition_key = "record.superconductive_properties.custom"
                record = {"record_key": f"legacy-property-{row['id']}", "paper_id": state["paper_id"], "paper_revision": state["paper_revision"], "material_state_id": state["id"], "record_type": "property", "property_code": "custom", "custom_property_key": f"legacy-{row['id']}", "name_raw": row.get("name_raw") or "legacy property", "value_kind": kind, "value_raw": row.get("value_raw") or str(row.get("value_number") or ""), "value_number": row.get("value_number") if kind == "number" else None, "value_min": row.get("value_min"), "value_max": row.get("value_max"), "value_text": row.get("value_raw") if kind == "text" else None, "value_boolean": None, "uncertainty": None, "unit_raw": row.get("unit_raw"), "canonical_unit": row.get("canonical_unit"), "method_code": None, "method_raw": None, "criterion_code": None, "criterion_raw": None, "is_representative": False, "structure_key": None, "source_fingerprint": row.get("source_fingerprint") or _checksum(["property", row["id"]])}
                evidence = _evidence_rows(conn, tables.get("superconductor_property_evidences"), "superconductor_property_id", row["id"])
                _copy_record(conn, tables, "superconductor_properties", row, state, record, definition_key, {}, evidence, dry_run=dry_run, report=report)
    if final_sync and not dry_run:
        _archive_deleted(conn, tables, report)
    if not dry_run:
        checkpoint = load_checkpoint(conn)
        if checkpoint.phase == MigrationPhase.EXPAND:
            advance_persisted(conn, MigrationPhase.COPY)
    return report


def reconcile_legacy_data(conn) -> dict[str, Any]:
    tables = _reflect(conn)
    mapping, records = tables["issue90_property_migration_map"], tables["property_records"]
    evidence = tables["property_record_evidences"]
    anomalies = tables["issue90_migration_anomalies"]
    report: dict[str, Any] = {"checked": 0, "errors": []}
    for item in conn.execute(select(mapping).where(and_(mapping.c.target_table == "property_records", mapping.c.status != "archived"))).mappings():
        report["checked"] += 1
        target = _first(conn, records, id=item["target_id"])
        ids = [] if not target else [row[0] for row in conn.execute(select(evidence.c.paper_evidence_id).where(evidence.c.record_id == target["id"]))]
        actual_checksum = None if not target else _target_checksum(dict(target), ids)
        field_map = _json_value(item["field_map"], {})
        expected = field_map.get("expected") or {}
        actual = {} if not target else _scientific_snapshot(dict(target))
        mismatches = _mismatches(expected, actual)
        if sorted(field_map.get("evidence") or []) != sorted(ids):
            mismatches.append({"field": "evidence", "expected": sorted(field_map.get("evidence") or []), "actual": sorted(ids)})
        if not target or actual_checksum != item["target_checksum"] or mismatches:
            error = _put_anomaly(conn, anomalies, source_table=item["source_table"], source_id=item["source_id"], paper_id=item["paper_id"], revision=item["paper_revision"], code="target_drift", details={"expected_checksum": item["target_checksum"], "actual_checksum": actual_checksum, "mismatches": mismatches})
            report["errors"].append(error)
            conn.execute(update(mapping).where(mapping.c.id == item["id"]).values(status="error", error_message="target_drift"))
        else:
            conn.execute(update(mapping).where(mapping.c.id == item["id"]).values(status="reconciled", error_message=None, updated_at=datetime.utcnow()))
            conn.execute(
                update(anomalies)
                .where(
                    and_(
                        anomalies.c.source_table == item["source_table"],
                        anomalies.c.source_id == item["source_id"],
                        anomalies.c.paper_id == item["paper_id"],
                        anomalies.c.paper_revision == item["paper_revision"],
                        anomalies.c.code == "target_drift",
                        anomalies.c.resolved == False,  # noqa: E712
                    )
                )
                .values(resolved=True)
            )
    unresolved = conn.execute(select(anomalies.c.id).where(anomalies.c.resolved == False)).first()  # noqa: E712
    if not report["errors"] and not unresolved:
        checkpoint = load_checkpoint(conn)
        if checkpoint.phase == MigrationPhase.COPY:
            advance_persisted(conn, MigrationPhase.RECONCILE, reconcile_ok=True)
    return report


def _read_switch(conn) -> dict[str, Any]:
    checkpoint = load_checkpoint(conn)
    if checkpoint.phase != MigrationPhase.RECONCILE or not checkpoint.reconciled:
        raise MigrationBlocked("最终 Reconcile 未完成")
    checkpoint.writes_blocked = True
    persist_checkpoint(conn, checkpoint)
    if conn.dialect.name != "mysql":
        raise MigrationBlocked("Read switch DDL 只允许在隔离 MySQL 执行")
    fks = inspect(conn).get_foreign_keys("material_states")
    for fk in fks:
        if fk.get("referred_table") == "superconductors" and fk.get("name"):
            conn.exec_driver_sql(f"ALTER TABLE material_states DROP FOREIGN KEY `{fk['name']}`")
    conn.exec_driver_sql("RENAME TABLE chemical_systems TO legacy_issue90_chemical_systems, issue90_chemical_systems TO chemical_systems, superconductors TO legacy_issue90_superconductors, issue90_superconductors TO superconductors")
    conn.execute(text("""
        UPDATE material_states ms
        JOIN issue90_property_migration_map m
          ON m.source_table='superconductors' AND m.source_id=ms.superconductor_id
         AND m.paper_id=ms.paper_id AND m.paper_revision=ms.paper_revision
         AND m.target_table='issue90_superconductors'
        SET ms.superconductor_id=m.target_id
    """))
    conn.exec_driver_sql("ALTER TABLE material_states ADD CONSTRAINT fk_material_states_superconductor_revision FOREIGN KEY (superconductor_id, paper_id, paper_revision) REFERENCES superconductors (id, paper_id, paper_revision) ON UPDATE CASCADE ON DELETE RESTRICT")
    advance_persisted(conn, MigrationPhase.READ_SWITCH)
    return {"phase": "read_switch", "reads_target": True, "writes_blocked": True}


def run_migration(conn, action: str | MigrationPhase, *, dry_run: bool = False) -> dict[str, Any]:
    value = action.value if isinstance(action, MigrationPhase) else str(action).replace("_", "-")
    if value == "copy":
        return copy_legacy_data(conn, dry_run=dry_run)
    if value == "final-sync":
        report = copy_legacy_data(conn, dry_run=dry_run, final_sync=True)
        if not dry_run and not report["errors"]:
            reconcile = reconcile_legacy_data(conn)
            report["reconcile"] = reconcile
            report["errors"].extend(reconcile["errors"])
        return report
    if value == "reconcile":
        return reconcile_legacy_data(conn)
    if value == "read-switch":
        return _read_switch(conn)
    if value == "write-switch":
        checkpoint = advance_persisted(conn, MigrationPhase.WRITE_SWITCH)
        return {"phase": checkpoint.phase.value, "writes_target": checkpoint.writes_target}
    if value == "observe":
        checkpoint = advance_persisted(conn, MigrationPhase.OBSERVE, observe_ok=True)
        return {"phase": checkpoint.phase.value, "observed": checkpoint.observed}
    raise ValueError(f"unknown Issue #90 migration action: {action}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", nargs="?", default="copy", choices=("copy", "final-sync", "reconcile", "read-switch", "write-switch", "observe"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with engine.begin() as conn:
        report = run_migration(conn, args.action, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if report.get("errors") else 0


if __name__ == "__main__":
    raise SystemExit(main())
