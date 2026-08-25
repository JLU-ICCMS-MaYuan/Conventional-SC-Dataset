"""Deterministically migrate legacy material type strings to material states.

The command is dry-run by default. It requires two explicit database URLs so a
target database can never be mistaken for the legacy source.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from sqlalchemy import create_engine, text

from backend.services.classification_catalog import resolve_seed_material_family


LEGACY_ROWS_SQL = text("""
    SELECT id, paper_id, superconductor_id, pressure_gpa, superconductor_type
    FROM superconductor_records
    WHERE superconductor_type IS NOT NULL
      AND TRIM(superconductor_type) <> ''
    ORDER BY id
""")

TARGET_STATES_SQL = text("""
    SELECT id, material_family_id
    FROM material_states
    WHERE paper_id = :paper_id
      AND superconductor_id = :superconductor_id
      AND (
        (:pressure_gpa IS NULL AND pressure_value_gpa IS NULL)
        OR pressure_value_gpa = :pressure_gpa
      )
""")


def classify_legacy_row(
    row: Mapping[str, Any],
    *,
    target_states: Iterable[Mapping[str, Any]],
    family_ids_by_code: Mapping[str, int],
) -> dict[str, Any]:
    result = {
        "legacy_record_id": row.get("id"),
        "paper_id": row.get("paper_id"),
        "superconductor_id": row.get("superconductor_id"),
        "pressure_gpa": row.get("pressure_gpa"),
        "legacy_value": row.get("superconductor_type"),
    }
    match = resolve_seed_material_family(row.get("superconductor_type"))
    if match is None or match.code not in family_ids_by_code:
        return {**result, "status": "unmapped", "reason": "旧值不在确定性白名单"}

    states = [dict(item) for item in target_states]
    if len(states) != 1:
        return {
            **result,
            "status": "ambiguous",
            "reason": f"目标材料状态匹配数量为 {len(states)}",
            "target_family_code": match.code,
        }

    state = states[0]
    target_family_id = int(family_ids_by_code[match.code])
    existing_family_id = state.get("material_family_id")
    if existing_family_id not in (None, target_family_id):
        return {
            **result,
            "status": "conflict",
            "reason": "目标材料状态已有不同材料家族",
            "material_state_id": state["id"],
            "existing_family_id": existing_family_id,
            "target_family_id": target_family_id,
        }
    return {
        **result,
        "status": "ready",
        "material_state_id": state["id"],
        "target_family_id": target_family_id,
        "target_family_code": match.code,
        "matched_by": match.matched_by,
    }


def build_report(legacy_engine, target_engine) -> dict[str, Any]:
    with target_engine.connect() as target_connection:
        families = target_connection.execute(
            text("SELECT id, code FROM material_families")
        ).mappings().all()
        family_ids_by_code = {str(item["code"]): int(item["id"]) for item in families}

        with legacy_engine.connect() as legacy_connection:
            legacy_rows = legacy_connection.execute(LEGACY_ROWS_SQL).mappings().all()

        items = []
        for row in legacy_rows:
            states = target_connection.execute(
                TARGET_STATES_SQL,
                {
                    "paper_id": row["paper_id"],
                    "superconductor_id": row["superconductor_id"],
                    "pressure_gpa": row["pressure_gpa"],
                },
            ).mappings().all()
            items.append(classify_legacy_row(
                row,
                target_states=states,
                family_ids_by_code=family_ids_by_code,
            ))

    counts = {
        status: sum(item["status"] == status for item in items)
        for status in ("ready", "ambiguous", "unmapped", "conflict")
    }
    return {"dry_run": True, "counts": counts, "items": items}


def apply_ready_items(target_engine, report: dict[str, Any]) -> int:
    ready = [item for item in report["items"] if item["status"] == "ready"]
    with target_engine.begin() as connection:
        for item in ready:
            result = connection.execute(
                text("""
                    UPDATE material_states
                    SET material_family_id = :family_id
                    WHERE id = :state_id
                      AND (material_family_id IS NULL OR material_family_id = :family_id)
                """),
                {"family_id": item["target_family_id"], "state_id": item["material_state_id"]},
            )
            if result.rowcount != 1:
                raise RuntimeError(f"材料状态 {item['material_state_id']} 在应用时发生并发冲突")
    report["dry_run"] = False
    report["applied"] = len(ready)
    return len(ready)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="迁移旧材料类型到材料状态分类目录")
    parser.add_argument("--legacy-database-url", required=True)
    parser.add_argument("--target-database-url", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="应用报告中 status=ready 的记录")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.legacy_database_url == args.target_database_url:
        raise SystemExit("旧数据库和目标数据库 URL 必须不同")
    legacy_engine = create_engine(args.legacy_database_url)
    target_engine = create_engine(args.target_database_url)
    report = build_report(legacy_engine, target_engine)
    if args.apply:
        apply_ready_items(target_engine, report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"report": str(args.report), **report["counts"], "applied": report.get("applied", 0)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
