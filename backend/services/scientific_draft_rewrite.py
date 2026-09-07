"""科学数据整体重写：单事务内删除论文当前科学实体并按请求体重建。

Issue #76：管理员在审核编辑页修改材料状态、Tc、普通物性与结构附件。
语义是整体替换而非增量更新（契约 scientific-draft-api.md C1），
删除顺序严格复用 goserver/handlers/paper_deletion.go 已验证的依赖逆序（R4）。

本模块只负责删除与版本字段更新；重建由 backend/ingest/scientific_drafts.py
的 persist_scientific_draft 承担（与上传提交链路同实现，保证产出一致）。
"""
from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models
from backend.ingest.property_modules import normalize_module
from backend.ingest.scientific_drafts import (
    _number,
    _property_modules_for_state,
    count_formula_elements,
)
from backend.services.space_groups import CRYSTAL_SYSTEMS
from backend.models import Paper
from backend.ingest.upload_contracts import convert_legacy_state


def _canonical_value(value: Any) -> Any:
    """把数值与 JSON 值规整为可跨 MySQL/Python 比较的形态。"""
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, float):
        return format(Decimal(str(value)).normalize(), "f")
    if isinstance(value, dict):
        return {str(key): _canonical_value(item) for key, item in sorted(value.items())}
    if isinstance(value, list):
        return [_canonical_value(item) for item in value]
    if isinstance(value, str):
        try:
            return _canonical_value(json.loads(value))
        except (TypeError, ValueError):
            return value
    return value


def _sorted_snapshot(items: list[dict[str, Any]]) -> list[str]:
    return sorted(
        json.dumps(_canonical_value(item), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for item in items
    )


def _record_snapshot(record: Any, *, module_code: str) -> dict[str, Any]:
    get = record.get if isinstance(record, dict) else lambda name, default=None: getattr(record, name, default)
    return {
        "record_key": get("record_key"),
        "module_code": module_code,
        "record_type": get("record_type"),
        "property_code": get("property_code"),
        "custom_property_key": get("custom_property_key"),
        "definition_key": get("definition_key"),
        "definition_version": int(get("definition_version") or 1),
        "name_raw": get("name_raw"),
        "value_kind": get("value_kind"),
        "value_raw": get("value_raw"),
        "value_number": get("value_number"),
        "value_min": get("value_min"),
        "value_max": get("value_max"),
        "value_text": get("value_text"),
        "value_boolean": get("value_boolean"),
        "uncertainty": get("uncertainty"),
        "unit_raw": get("unit_raw"),
        "canonical_unit": get("canonical_unit"),
        "method_code": get("method_code"),
        "method_raw": get("method_raw"),
        "criterion_code": get("criterion_code"),
        "criterion_raw": get("criterion_raw"),
        "is_representative": bool(get("is_representative")),
        "structure_key": get("structure_key"),
        "payload": get("payload") if isinstance(record, dict) else get("payload_json") or {},
    }


def _module_snapshot(module: dict[str, Any]) -> dict[str, Any]:
    code = module["module_code"]
    return {
        "module_key": module["module_key"],
        "module_code": code,
        "definition_key": module.get("definition_key") or f"module.{code}",
        "definition_version": int(module.get("definition_version") or 1),
        "display_order": int(module.get("display_order") or 0),
        "metadata": module.get("metadata") or {},
        "records": sorted(
            (_record_snapshot(record, module_code=code) for record in module.get("records") or []),
            key=lambda item: str(item["record_key"]),
        ),
    }


def _calculation_snapshot(values: Any, *, has_structure: bool) -> dict[str, Any]:
    get = values.get if isinstance(values, dict) else lambda name, default=None: getattr(values, name, default)
    return {
        "has_structure": has_structure,
        "missing_structure_reason": (
            None if has_structure
            else get("missing_structure_reason") or "论文未提供或未提取完整结构文本"
        ),
        "phonon_nuclear_treatment": get("phonon_nuclear_treatment") or "unknown",
        "lambda_ep": _number(get("lambda_ep")),
        "omega_log_k": _number(get("omega_log_k")),
        "mu_star": _number(get("mu_star")),
        "epc_method": get("epc_method"),
        "calculation_code": get("calculation_code"),
        "parameters_json": _canonical_value(get("parameters_json")),
    }


def _experimental_snapshot(values: Any, *, has_structure: bool) -> dict[str, Any]:
    get = values.get if isinstance(values, dict) else lambda name, default=None: getattr(values, name, default)
    return {
        "has_structure": has_structure,
        "sample_label": get("sample_label"),
        "measurement_method": get("measurement_method"),
        "tc_criterion": get("tc_criterion") or "unknown",
        "applied_field_t": _number(get("applied_field_t")),
        "pressure_uncertainty_gpa": _number(get("pressure_uncertainty_gpa")),
        "parameters_json": _canonical_value(get("parameters_json")),
    }


def _tc_snapshot(
    values: Any,
    *,
    has_calculation_context: bool,
    has_experimental_context: bool,
) -> dict[str, Any]:
    get = values.get if isinstance(values, dict) else lambda name, default=None: getattr(values, name, default)
    requested_kind = get("result_kind") or "theoretical"
    method = get("tc_method") or ("experimental" if requested_kind == "experimental" else "unknown")
    result_kind = "experimental" if method == "experimental" else "theoretical"
    return {
        "result_kind": result_kind,
        "tc_method": method,
        "tc_method_custom": (get("tc_method_custom") or None) if method == "other" else None,
        "tc_value_k": _number(get("tc_value_k")),
        "tc_min_k": _number(get("tc_min_k")),
        "tc_max_k": _number(get("tc_max_k")),
        "uncertainty_k": _number(get("uncertainty_k")),
        "value_raw": str(get("value_raw") or get("tc_value_k") or "").strip(),
        "unit_raw": str(get("unit_raw") or "K"),
        "has_calculation_context": has_calculation_context,
        "has_experimental_context": has_experimental_context,
    }


def _property_snapshot(
    values: Any,
    *,
    material: str,
    has_structure: bool,
    has_calculation_context: bool,
) -> dict[str, Any]:
    get = values.get if isinstance(values, dict) else lambda name, default=None: getattr(values, name, default)
    value_min = _number(get("value_min"))
    value_max = _number(get("value_max"))
    value_number = _number(get("value") if isinstance(values, dict) else get("value_number"))
    value_kind = "range" if value_min is not None and value_max is not None else "number" if value_number is not None else "text"
    return {
        "material": material,
        "name_raw": str(get("name_raw") or get("name") or "").strip(),
        "value_raw": str(get("value_raw") or (get("value") if isinstance(values, dict) else get("value_number")) or "").strip(),
        "unit": get("unit") if isinstance(values, dict) else get("unit_raw"),
        "value_number": value_number if value_kind == "number" else None,
        "value_min": value_min,
        "value_max": value_max,
        "canonical_unit": get("unit") if isinstance(values, dict) else get("canonical_unit"),
        "condition_note": get("condition_note"),
        "has_structure": has_structure,
        "has_calculation_context": has_calculation_context,
    }


def _structure_snapshot(
    *,
    space_group_symbol: Any,
    space_group_number: Any,
    structure_format: Any,
    structure_text: Any,
    nuclear_treatment: Any,
) -> dict[str, Any]:
    return {
        "space_group_symbol": space_group_symbol,
        "space_group_number": space_group_number,
        "structure_format": structure_format or "unknown",
        "structure_text": str(structure_text or ""),
        "nuclear_treatment": nuclear_treatment or "unknown",
    }


def _requested_scientific_snapshot(paper: Paper, draft: dict[str, Any]) -> dict[str, Any]:
    """按 persist_scientific_draft 的真实写入规则生成请求快照。

    只纳入会保存到科学实体图的字段。证据、候选来源文件名、主键与创建时间都不是
    编辑页可修改的科学内容，不能令一次同值保存被误判为修改。
    """
    states: list[dict[str, Any]] = []
    confirmed_candidates: dict[int, list[dict[str, Any]]] = {}
    for candidate in draft.get("structure_candidates") or []:
        if not isinstance(candidate, dict):
            continue
        if candidate.get("confirmation") != "confirmed" or candidate.get("status") != "confirmed":
            continue
        reference = str(candidate.get("material_state_ref") or "")
        if reference.startswith("material_states[") and reference.endswith("]"):
            try:
                index = int(reference[len("material_states["):-1])
            except ValueError:
                continue
            confirmed_candidates.setdefault(index, []).append(candidate)

    for state_index, state_data in enumerate(draft.get("material_states") or []):
        if not isinstance(state_data, dict):
            continue
        material = str(state_data.get("material") or "").strip()
        dimensionality = str(state_data.get("material_dimensionality") or "unknown")
        crystal_system = state_data.get("crystal_system") or "unknown"
        if crystal_system not in CRYSTAL_SYSTEMS:
            crystal_system = "unknown"
        element_count = state_data.get("element_count")
        if not isinstance(element_count, int) or isinstance(element_count, bool):
            element_count = count_formula_elements(material)

        structures: list[dict[str, Any]] = []
        structure_data = state_data.get("structure")
        if isinstance(structure_data, dict) and str(structure_data.get("structure_text") or "").strip():
            structures.append(_structure_snapshot(
                space_group_symbol=structure_data.get("space_group_symbol") or state_data.get("reported_space_group_symbol"),
                space_group_number=structure_data.get("space_group_number") or state_data.get("reported_space_group_number"),
                structure_format=structure_data.get("structure_format"),
                structure_text=structure_data.get("structure_text"),
                nuclear_treatment=structure_data.get("nuclear_treatment"),
            ))
        for candidate in confirmed_candidates.get(state_index, []):
            representations = candidate.get("representations")
            conventional = representations.get("conventional") if isinstance(representations, dict) else None
            cif = conventional.get("cif") if isinstance(conventional, dict) else None
            structure_text = cif.get("text") if isinstance(cif, dict) else None
            if not str(structure_text or "").strip():
                continue
            calculation_data = state_data.get("calculation_context")
            structures.append(_structure_snapshot(
                space_group_symbol=state_data.get("reported_space_group_symbol"),
                space_group_number=state_data.get("reported_space_group_number"),
                structure_format="cif",
                structure_text=structure_text,
                nuclear_treatment=(calculation_data or {}).get("phonon_nuclear_treatment")
                if isinstance(calculation_data, dict) else "unknown",
            ))

        tc_items = [item for item in state_data.get("tc_results") or [] if isinstance(item, dict)]
        calculation_data = state_data.get("calculation_context")
        has_shared_calculation = isinstance(calculation_data, dict) or any(
            (item.get("tc_method") or "unknown") != "experimental" for item in tc_items
        )
        calculation_values = calculation_data if isinstance(calculation_data, dict) else {}
        calculations: list[dict[str, Any]] = []
        if has_shared_calculation:
            calculations.append(_calculation_snapshot(calculation_values, has_structure=bool(structures)))

        experiments: list[dict[str, Any]] = []
        experimental_data = state_data.get("experimental_context")
        has_experiment = isinstance(experimental_data, dict) or any(
            item.get("tc_method") == "experimental" for item in tc_items
        )
        if has_experiment:
            experiments.append(_experimental_snapshot(
                experimental_data if isinstance(experimental_data, dict) else {},
                has_structure=bool(structures),
            ))

        tc_results: list[dict[str, Any]] = []
        for item in tc_items:
            method = item.get("tc_method") or (
                "experimental" if item.get("result_kind") == "experimental" else "unknown"
            )
            item_calculation = item.get("calculation_context")
            has_item_calculation = method != "experimental" and isinstance(item_calculation, dict) and any(
                _number(item_calculation.get(key)) is not None
                for key in ("lambda_ep", "omega_log_k", "mu_star")
            )
            if has_item_calculation:
                calculations.append(_calculation_snapshot(item_calculation, has_structure=bool(structures)))
            tc_results.append(_tc_snapshot(
                item,
                has_calculation_context=method != "experimental" and (has_shared_calculation or has_item_calculation),
                has_experimental_context=method == "experimental" and has_experiment,
            ))

        properties = [
            _property_snapshot(
                item,
                material=material,
                has_structure=bool(structures),
                has_calculation_context=has_shared_calculation,
            )
            for item in state_data.get("properties") or []
            if isinstance(item, dict)
        ]
        states.append({
            "material": material,
            "element_count": element_count,
            "material_dimensionality": dimensionality,
            "pressure_value_gpa": _number(state_data.get("pressure_value_gpa")),
            "pressure_min_gpa": _number(state_data.get("pressure_min_gpa")),
            "pressure_max_gpa": _number(state_data.get("pressure_max_gpa")),
            "pressure_raw": state_data.get("pressure_raw"),
            "pressure_unit_raw": state_data.get("pressure_unit_raw"),
            "reported_space_group_symbol": state_data.get("reported_space_group_symbol"),
            "reported_space_group_number": state_data.get("reported_space_group_number"),
            "temperature_value_k": _number(state_data.get("temperature_value_k")),
            "temperature_raw": state_data.get("temperature_raw"),
            "temperature_unit_raw": state_data.get("temperature_unit_raw"),
            "magnetic_field_t": _number(state_data.get("magnetic_field_t")),
            "state_kind": state_data.get("state_kind") or "unknown",
            "crystal_system": crystal_system,
            "note": state_data.get("note"),
            "structures": _sorted_snapshot(structures),
            "calculations": _sorted_snapshot(calculations),
            "experiments": _sorted_snapshot(experiments),
            "tc_results": _sorted_snapshot(tc_results),
            "properties": _sorted_snapshot(properties),
        })
    return {
        "superconductor_kind": draft.get("paper", {}).get("superconductor_kind") or "unknown",
        "states": _sorted_snapshot(states),
    }


async def scientific_draft_matches_current_revision(
    session: AsyncSession,
    paper: Paper,
    draft: dict[str, Any],
) -> bool:
    """返回请求是否与当前科学数据语义相同，不做任何写入。"""
    requested = []
    for index, raw_state in enumerate(draft.get("material_states") or []):
        modules = [
            normalize_module(
                module,
                paper_id=paper.id,
                paper_revision=paper.content_revision or 1,
            )
            for module in _property_modules_for_state(raw_state)
        ]
        requested.append({
            "state_key": str(raw_state.get("state_key") or f"state-{index + 1}"),
            "material": str(raw_state.get("material") or "").strip(),
            "pressure_value_gpa": _number(raw_state.get("pressure_value_gpa")),
            "state_kind": raw_state.get("state_kind") or "unknown",
            "property_modules": _canonical_value(sorted(
                (_module_snapshot(module) for module in modules),
                key=lambda item: str(item["module_key"]),
            )),
        })
    revision = paper.content_revision or 1
    rows = (await session.execute(
        select(models.MaterialState, models.Superconductor.chemical_formula)
        .join(models.Superconductor, models.Superconductor.id == models.MaterialState.superconductor_id)
        .where(models.MaterialState.paper_id == paper.id, models.MaterialState.paper_revision == revision)
    )).all()
    stored = []
    for state, formula in rows:
        modules = (await session.execute(
            select(models.PropertyModule).where(models.PropertyModule.material_state_id == state.id)
        )).scalars().all()
        module_values = []
        for module in modules:
            records = (await session.execute(
                select(models.PropertyRecord).where(models.PropertyRecord.module_id == module.id)
            )).scalars().all()
            module_values.append({
                "module_key": module.module_key, "module_code": module.module_code,
                "definition_key": module.definition_key, "definition_version": module.definition_version,
                "display_order": module.display_order,
                "metadata": module.metadata_json or {},
                "records": sorted(
                    (_record_snapshot(record, module_code=module.module_code) for record in records),
                    key=lambda item: str(item["record_key"]),
                ),
            })
        stored.append({
            "state_key": state.state_key, "material": str(formula or "").strip(),
            "pressure_value_gpa": _number(state.pressure_value_gpa), "state_kind": state.state_kind,
            "property_modules": _canonical_value(sorted(
                module_values,
                key=lambda item: str(item["module_key"]),
            )),
        })
    return _sorted_snapshot(requested) == _sorted_snapshot(stored)


async def delete_scientific_entities(session: AsyncSession, paper_id: int) -> None:
    """按依赖逆序删除论文的科学实体，共 6 步。

    与 paper_deletion.go 的 cascadeDeleteInDB 前 6 步一致；本模块**不触碰**
    paper_evidences / paper_chunks / paper_files——它们的 paper_revision
    由外键级联自动更新（见 data-model.md 外键迁移）。
    """
    # Target records and their immutable audit/evidence dependencies.
    await session.execute(text("DELETE FROM property_record_evidences WHERE paper_id = :pid"), {"pid": paper_id})
    await session.execute(text("DELETE FROM property_record_definition_events WHERE paper_id = :pid"), {"pid": paper_id})
    await session.execute(text("DELETE FROM property_records WHERE paper_id = :pid"), {"pid": paper_id})
    await session.execute(text("DELETE FROM property_modules WHERE paper_id = :pid"), {"pid": paper_id})

    # Structure evidence remains part of the target graph.
    for table in (
        "structure_model_evidences",
    ):
        await session.execute(text(f"DELETE FROM {table} WHERE paper_id = :pid"), {"pid": paper_id})

    # structure_models：自引用 parent_structure_id 先置空再删，
    #    否则同论文内父子结构的删除先后顺序不定，可能触发外键错误。
    await session.execute(
        text(
            "UPDATE structure_models SET parent_structure_id = NULL "
            "WHERE paper_id = :pid AND parent_structure_id IS NOT NULL"
        ),
        {"pid": paper_id},
    )
    await session.execute(
        text("DELETE FROM structure_models WHERE paper_id = :pid"), {"pid": paper_id}
    )

    # 5. 连接表无 paper_id，按本论文的材料状态子查询删除
    await session.execute(
        text(
            "DELETE FROM material_state_structure_families "
            "WHERE material_state_id IN (SELECT id FROM material_states WHERE paper_id = :pid)"
        ),
        {"pid": paper_id},
    )

    # 6. 材料状态（此时全部子表已清空）
    await session.execute(
        text("DELETE FROM material_states WHERE paper_id = :pid"), {"pid": paper_id}
    )
    await session.execute(text("DELETE FROM superconductors WHERE paper_id = :pid"), {"pid": paper_id})
    await session.execute(text("DELETE FROM chemical_systems WHERE paper_id = :pid"), {"pid": paper_id})

async def bump_paper_revision(session: AsyncSession, paper: Paper) -> None:
    """升版：单条 UPDATE 三个版本字段，触发外键级联迁移血缘数据。

    三个字段必须同一条 UPDATE 写入（R7）：分多条会产生违约的中间状态。
    content_revision 条件同时充当并发保护——行数不为 1 说明版本已被并发修改。

    必须用 `synchronize_session=False`：默认的 auto 会把 UPDATE 结果同步回
    identity map 中已加载的 paper（content_revision 已 +1），再手动同步就会
    重复递增（1 → 2 → 3）。
    """
    result = await session.execute(
        update(Paper)
        .where(Paper.id == paper.id, Paper.content_revision == paper.content_revision)
        .values(
            content_revision=paper.content_revision + 1,
            approved_revision=None,
            review_status="pending",
        )
        .execution_options(synchronize_session=False)
    )
    if result.rowcount != 1:
        raise RuntimeError("升版失败：论文版本已被并发修改，请刷新后重试")
    # 手动同步 ORM 对象内存值，供 persist_scientific_draft 使用新版本号
    paper.content_revision += 1
    paper.approved_revision = None
    paper.review_status = "pending"
