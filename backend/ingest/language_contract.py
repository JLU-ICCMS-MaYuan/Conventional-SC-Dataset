"""上传解析中 AI 生成字段的语言约束。"""

from __future__ import annotations

import re
from typing import Any


_CJK_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")
_PAPER_GENERATED_FIELDS = (
    "summary",
    "keywords_tags",
    "methodology",
    "key_finding",
    "research_motivation",
    "knowledge_graph_title",
    "research_materials",
)


class GeneratedFieldLanguageError(ValueError):
    """LLM 在要求英文的字段中返回了中日韩字符。"""

    def __init__(self, path: str):
        self.path = path
        super().__init__(f"generated_field_must_be_english: {path}")


def _require_english(value: Any, path: str) -> None:
    if isinstance(value, str) and _CJK_PATTERN.search(value):
        raise GeneratedFieldLanguageError(path)
    if isinstance(value, list):
        for index, item in enumerate(value):
            _require_english(item, f"{path}[{index}]")


def validate_draft_generated_english(draft: dict[str, Any]) -> None:
    """只校验 AI 归纳字段，保留标题、摘要和 quote 等原文事实。"""
    paper = draft.get("paper") if isinstance(draft.get("paper"), dict) else {}
    for field in _PAPER_GENERATED_FIELDS:
        _require_english(paper.get(field), f"paper.{field}")

    for index, selection in enumerate(paper.get("material_families") or []):
        if isinstance(selection, dict):
            _require_english(selection.get("name"), f"paper.material_families[{index}].name")

    _require_english(draft.get("research_motivation"), "research_motivation")
    for state_index, state in enumerate(draft.get("material_states") or []):
        if not isinstance(state, dict):
            continue
        _require_english(state.get("material"), f"material_states[{state_index}].material")
        for family_index, family in enumerate(state.get("structure_families") or []):
            if isinstance(family, dict):
                _require_english(
                    family.get("name"),
                    f"material_states[{state_index}].structure_families[{family_index}].name",
                )
        for property_index, property_value in enumerate(state.get("properties") or []):
            if isinstance(property_value, dict):
                _require_english(
                    property_value.get("name"),
                    f"material_states[{state_index}].properties[{property_index}].name",
                )


def validate_chunk_generated_english(result: dict[str, Any]) -> None:
    """校验分段候选的 AI 归纳字段，不检查 quote 或 metadata 原文。"""
    for field in ("research_materials", "methodology", "key_findings"):
        for index, item in enumerate(result.get(field) or []):
            if isinstance(item, dict):
                for key in ("name", "material", "value", "method", "finding", "text"):
                    _require_english(item.get(key), f"{field}[{index}].{key}")
            else:
                _require_english(item, f"{field}[{index}]")

    for index, item in enumerate(result.get("material_relations") or []):
        if isinstance(item, dict):
            _require_english(item.get("material"), f"material_relations[{index}].material")
            _require_english(item.get("relation"), f"material_relations[{index}].relation")

    for state_index, state in enumerate(result.get("material_states") or []):
        if not isinstance(state, dict):
            continue
        _require_english(state.get("material"), f"material_states[{state_index}].material")
        family = state.get("material_family")
        if isinstance(family, dict):
            _require_english(
                family.get("name") or family.get("value"),
                f"material_states[{state_index}].material_family",
            )
        for family_index, family in enumerate(state.get("structure_families") or []):
            if isinstance(family, dict):
                _require_english(
                    family.get("name") or family.get("value"),
                    f"material_states[{state_index}].structure_families[{family_index}]",
                )
