"""MaterialState 模块化物性记录的规范化与持久化入口。

该模块只接受声明式 JSON；定义服务负责版本和权限，本文负责记录级不变量，
从而让上传、管理员编辑和迁移使用同一套校验逻辑。
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from decimal import Decimal
import hashlib
import json
from typing import Any, Iterable

from sqlalchemy import select

from backend import models


MODULE_CODES = set(models.PROPERTY_MODULE_CODES)
VALUE_KINDS = set(models.PROPERTY_RECORD_VALUE_KINDS)
THEORETICAL_METHODS = {
    "allen_dynes", "mcmillan", "isotropic_eliashberg",
    "anisotropic_eliashberg", "scdft", "other", "unknown",
}
EXPERIMENTAL_METHODS = {"resistivity", "magnetic_susceptibility", "specific_heat", "other", "unknown"}
SYSTEM_KEYS = {"tc", "critical_temperature", "lambda_ep", "omega_log", "mu_star"}


@dataclass
class PropertyIssue:
    field: str
    code: str
    message: str


class PropertyValidationError(ValueError):
    def __init__(self, issues: Iterable[PropertyIssue]):
        self.issues = list(issues)
        super().__init__("科学数据校验失败")

    def as_dict(self) -> dict[str, Any]:
        return {"detail": str(self), "issues": [issue.__dict__ for issue in self.issues]}


def _issue(field: str, code: str, message: str) -> PropertyIssue:
    return PropertyIssue(field, code, message)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)


def record_checksum(record: dict[str, Any]) -> str:
    material = {
        key: record.get(key)
        for key in (
            "record_key", "module_code", "record_type", "property_code", "custom_property_key",
            "definition_key", "definition_version", "name_raw", "value_kind", "value_raw",
            "value_number", "value_min", "value_max", "value_text", "value_boolean", "uncertainty",
            "unit_raw", "canonical_unit", "method_code", "method_raw", "criterion_code", "criterion_raw",
            "is_representative", "structure_key", "payload",
        )
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def _validate_schema(value: Any, schema: dict[str, Any], path: str, issues: list[PropertyIssue]) -> None:
    if not isinstance(schema, dict):
        return
    if "const" in schema and value != schema["const"]:
        issues.append(_issue(path, "schema_validation_failed", "字段必须匹配固定值"))
        return
    if "enum" in schema and value not in schema["enum"]:
        issues.append(_issue(path, "schema_validation_failed", "字段值不在允许枚举中"))
        return
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是对象"))
            return
        for name in schema.get("required", []):
            if name not in value:
                issues.append(_issue(f"{path}.{name}", "schema_validation_failed", "缺少必填字段"))
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    issues.append(_issue(f"{path}.{name}", "schema_validation_failed", "不允许的字段"))
        for name, child in properties.items():
            if name in value:
                _validate_schema(value[name], child, f"{path}.{name}", issues)
    elif expected == "array":
        if not isinstance(value, list):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是数组"))
            return
        if "minItems" in schema and len(value) < schema["minItems"]:
            issues.append(_issue(path, "schema_validation_failed", "数组元素数量不足"))
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            issues.append(_issue(path, "schema_validation_failed", "数组元素数量超限"))
        for index, item in enumerate(value):
            _validate_schema(item, schema.get("items", {}), f"{path}[{index}]", issues)
    elif expected == "string":
        if not isinstance(value, str):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是字符串"))
        elif "minLength" in schema and len(value) < schema["minLength"]:
            issues.append(_issue(path, "schema_validation_failed", "字符串长度不足"))
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是数字"))
        elif "minimum" in schema and value < schema["minimum"]:
            issues.append(_issue(path, "schema_validation_failed", "字段值小于最小值"))
    elif expected == "boolean" and not isinstance(value, bool):
        issues.append(_issue(path, "schema_validation_failed", "字段必须是布尔值"))


def _validate_value_shape(record: dict[str, Any], path: str, issues: list[PropertyIssue]) -> None:
    kind = record.get("value_kind")
    if kind not in VALUE_KINDS:
        issues.append(_issue(f"{path}.value_kind", "schema_validation_failed", "不支持的值类型"))
        return
    present = {key for key in ("value_number", "value_min", "value_max", "value_text", "value_boolean") if record.get(key) is not None}
    expected = {
        "number": {"value_number"}, "range": {"value_min", "value_max"},
        "text": {"value_text"}, "boolean": {"value_boolean"},
    }[kind]
    if not expected.issubset(present) or (present - expected):
        issues.append(_issue(f"{path}.value_kind", "schema_validation_failed", "规范值字段与 value_kind 不匹配"))
    if kind == "range" and record.get("value_min") > record.get("value_max"):
        issues.append(_issue(f"{path}.value_max", "schema_validation_failed", "范围上界必须不小于下界"))
    if record.get("uncertainty") is not None and record["uncertainty"] < 0:
        issues.append(_issue(f"{path}.uncertainty", "schema_validation_failed", "不确定度不能为负"))


def validate_record(record: dict[str, Any], definition: models.FormDefinition | None = None, path: str = "record") -> dict[str, Any]:
    """校验并复制一条记录，返回可安全写入的规范化数据。"""
    item = deepcopy(record)
    issues: list[PropertyIssue] = []
    module_code = str(item.get("module_code") or "")
    record_type = str(item.get("record_type") or "property")
    property_code = str(item.get("property_code") or "")
    method_code = str(item.get("method_code") or "") or None
    item["module_code"] = module_code
    item["record_type"] = record_type
    item["property_code"] = property_code
    item["method_code"] = method_code
    item["record_key"] = str(item.get("record_key") or "").strip()
    item["name_raw"] = str(item.get("name_raw") or "").strip()
    item["value_raw"] = str(item.get("value_raw") or "").strip()
    item["payload"] = deepcopy(item.get("payload") if isinstance(item.get("payload"), dict) else {})
    if module_code not in MODULE_CODES:
        issues.append(_issue(f"{path}.module_code", "unknown_module", "未注册的物性模块"))
    if not item["record_key"]:
        issues.append(_issue(f"{path}.record_key", "schema_validation_failed", "record_key 不能为空"))
    if not item["name_raw"]:
        issues.append(_issue(f"{path}.name_raw", "schema_validation_failed", "名称不能为空"))
    if not item["value_raw"]:
        issues.append(_issue(f"{path}.value_raw", "schema_validation_failed", "原始值不能为空"))
    if record_type in {"predicted_tc", "measured_tc"}:
        if property_code != "tc":
            issues.append(_issue(f"{path}.property_code", "schema_validation_failed", "Tc 记录必须使用 property_code=tc"))
        if not method_code:
            issues.append(_issue(f"{path}.method_code", "schema_validation_failed", "Tc 记录必须指定方法"))
        if record_type == "predicted_tc":
            if method_code not in THEORETICAL_METHODS:
                issues.append(_issue(f"{path}.method_code", "schema_validation_failed", "预测 Tc 方法无效"))
            if not isinstance(item["payload"].get("calculation_conditions"), dict) or item["payload"].get("experimental_conditions") is not None:
                issues.append(_issue(f"{path}.payload", "invalid_condition_type", "预测 Tc 必须使用计算 Conditions"))
        else:
            if method_code not in EXPERIMENTAL_METHODS:
                issues.append(_issue(f"{path}.method_code", "schema_validation_failed", "测量 Tc 方法无效"))
            if not isinstance(item["payload"].get("experimental_conditions"), dict) or item["payload"].get("calculation_conditions") is not None:
                issues.append(_issue(f"{path}.payload", "invalid_condition_type", "测量 Tc 必须使用实验 Conditions"))
        if item.get("canonical_unit") not in {None, "K"}:
            issues.append(_issue(f"{path}.canonical_unit", "schema_validation_failed", "Tc 规范单位必须为 K"))
    if property_code == "custom":
        if record_type != "property" or not str(item.get("custom_property_key") or "").strip():
            issues.append(_issue(f"{path}.custom_property_key", "custom_property_conflict", "自定义性质必须具有 custom_property_key"))
    elif str(item.get("custom_property_key") or "").strip():
        issues.append(_issue(f"{path}.custom_property_key", "schema_validation_failed", "规范性质不能携带自定义键"))
    _validate_value_shape(item, path, issues)
    if definition is not None:
        if definition.status not in {"published", "retired"}:
            issues.append(_issue(f"{path}.definition_version", "definition_not_available", "定义版本不可用于记录"))
        if definition.module_code != module_code or (definition.record_type and definition.record_type != record_type):
            issues.append(_issue(f"{path}.definition_key", "schema_validation_failed", "定义与记录类型不匹配"))
        _validate_schema(item["payload"], definition.json_schema or {}, f"{path}.payload", issues)
    if issues:
        raise PropertyValidationError(issues)
    item["record_checksum"] = record_checksum(item)
    return item


def normalize_module(module: dict[str, Any], *, paper_id: int, paper_revision: int) -> dict[str, Any]:
    item = deepcopy(module)
    code = str(item.get("module_code") or "").strip()
    if code not in MODULE_CODES:
        raise PropertyValidationError([_issue("module_code", "unknown_module", "未注册的物性模块")])
    item["module_code"] = code
    item["module_key"] = str(item.get("module_key") or f"module-{code}").strip()
    item["paper_id"] = paper_id
    item["paper_revision"] = paper_revision
    item["display_order"] = max(0, int(item.get("display_order") or 0))
    item["records"] = [validate_record({**record, "module_code": code}, path=f"module[{code}].records[{index}]") for index, record in enumerate(item.get("records") or []) if isinstance(record, dict)]
    return item


async def persist_property_modules(session: Any, *, paper_id: int, paper_revision: int, material_state_id: int, modules: list[dict[str, Any]], deleted_record_keys: list[str] | None = None, deleted_module_keys: list[str] | None = None) -> list[models.PropertyRecord]:
    """在一个事务中保存模块和记录；删除必须通过显式列表请求。"""
    deleted_record_keys = set(deleted_record_keys or [])
    deleted_module_keys = set(deleted_module_keys or [])
    result = await session.execute(select(models.PropertyModule).where(models.PropertyModule.material_state_id == material_state_id))
    existing = {item.module_key: item for item in (result.scalars().all() if hasattr(result, "scalars") else [])}
    output: list[models.PropertyRecord] = []
    seen_modules: set[str] = set()
    for raw_module in modules:
        module = normalize_module(raw_module, paper_id=paper_id, paper_revision=paper_revision)
        if module["module_key"] in seen_modules:
            raise PropertyValidationError([_issue("property_modules", "schema_validation_failed", "模块键重复")])
        seen_modules.add(module["module_key"])
        db_module = existing.get(module["module_key"])
        if db_module is None:
            db_module = models.PropertyModule(
                module_key=module["module_key"], paper_id=paper_id, paper_revision=paper_revision,
                material_state_id=material_state_id, module_code=module["module_code"],
                definition_key=module.get("definition_key") or "module.property",
                definition_version=int(module.get("definition_version") or 1),
                display_order=module["display_order"], metadata_json=module.get("metadata") or {},
            )
            session.add(db_module)
            await session.flush()
        existing_records = {record.record_key: record for record in getattr(db_module, "records", [])}
        representative: set[tuple[str, str]] = set()
        for record in module["records"]:
            if record["record_key"] in deleted_record_keys:
                continue
            if record.get("is_representative") and record["record_type"] in {"predicted_tc", "measured_tc"}:
                key = (record["record_type"], record.get("method_code") or "")
                if key in representative:
                    raise PropertyValidationError([_issue(f"{module['module_key']}.{record['record_key']}", "duplicate_representative_tc", "同一类型和方法只能有一条代表 Tc")])
                representative.add(key)
            if not record.get("definition_id") and record.get("definition_key"):
                definition_result = await session.execute(select(models.FormDefinition).where(
                    models.FormDefinition.definition_key == record["definition_key"],
                    models.FormDefinition.version == int(record.get("definition_version") or 1),
                ))
                definition = definition_result.scalars().first() if hasattr(definition_result, "scalars") else None
                if definition is not None:
                    record["definition_id"] = definition.id
                    validate_record(record, definition, path=f"module[{module['module_key']}].records[{record['record_key']}]")
                elif getattr(session, "bind", None) is not None:
                    raise PropertyValidationError([_issue(record["record_key"], "unknown_definition_version", "定义版本不存在")])
            db_record = existing_records.get(record["record_key"])
            values = {
                "record_key": record["record_key"], "paper_id": paper_id, "paper_revision": paper_revision,
                "material_state_id": material_state_id, "module_id": db_module.id,
                "record_type": record["record_type"], "property_code": record["property_code"],
                "custom_property_key": record.get("custom_property_key"),
                "definition_id": record.get("definition_id") or 0, "definition_key": record.get("definition_key") or "",
                "definition_version": int(record.get("definition_version") or 1), "name_raw": record["name_raw"],
                "value_kind": record["value_kind"], "value_raw": record["value_raw"],
                "value_number": record.get("value_number"), "value_min": record.get("value_min"), "value_max": record.get("value_max"),
                "value_text": record.get("value_text"), "value_boolean": record.get("value_boolean"), "uncertainty": record.get("uncertainty"),
                "unit_raw": record.get("unit_raw"), "canonical_unit": record.get("canonical_unit"), "method_code": record.get("method_code"),
                "method_raw": record.get("method_raw"), "criterion_code": record.get("criterion_code"), "criterion_raw": record.get("criterion_raw"),
                "is_representative": bool(record.get("is_representative", False)), "structure_key": record.get("structure_key"),
                "payload_json": record["payload"], "source_fingerprint": record.get("source_fingerprint") or hashlib.sha256(record["record_key"].encode()).hexdigest(),
                "record_checksum": record["record_checksum"],
            }
            if db_record is None:
                db_record = models.PropertyRecord(**values)
                db_module.records.append(db_record)
                session.add(db_record)
            else:
                for key, value in values.items():
                    if key not in {"module_id", "material_state_id", "paper_id", "paper_revision"}:
                        setattr(db_record, key, value)
            output.append(db_record)
        for key in deleted_record_keys:
            if key in existing_records:
                await session.delete(existing_records[key])
        if module["module_key"] in deleted_module_keys:
            if existing_records and any(key not in deleted_record_keys for key in existing_records):
                raise PropertyValidationError([_issue(module["module_key"], "nonempty_module_delete", "非空模块必须先显式删除全部记录")])
            await session.delete(db_module)
    return output
