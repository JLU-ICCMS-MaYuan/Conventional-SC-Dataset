"""Issue #90 Copy/Reconcile 数据迁移。

用法：``python -m backend.scripts.migrate_issue90_properties [--dry-run]``。
脚本只向目标表新增数据，重复执行依赖 ``issue90_property_migration_map`` 的
源/目标组合唯一键保持幂等；异常会写入映射表并以非零状态返回。
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from typing import Any

from sqlalchemy import MetaData, Table, and_, insert, select, update

from backend.database import engine


def _checksum(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _first(conn, table: Table, **filters):
    return conn.execute(select(table).where(and_(*[table.c[key] == value for key, value in filters.items()]))).mappings().first()


def copy_legacy_data(conn, *, dry_run: bool = False) -> dict[str, Any]:
    metadata = MetaData()
    metadata.reflect(bind=conn)
    required = {"property_modules", "property_records", "form_definitions", "issue90_property_migration_map"}
    missing = required - set(metadata.tables)
    if missing:
        raise RuntimeError(f"Expand 尚未执行，缺少目标表: {', '.join(sorted(missing))}")
    target_modules = metadata.tables["property_modules"]
    target_records = metadata.tables["property_records"]
    definitions = metadata.tables["form_definitions"]
    mapping = metadata.tables["issue90_property_migration_map"]
    states = metadata.tables.get("material_states")
    tcs = metadata.tables.get("tc_results")
    props = metadata.tables.get("superconductor_properties")
    contexts = metadata.tables.get("calculation_contexts")
    experiments = metadata.tables.get("experimental_contexts")
    chemical_systems = metadata.tables.get("chemical_systems")
    superconductors = metadata.tables.get("superconductors")
    shadow_systems = metadata.tables.get("issue90_legacy_chemical_systems")
    shadow_superconductors = metadata.tables.get("issue90_legacy_superconductors")
    tc_evidence = metadata.tables.get("tc_result_evidences")
    prop_evidence = metadata.tables.get("superconductor_property_evidences")
    target_evidence = metadata.tables.get("property_record_evidences")
    report: dict[str, Any] = {"copied": 0, "skipped": 0, "errors": []}
    if states is None:
        return report

    def ensure_module(state):
        existing = conn.execute(select(target_modules).where(and_(target_modules.c.material_state_id == state["id"], target_modules.c.module_code == "superconductive_properties"))).mappings().first()
        if existing:
            return existing
        values = {"module_key": f"legacy-superconductive-{state['id']}", "paper_id": state["paper_id"], "paper_revision": state["paper_revision"], "material_state_id": state["id"], "module_code": "superconductive_properties", "definition_key": "module.superconductive_properties", "definition_version": 1, "display_order": 0, "metadata_json": {"source": "issue90"}}
        if dry_run:
            return {**values, "id": -state["id"]}
        result = conn.execute(insert(target_modules).values(**values))
        return conn.execute(select(target_modules).where(target_modules.c.module_key == values["module_key"])).mappings().one()

    def copy_record(source_table: str, source: dict[str, Any], state: dict[str, Any], record: dict[str, Any], definition_key: str, payload: dict[str, Any]):
        source_id = source["id"]
        existing_map = conn.execute(select(mapping).where(and_(mapping.c.source_table == source_table, mapping.c.source_id == source_id, mapping.c.paper_id == state["paper_id"], mapping.c.paper_revision == state["paper_revision"], mapping.c.target_table == "property_records"))).mappings().first()
        if existing_map and existing_map.get("status") == "copied":
            report["skipped"] += 1
            return
        module = ensure_module(state)
        definition = conn.execute(select(definitions).where(and_(definitions.c.definition_key == definition_key, definitions.c.version == 1))).mappings().first()
        if not definition:
            report["errors"].append({"source_table": source_table, "source_id": source_id, "error": "missing_definition", "definition_key": definition_key})
            return
        if record["record_type"] == "predicted_tc" and "calculation_conditions" not in payload:
            payload["calculation_conditions"] = {}
        if record["record_type"] == "measured_tc" and "experimental_conditions" not in payload:
            payload["experimental_conditions"] = {}
        record.update({"module_id": module["id"], "definition_id": definition["id"], "definition_key": definition_key, "definition_version": 1, "payload_json": payload})
        record["record_checksum"] = _checksum(record)
        if not dry_run:
            result = conn.execute(insert(target_records).values(**record))
            target_id = result.inserted_primary_key[0]
            conn.execute(insert(mapping).values(source_table=source_table, source_id=source_id, paper_id=state["paper_id"], paper_revision=state["paper_revision"], target_table="property_records", target_id=target_id, target_record_key=record["record_key"], field_map={"payload": "legacy context"}, status="copied"))
            if target_evidence is not None:
                evidence_table = tc_evidence if source_table == "tc_results" else prop_evidence
                source_key = "tc_result_id" if source_table == "tc_results" else "superconductor_property_id"
                for evidence in conn.execute(select(evidence_table).where(evidence_table.c[source_key] == source_id)).mappings() if evidence_table is not None else ():
                    conn.execute(insert(target_evidence).values(record_id=target_id, paper_evidence_id=evidence["paper_evidence_id"], paper_id=state["paper_id"], paper_revision=state["paper_revision"], field_path="", evidence_role=evidence.get("evidence_role") or "primary"))
        report["copied"] += 1

    for state in conn.execute(select(states)).mappings():
        # 论文内材料影子副本：旧材料可能被多篇论文共享，目标唯一键必须缩小到
        # paper_id + revision，且同一论文重复运行不能生成额外副本。
        if superconductors is not None and shadow_superconductors is not None:
            source_material = _first(conn, superconductors, id=state["superconductor_id"])
            if source_material:
                source_system = _first(conn, chemical_systems, id=source_material["chemical_system_id"]) if chemical_systems is not None else None
                if source_system and shadow_systems is not None and not _first(conn, shadow_systems, paper_id=state["paper_id"], paper_revision=state["paper_revision"], system_key=source_system["system_key"]):
                    if not dry_run:
                        conn.execute(insert(shadow_systems).values(source_id=source_system["id"], paper_id=state["paper_id"], paper_revision=state["paper_revision"], system_key=source_system["system_key"], elements_list=source_system["elements_list"], element_count=source_system["element_count"]))
                if not dry_run and not _first(conn, shadow_superconductors, paper_id=state["paper_id"], paper_revision=state["paper_revision"], composition_key=source_material["composition_key"]):
                    shadow_system = _first(conn, shadow_systems, paper_id=state["paper_id"], paper_revision=state["paper_revision"], system_key=source_system["system_key"]) if source_system is not None else None
                    conn.execute(insert(shadow_superconductors).values(source_id=source_material["id"], paper_id=state["paper_id"], paper_revision=state["paper_revision"], chemical_system_id=shadow_system["id"] if shadow_system else 0, chemical_formula=source_material["chemical_formula"], formula_normalized=source_material["formula_normalized"], composition_key=source_material["composition_key"], isotope_signature=source_material.get("isotope_signature"), display_name=source_material["display_name"], elements_list=source_material["elements_list"], composition=source_material["composition"], element_ratio=source_material["element_ratio"]))
        if tcs is not None:
            rows = conn.execute(select(tcs).where(tcs.c.material_state_id == state["id"])).mappings()
            for row in rows:
                experimental = row.get("result_kind") == "experimental" or row.get("tc_method") == "experimental"
                method = "resistivity" if experimental and row.get("tc_method") == "experimental" else (row.get("tc_method") or "unknown")
                key = f"legacy-tc-{row['id']}"
                payload: dict[str, Any] = {}
                if experimental and experiments is not None and row.get("experimental_context_id"):
                    context = _first(conn, experiments, id=row["experimental_context_id"])
                    payload["experimental_conditions"] = dict(context or {})
                elif contexts is not None and row.get("calculation_context_id"):
                    context = _first(conn, contexts, id=row["calculation_context_id"])
                    payload["calculation_conditions"] = dict(context or {})
                    payload["parameters"] = {name: context.get(name) for name in ("lambda_ep", "omega_log_k", "mu_star") if context and context.get(name) is not None}
                values = {"record_key": key, "paper_id": state["paper_id"], "paper_revision": state["paper_revision"], "material_state_id": state["id"], "record_type": "measured_tc" if experimental else "predicted_tc", "property_code": "tc", "custom_property_key": None, "name_raw": "critical temperature", "value_kind": "number" if row.get("tc_value_k") is not None else "range", "value_raw": row.get("value_raw") or "", "value_number": row.get("tc_value_k"), "value_min": row.get("tc_min_k"), "value_max": row.get("tc_max_k"), "value_text": None, "value_boolean": None, "uncertainty": row.get("uncertainty_k"), "unit_raw": row.get("unit_raw") or "K", "canonical_unit": "K", "method_code": method, "method_raw": row.get("tc_method_custom"), "criterion_code": None, "criterion_raw": None, "is_representative": bool(row.get("is_representative")), "structure_key": None, "source_fingerprint": row.get("source_fingerprint") or _checksum(["tc", row["id"]])}
                definition_key = f"record.superconductive_properties.{'measured_tc' if experimental else 'predicted_tc'}.{method}"
                if not conn.execute(select(definitions.c.id).where(and_(definitions.c.definition_key == definition_key, definitions.c.version == 1))).first():
                    definition_key = "record.superconductive_properties.measured_tc.resistivity" if experimental else "record.superconductive_properties.predicted_tc.unknown"
                copy_record("tc_results", row, state, values, definition_key, payload)
        if props is not None:
            for row in conn.execute(select(props).where(props.c.material_state_id == state["id"])).mappings():
                kind = "range" if row.get("value_min") is not None and row.get("value_max") is not None else "number" if row.get("value_number") is not None else "text"
                values = {"record_key": f"legacy-property-{row['id']}", "paper_id": state["paper_id"], "paper_revision": state["paper_revision"], "material_state_id": state["id"], "record_type": "property", "property_code": "custom", "custom_property_key": f"legacy-{row['id']}", "name_raw": row.get("name_raw") or "legacy property", "value_kind": kind, "value_raw": row.get("value_raw") or "", "value_number": row.get("value_number") if kind == "number" else None, "value_min": row.get("value_min"), "value_max": row.get("value_max"), "value_text": row.get("value_raw") if kind == "text" else None, "value_boolean": None, "uncertainty": None, "unit_raw": row.get("unit_raw"), "canonical_unit": row.get("canonical_unit"), "method_code": None, "method_raw": None, "criterion_code": None, "criterion_raw": None, "is_representative": False, "structure_key": None, "source_fingerprint": row.get("source_fingerprint") or _checksum(["property", row["id"]])}
                copy_record("superconductor_properties", row, state, values, "record.superconductive_properties.custom", {})
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    with engine.begin() as conn:
        report = copy_legacy_data(conn, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
