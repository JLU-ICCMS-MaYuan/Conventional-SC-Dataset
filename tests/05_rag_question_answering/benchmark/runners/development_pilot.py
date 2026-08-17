"""运行不依赖PDF的20题流程pilot并生成不可覆盖产物。"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from benchmark.scaffold import iter_jsonl, load_json


def inspect_question(
    question: dict[str, Any],
    temporary_gold: dict[str, Any],
    capabilities: dict[str, Any],
) -> dict[str, Any]:
    """检查题目清晰度、工具可用性和临时gold状态。"""

    text = question["question"].strip()
    clarity_issues = []
    if not text.endswith(("？", "?")):
        clarity_issues.append("not_a_question")
    if not 10 <= len(text) <= 180:
        clarity_issues.append("length_out_of_range")
    if question["answerability"] == "unanswerable" and not question.get("unanswerable_reason"):
        clarity_issues.append("missing_unanswerable_reason")

    tools = capabilities["tools"]
    unavailable = [
        {"tool": name, "reason": tools.get(name, {}).get("reason", "not_probed")}
        for name in question.get("required_tools", [])
        if not tools.get(name, {}).get("available", False)
    ]

    if clarity_issues:
        status = "needs_revision"
    elif unavailable:
        status = "blocked_tool"
    elif temporary_gold["status"] == "pending_tool_run":
        status = "pending_tool_run"
    else:
        status = "ready_for_development"

    return {
        "schema_version": "1.0.0",
        "question_id": question["question_id"],
        "question_type": question["question_type"],
        "clarity_issues": clarity_issues,
        "required_tools": question.get("required_tools", []),
        "unavailable_tools": unavailable,
        "temporary_gold_status": temporary_gold["status"],
        "pdf_verified": False,
        "status": status,
    }


def run_pilot(
    questions_path: Path,
    temporary_gold_path: Path,
    capabilities_path: Path,
    output_root: Path,
    experiment_id: str,
) -> dict[str, Any]:
    """生成原始JSONL、汇总CSV和错误JSONL；目标目录存在则拒绝覆盖。"""

    output_dir = output_root / experiment_id
    output_dir.mkdir(parents=True, exist_ok=False)
    questions = list(iter_jsonl(questions_path))
    gold_by_id = {
        item["question_id"]: item for item in iter_jsonl(temporary_gold_path)
    }
    capabilities = load_json(capabilities_path)
    if set(gold_by_id) != {item["question_id"] for item in questions}:
        raise ValueError("临时gold必须与20题一一对应")

    records = [
        inspect_question(question, gold_by_id[question["question_id"]], capabilities)
        for question in questions
    ]
    raw_path = output_dir / "raw.jsonl"
    with raw_path.open("x", encoding="utf-8") as stream:
        for record in records:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    summary_path = output_dir / "summary.csv"
    counts = Counter(record["status"] for record in records)
    with summary_path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["status", "count"])
        for status, count in sorted(counts.items()):
            writer.writerow([status, count])

    errors_path = output_dir / "errors.jsonl"
    with errors_path.open("x", encoding="utf-8") as stream:
        for record in records:
            if record["status"] != "ready_for_development":
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")

    metadata = {
        "schema_version": "1.0.0",
        "experiment_id": experiment_id,
        "status": "development",
        "snapshot_id": capabilities["snapshot_id"],
        "pdf_gate": "blocked",
        "question_count": len(records),
        "counts": dict(sorted(counts.items())),
    }
    with (output_dir / "metadata.json").open("x", encoding="utf-8") as stream:
        json.dump(metadata, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return metadata


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--questions", dest="questions_path", type=Path, required=True)
    parser.add_argument("--temporary-gold", dest="temporary_gold_path", type=Path, required=True)
    parser.add_argument("--capabilities", dest="capabilities_path", type=Path, required=True)
    parser.add_argument("--output-root", dest="output_root", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    args = parser.parse_args()
    print(json.dumps(run_pilot(**vars(args)), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
