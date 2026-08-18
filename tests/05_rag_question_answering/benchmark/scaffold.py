"""Phase 0 的无依赖配置与 fixture 加载器。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator


EXPECTED_ABLATION_TOOLS = {
    "llm_only": [],
    "qdrant_only": ["search_literature"],
    "qdrant_mysql": ["search_literature", "query_properties"],
    "qdrant_mysql_neo4j": [
        "search_literature",
        "query_properties",
        "search_papers",
        "paper_context",
        "material_info",
        "explore_graph",
        "paper_path",
    ],
}


def load_json(path: Path) -> dict[str, Any]:
    """读取 UTF-8 JSON 对象。"""

    with path.open(encoding="utf-8") as stream:
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError(f"JSON 顶层必须是对象: {path}")
    return value


def iter_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """逐行读取 JSONL，拒绝空行和非对象记录。"""

    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, start=1):
            if not line.strip():
                raise ValueError(f"JSONL 不允许空行: {path}:{line_number}")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"JSONL 记录必须是对象: {path}:{line_number}")
            yield value


def assert_development_question(record: dict[str, Any]) -> None:
    """验证 Phase 0 fixture 的最小安全边界。"""

    required = {"schema_version", "question_id", "split", "question_type", "question"}
    missing = required - record.keys()
    if missing:
        raise ValueError(f"问题记录缺少字段: {sorted(missing)}")
    if record["split"] != "development":
        raise ValueError("PDF Gate 前 fixture 只能使用 development split")
