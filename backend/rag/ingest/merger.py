"""
merger.py — 提取结果合并模块。

将 extractor（第一轮）和 cross_check（第二轮）的结果合并为最终数据。
"""

from __future__ import annotations

from typing import Any

from backend.rag.ingest.extractor import ExtractionResult, _parse_result


def merge(
    first_result: ExtractionResult,
    cross_check_result: dict[str, Any],
) -> ExtractionResult:
    """合并两轮提取结果。

    处理逻辑：
    1. 删除重复的数据点（按索引）
    2. 应用字段修正
    3. 追加遗漏的数据点
    4. 保留第一轮的论文元信息不变

    Args:
        first_result: 第一轮提取结果
        cross_check_result: 第二轮验证结果

    Returns:
        合并后的 ExtractionResult
    """
    data_points = list(first_result.data_points)
    corrections = cross_check_result.get("corrections") or []
    duplicates = cross_check_result.get("duplicates_to_remove") or []
    missing = cross_check_result.get("missing_data_points") or []

    # 1. 删除重复行（从后往前删，避免索引错位）
    for idx in sorted(duplicates, reverse=True):
        if 0 <= idx < len(data_points):
            deleted = data_points.pop(idx)
            print(f"    [合并] 删除重复行 #{idx}: {deleted.get('chemical_formula')}")

    # 2. 应用修正
    for corr in corrections:
        dp_idx = corr.get("data_point_index")
        field = corr.get("field")
        corrected = corr.get("corrected")

        if dp_idx is not None and 0 <= dp_idx < len(data_points) and field and corrected is not None:
            original = data_points[dp_idx].get(field)
            data_points[dp_idx][field] = corrected
            print(f"    [合并] 修正 #{dp_idx}.{field}: {original} → {corrected}")

    # 3. 追加遗漏的数据点
    added_count = 0
    for item in missing:
        if not isinstance(item, dict):
            continue
        # 标准化字段
        cleaned = {
            "chemical_formula": item.get("chemical_formula"),
            "pressure_gpa": _to_float(item.get("pressure_gpa")),
            "space_group_symbol": item.get("space_group_symbol"),
            "tc_k": _to_float(item.get("tc_k")),
            "lambda_value": _to_float(item.get("lambda_value")),
            "omega_log": _to_float(item.get("omega_log")),
            "n_ef_total": _to_float(item.get("n_ef_total")),
            "crystal_structure": item.get("crystal_structure"),
            "energy_above_hull": _to_float(item.get("energy_above_hull")),
            "source_label": "paper",
        }
        data_points.append(cleaned)
        added_count += 1

    if added_count:
        print(f"    [合并] 追加遗漏数据点: {added_count} 条")

    # 4. 构建合并后的结果
    merged_dict = dict(first_result.raw_json or {}) if first_result.raw_json else {}
    merged_dict["data_points"] = data_points

    merged = _parse_result(merged_dict)

    # 保留第一轮的基本信息
    merged.paper = first_result.paper
    merged.summary = first_result.summary
    merged.keywords_tags = first_result.keywords_tags
    merged.paper_type = first_result.paper_type

    return merged


def _to_float(v) -> float | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None
