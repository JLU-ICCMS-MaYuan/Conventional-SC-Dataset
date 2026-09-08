"""修复 Issue #90 初始定义字段和旧结构引用。"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "issue90_data_integrity_repair_v1"
down_revision = "issue90_audit_cleanup_v1"
branch_labels = None
depends_on = None


DEFINITION_KEYS = (
    "definition_key",
    "version",
    "target_kind",
    "module_code",
    "record_type",
    "method_code",
    "property_code",
    "core_schema",
    "json_schema",
    "ui_schema",
)

RECORD_COLUMNS = (
    "record_key", "paper_id", "paper_revision", "material_state_id", "module_id",
    "record_type", "property_code", "custom_property_key", "definition_id", "definition_key",
    "definition_version", "name_raw", "value_kind", "value_raw", "value_number", "value_min",
    "value_max", "value_text", "value_boolean", "uncertainty", "unit_raw", "canonical_unit",
    "method_code", "method_raw", "criterion_code", "criterion_raw", "is_representative",
    "structure_key", "payload_json", "source_fingerprint",
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
    return hashlib.sha256(
        json.dumps(
            _plain(value), ensure_ascii=False, sort_keys=True,
            separators=(",", ":"), default=str,
        ).encode()
    ).hexdigest()


def _definition_checksum(row: dict) -> str:
    content = {key: row.get(key) for key in DEFINITION_KEYS}
    return hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _repair_definitions(connection) -> None:
    path = Path(__file__).parents[2] / "backend" / "data" / "form_definitions.v1.json"
    source_rows = json.loads(path.read_text(encoding="utf-8"))
    column_types = {
        "version": sa.Integer(),
        "core_schema": sa.JSON(),
        "json_schema": sa.JSON(),
        "ui_schema": sa.JSON(),
    }
    definitions = sa.table(
        "form_definitions",
        *[
            sa.column(name, column_types.get(name, sa.String()))
            for name in DEFINITION_KEYS
        ],
        sa.column("checksum", sa.String()),
    )
    for source in source_rows:
        values = {key: source.get(key) for key in DEFINITION_KEYS}
        values["checksum"] = _definition_checksum(source)
        connection.execute(
            sa.update(definitions)
            .where(
                sa.and_(
                    definitions.c.definition_key == source["definition_key"],
                    definitions.c.version == source["version"],
                )
            )
            .values(
                record_type=values["record_type"],
                method_code=values["method_code"],
                property_code=values["property_code"],
                checksum=values["checksum"],
            )
        )


def _repair_structure_references(connection) -> None:
    metadata = sa.MetaData()
    metadata.reflect(bind=connection, only=["property_records", "structure_models"])
    records = metadata.tables["property_records"]
    structures = metadata.tables["structure_models"]

    rows = connection.execute(sa.select(records)).mappings().all()

    for row in rows:
        payload = row["payload_json"] or {}
        if isinstance(payload, str):
            payload = json.loads(payload)
        if not isinstance(payload, dict):
            continue
        payload = deepcopy(payload)
        structure_key = row["structure_key"]
        changed = False
        if isinstance(structure_key, str) and structure_key.isdigit():
            structure = connection.execute(
                sa.select(structures.c.id).where(
                    structures.c.id == int(structure_key),
                    structures.c.material_state_id == row["material_state_id"],
                    structures.c.paper_id == row["paper_id"],
                    structures.c.paper_revision == row["paper_revision"],
                )
            ).first()
            if structure is None:
                raise RuntimeError(
                    f"Issue #90 结构引用无法解析: property_record={row['id']}, structure_key={structure_key}"
                )
            structure_key = f"structure-{structure_key}"
            changed = True
        for condition_name in ("calculation_conditions", "experimental_conditions"):
            conditions = payload.get(condition_name)
            if not isinstance(conditions, dict) or conditions.get("structure_id") is None:
                continue
            structure_id = conditions["structure_id"]
            structure = connection.execute(
                sa.select(structures.c.id).where(
                    structures.c.id == structure_id,
                    structures.c.material_state_id == row["material_state_id"],
                    structures.c.paper_id == row["paper_id"],
                    structures.c.paper_revision == row["paper_revision"],
                )
            ).first()
            if structure is None:
                raise RuntimeError(
                    f"Issue #90 结构引用无法解析: property_record={row['id']}, structure_id={structure_id}"
                )
            candidate_key = f"structure-{structure_id}"
            if structure_key not in (None, candidate_key):
                raise RuntimeError(
                    f"Issue #90 结构引用冲突: property_record={row['id']}, "
                    f"structure_key={structure_key}, structure_id={structure_id}"
                )
            structure_key = candidate_key
            conditions.pop("structure_id", None)
            changed = True

        if not changed:
            continue
        values = dict(row)
        values["structure_key"] = structure_key
        values["payload_json"] = payload
        values["record_checksum"] = _checksum({
            key: values.get(key)
            for key in RECORD_COLUMNS
        })
        connection.execute(
            records.update()
            .where(records.c.id == row["id"])
            .values(
                structure_key=values["structure_key"],
                payload_json=values["payload_json"],
                record_checksum=values["record_checksum"],
            )
        )


def upgrade() -> None:
    connection = op.get_bind()
    _repair_definitions(connection)
    _repair_structure_references(connection)


def downgrade() -> None:
    raise RuntimeError("Issue #90 数据修复不可逆；请从修复前数据库快照恢复")
