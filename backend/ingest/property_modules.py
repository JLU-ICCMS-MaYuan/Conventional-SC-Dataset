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
    if "allOf" in schema:
        for child in schema["allOf"]:
            _validate_schema(value, child, path, issues)
    if "anyOf" in schema:
        if not any(_schema_matches(value, child) for child in schema["anyOf"]):
            issues.append(_issue(path, "schema_validation_failed", "字段不匹配任何允许结构"))
            return
    if "oneOf" in schema:
        if sum(_schema_matches(value, child) for child in schema["oneOf"]) != 1:
            issues.append(_issue(path, "schema_validation_failed", "字段必须且只能匹配一个允许结构"))
            return
    if "if" in schema:
        branch = schema.get("then") if _schema_matches(value, schema["if"]) else schema.get("else")
        if isinstance(branch, dict):
            _validate_schema(value, branch, path, issues)
    if "const" in schema and value != schema["const"]:
        issues.append(_issue(path, "schema_validation_failed", "字段必须匹配固定值"))
        return
    if "enum" in schema and value not in schema["enum"]:
        issues.append(_issue(path, "schema_validation_failed", "字段值不在允许枚举中"))
        return
    expected = schema.get("type")
    if isinstance(expected, list):
        if not any(_type_matches(value, candidate) for candidate in expected):
            issues.append(_issue(path, "schema_validation_failed", "字段类型不匹配"))
            return
        expected = next((candidate for candidate in expected if _type_matches(value, candidate)), None)
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
        elif isinstance(schema.get("additionalProperties"), dict):
            for name in value:
                if name not in properties:
                    _validate_schema(value[name], schema["additionalProperties"], f"{path}.{name}", issues)
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
        elif "maxLength" in schema and len(value) > schema["maxLength"]:
            issues.append(_issue(path, "schema_validation_failed", "字符串长度超限"))
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是数字"))
        elif "minimum" in schema and value < schema["minimum"]:
            issues.append(_issue(path, "schema_validation_failed", "字段值小于最小值"))
        elif "maximum" in schema and value > schema["maximum"]:
            issues.append(_issue(path, "schema_validation_failed", "字段值大于最大值"))
    elif expected == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            issues.append(_issue(path, "schema_validation_failed", "字段必须是整数"))
        elif "minimum" in schema and value < schema["minimum"]:
            issues.append(_issue(path, "schema_validation_failed", "字段值小于最小值"))
        elif "maximum" in schema and value > schema["maximum"]:
            issues.append(_issue(path, "schema_validation_failed", "字段值大于最大值"))
    elif expected == "boolean" and not isinstance(value, bool):
        issues.append(_issue(path, "schema_validation_failed", "字段必须是布尔值"))
    elif expected == "null" and value is not None:
        issues.append(_issue(path, "schema_validation_failed", "字段必须为空"))


def _type_matches(value: Any, expected: str) -> bool:
    return {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, (int, float, Decimal)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }.get(expected, True)


def _schema_matches(value: Any, schema: dict[str, Any]) -> bool:
    candidate_issues: list[PropertyIssue] = []
    _validate_schema(value, schema, "candidate", candidate_issues)
    return not candidate_issues


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
    if kind == "range" and record.get("value_min") is not None and record.get("value_max") is not None and record["value_min"] > record["value_max"]:
        issues.append(_issue(f"{path}.value_max", "schema_validation_failed", "范围上界必须不小于下界"))
    if record.get("uncertainty") is not None and record["uncertainty"] < 0:
        issues.append(_issue(f"{path}.uncertainty", "schema_validation_failed", "不确定度不能为负"))


def validate_record(
    record: dict[str, Any],
    definition: models.FormDefinition | None = None,
    path: str = "record",
    *,
    allow_retired: bool = False,
) -> dict[str, Any]:
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
        if item.get("canonical_unit") != "K":
            issues.append(_issue(f"{path}.canonical_unit", "schema_validation_failed", "Tc 规范单位必须为 K"))
        for value_field in ("value_number", "value_min", "value_max", "uncertainty"):
            if item.get(value_field) is not None and item[value_field] < 0:
                issues.append(_issue(f"{path}.{value_field}", "schema_validation_failed", "Tc 数值不能为负"))
    elif item.get("is_representative"):
        issues.append(_issue(f"{path}.is_representative", "schema_validation_failed", "只有 Tc 记录可以标记为代表结果"))
    if property_code == "custom":
        item["custom_property_key"] = str(item.get("custom_property_key") or "").strip()
        if record_type != "property" or not item["custom_property_key"]:
            issues.append(_issue(f"{path}.custom_property_key", "custom_property_conflict", "自定义性质必须具有 custom_property_key"))
    elif str(item.get("custom_property_key") or "").strip():
        issues.append(_issue(f"{path}.custom_property_key", "schema_validation_failed", "规范性质不能携带自定义键"))
    _validate_value_shape(item, path, issues)
    if definition is not None:
        if definition.status != "published" and not (allow_retired and definition.status == "retired"):
            issues.append(_issue(f"{path}.definition_version", "definition_not_available", "定义版本不可用于记录"))
        if definition.target_kind != "property_record":
            issues.append(_issue(f"{path}.definition_key", "schema_validation_failed", "定义目标不是物性记录"))
        if definition.definition_key != item.get("definition_key") or definition.version != int(item.get("definition_version") or 0):
            issues.append(_issue(f"{path}.definition_key", "schema_validation_failed", "记录绑定的定义键或版本不匹配"))
        if definition.module_code != module_code:
            issues.append(_issue(f"{path}.module_code", "schema_validation_failed", "定义与模块不匹配"))
        if definition.record_type and definition.record_type != record_type:
            issues.append(_issue(f"{path}.record_type", "schema_validation_failed", "定义与记录类型不匹配"))
        if definition.property_code and definition.property_code != property_code:
            issues.append(_issue(f"{path}.property_code", "schema_validation_failed", "定义与物性代码不匹配"))
        if definition.method_code and definition.method_code != method_code:
            issues.append(_issue(f"{path}.method_code", "schema_validation_failed", "定义与方法不匹配"))
        from backend.ingest.form_definitions import definition_checksum, definition_payload
        if definition.checksum != definition_checksum(definition_payload(definition)):
            issues.append(_issue(f"{path}.definition_version", "schema_checksum_mismatch", "定义内容与校验和不一致"))
        _validate_schema(item, definition.core_schema or {}, path, issues)
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


def _evidence_references(record: dict[str, Any]) -> list[dict[str, Any]]:
    references: list[dict[str, Any]] = []

    def add(items: Any, field_path: str) -> None:
        if not isinstance(items, list):
            return
        for item in items:
            if isinstance(item, int):
                references.append({"paper_evidence_id": item, "field_path": field_path, "evidence_role": "primary"})
            elif isinstance(item, dict) and item.get("paper_evidence_id", item.get("id")) is not None:
                references.append({
                    "paper_evidence_id": int(item.get("paper_evidence_id", item.get("id"))),
                    "field_path": str(item.get("field_path") or field_path),
                    "evidence_role": str(item.get("evidence_role") or "primary"),
                })

    add(record.get("evidences"), "")

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            add(value.get("evidences"), path)
            for key, child in value.items():
                if key != "evidences":
                    walk(child, f"{path}.{key}" if path else key)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")

    walk(record.get("payload") or {}, "payload")
    seen: dict[int, str] = {}
    for reference in references:
        evidence_id = reference["paper_evidence_id"]
        previous = seen.get(evidence_id)
        if previous is not None and previous != reference["field_path"]:
            raise PropertyValidationError([_issue(
                reference["field_path"], "extension_field_conflict",
                "同一 Evidence 在一条记录中不能绑定多个字段路径",
            )])
        seen[evidence_id] = reference["field_path"]
    return list({item["paper_evidence_id"]: item for item in references}.values())


def _custom_signature(record: Any) -> tuple[str, str, str]:
    value = record if isinstance(record, dict) else {
        "name_raw": record.name_raw,
        "value_kind": record.value_kind,
        "unit_raw": record.unit_raw,
    }
    return (
        str(value.get("name_raw") or "").strip().casefold(),
        str(value.get("value_kind") or ""),
        str(value.get("unit_raw") or "").strip().casefold(),
    )


async def persist_property_modules(session: Any, *, paper_id: int, paper_revision: int, material_state_id: int, modules: list[dict[str, Any]], deleted_record_keys: list[str] | None = None, deleted_module_keys: list[str] | None = None) -> list[models.PropertyRecord]:
    """在一个事务中保存模块和记录；删除必须通过显式列表请求。"""
    deleted_record_keys = set(deleted_record_keys or [])
    deleted_module_keys = set(deleted_module_keys or [])
    result = await session.execute(select(models.PropertyModule).where(models.PropertyModule.material_state_id == material_state_id))
    existing_modules = list(result.scalars().all())
    existing = {item.module_key: item for item in existing_modules}
    records_result = await session.execute(select(models.PropertyRecord).where(models.PropertyRecord.material_state_id == material_state_id))
    existing_records_list = list(records_result.scalars().all())
    module_key_by_id = {item.id: item.module_key for item in existing_modules}
    existing_records = {(module_key_by_id.get(item.module_id), item.record_key): item for item in existing_records_list}

    normalized_modules: list[dict[str, Any]] = []
    seen_modules: set[str] = set()
    seen_module_codes: set[str] = set()
    submitted_record_keys: set[tuple[str, str]] = set()
    for raw_module in modules:
        module = normalize_module(raw_module, paper_id=paper_id, paper_revision=paper_revision)
        if module["module_key"] in seen_modules or module["module_code"] in seen_module_codes:
            raise PropertyValidationError([_issue("property_modules", "schema_validation_failed", "模块键或模块代码重复")])
        seen_modules.add(module["module_key"])
        seen_module_codes.add(module["module_code"])
        for record in module["records"]:
            submitted_record_keys.add((module["module_key"], record["record_key"]))
        normalized_modules.append(module)

    for module_key in deleted_module_keys:
        db_module = existing.get(module_key)
        if db_module is None:
            continue
        retained = [
            item for item in existing_records_list
            if item.module_id == db_module.id and item.record_key not in deleted_record_keys
        ]
        if retained:
            raise PropertyValidationError([_issue(module_key, "nonempty_module_delete", "非空模块必须先显式删除全部记录")])

    definitions_result = await session.execute(select(models.FormDefinition))
    definitions = {
        (item.definition_key, item.version): item
        for item in definitions_result.scalars().all()
    }
    custom_signatures: dict[tuple[str, str], tuple[str, str, str]] = {}
    representative: set[tuple[str, str]] = set()
    for record in existing_records_list:
        module_key = module_key_by_id.get(record.module_id)
        if record.record_key in deleted_record_keys or (module_key, record.record_key) in submitted_record_keys:
            continue
        module = existing.get(module_key)
        if record.is_representative and record.record_type in {"predicted_tc", "measured_tc"}:
            representative.add((record.record_type, record.method_code or ""))
        if record.property_code == "custom" and record.custom_property_key and module:
            custom_signatures[(module.module_code, record.custom_property_key)] = _custom_signature(record)

    evidence_by_record: dict[tuple[str, str], list[dict[str, Any]]] = {}
    evidence_ids: set[int] = set()
    from backend.ingest.form_definitions import definition_checksum, definition_payload
    for module in normalized_modules:
        module_definition = definitions.get((module.get("definition_key") or f"module.{module['module_code']}", int(module.get("definition_version") or 1)))
        if module_definition is None or module_definition.status != "published" or module_definition.target_kind != "property_module" or module_definition.module_code != module["module_code"]:
            raise PropertyValidationError([_issue(module["module_key"], "unknown_definition_version", "模块定义版本不存在或不可用")])
        if module_definition.checksum != definition_checksum(definition_payload(module_definition)):
            raise PropertyValidationError([_issue(module["module_key"], "schema_checksum_mismatch", "模块定义校验和不匹配")])
        for record in module["records"]:
            definition = definitions.get((record.get("definition_key"), int(record.get("definition_version") or 1)))
            if definition is None:
                raise PropertyValidationError([_issue(record["record_key"], "unknown_definition_version", "定义版本不存在")])
            normalized = validate_record(record, definition, path=f"module[{module['module_key']}].records[{record['record_key']}]")
            record.clear()
            record.update(normalized)
            record["definition_id"] = definition.id
            if record.get("is_representative") and record["record_type"] in {"predicted_tc", "measured_tc"}:
                key = (record["record_type"], record.get("method_code") or "")
                if key in representative:
                    raise PropertyValidationError([_issue(record["record_key"], "duplicate_representative_tc", "同一类型和方法只能有一条代表 Tc")])
                representative.add(key)
            if record["property_code"] == "custom":
                custom_key = (module["module_code"], str(record.get("custom_property_key") or ""))
                signature = _custom_signature(record)
                if custom_key in custom_signatures and custom_signatures[custom_key] != signature:
                    raise PropertyValidationError([_issue(record["record_key"], "custom_property_conflict", "同一自定义性质键的名称、类型或单位不一致")])
                custom_signatures[custom_key] = signature
            references = _evidence_references(record)
            evidence_by_record[(module["module_key"], record["record_key"])] = references
            evidence_ids.update(item["paper_evidence_id"] for item in references)

    valid_evidence_ids: set[int] = set()
    if evidence_ids:
        evidence_result = await session.execute(select(models.PaperEvidence).where(
            models.PaperEvidence.id.in_(evidence_ids),
            models.PaperEvidence.paper_id == paper_id,
            models.PaperEvidence.paper_revision == paper_revision,
        ))
        valid_evidence_ids = {item.id for item in evidence_result.scalars().all()}
        missing = sorted(evidence_ids - valid_evidence_ids)
        if missing:
            raise PropertyValidationError([_issue("evidences", "cross_revision_reference", f"Evidence 不属于当前论文 revision: {missing[0]}")])

    output: list[models.PropertyRecord] = []
    for module in normalized_modules:
        if module["module_key"] in deleted_module_keys:
            continue
        db_module = existing.get(module["module_key"])
        if db_module is None:
            db_module = models.PropertyModule(
                module_key=module["module_key"], paper_id=paper_id, paper_revision=paper_revision,
                material_state_id=material_state_id, module_code=module["module_code"],
                definition_key=module.get("definition_key") or f"module.{module['module_code']}",
                definition_version=int(module.get("definition_version") or 1),
                display_order=module["display_order"], metadata_json=module.get("metadata") or {},
            )
            session.add(db_module)
            await session.flush()
        for record in module["records"]:
            if record["record_key"] in deleted_record_keys:
                continue
            db_record = existing_records.get((module["module_key"], record["record_key"]))
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
                session.add(db_record)
                await session.flush()
            else:
                for key, value in values.items():
                    if key not in {"module_id", "material_state_id", "paper_id", "paper_revision"}:
                        setattr(db_record, key, value)
                await session.flush()
            references = evidence_by_record[(module["module_key"], record["record_key"])]
            if "evidences" in record or references:
                link_result = await session.execute(select(models.PropertyRecordEvidence).where(models.PropertyRecordEvidence.record_id == db_record.id))
                for link in link_result.scalars().all():
                    await session.delete(link)
                await session.flush()
                for reference in references:
                    session.add(models.PropertyRecordEvidence(
                        record_id=db_record.id,
                        paper_evidence_id=reference["paper_evidence_id"],
                        paper_id=paper_id,
                        paper_revision=paper_revision,
                        field_path=reference["field_path"],
                        evidence_role=reference["evidence_role"],
                    ))
            output.append(db_record)

    records_to_delete = [item for item in existing_records_list if item.record_key in deleted_record_keys]
    for record in records_to_delete:
        links = await session.execute(select(models.PropertyRecordEvidence).where(models.PropertyRecordEvidence.record_id == record.id))
        for link in links.scalars().all():
            await session.delete(link)
        await session.delete(record)
    if records_to_delete:
        await session.flush()
    for module_key in deleted_module_keys:
        db_module = existing.get(module_key)
        if db_module is not None:
            await session.delete(db_module)
    return output
