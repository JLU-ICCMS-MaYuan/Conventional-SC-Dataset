"""验证 Phase 0 骨架无需外部服务即可运行。"""

from __future__ import annotations

import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.scaffold import (  # noqa: E402
    EXPECTED_ABLATION_TOOLS,
    assert_development_question,
    iter_jsonl,
    load_json,
)


def test_four_ablation_groups_are_exactly_frozen() -> None:
    config = load_json(TEST_ROOT / "benchmark/configs/ablation-groups.json")

    assert config["schema_version"] == "1.0.0"
    assert config["groups"] == EXPECTED_ABLATION_TOOLS


def test_llm_only_has_no_hidden_tool_access() -> None:
    assert EXPECTED_ABLATION_TOOLS["llm_only"] == []


def test_synthetic_questions_are_development_only_and_unique() -> None:
    records = list(iter_jsonl(TEST_ROOT / "fixtures/questions.synthetic.jsonl"))
    question_ids = []

    for record in records:
        assert_development_question(record)
        question_ids.append(record["question_id"])

    assert question_ids
    assert len(question_ids) == len(set(question_ids))


def test_versioned_schemas_are_present() -> None:
    question_schema = load_json(TEST_ROOT / "benchmark/schemas/question.schema.json")
    run_schema = load_json(TEST_ROOT / "benchmark/schemas/run-record.schema.json")

    assert question_schema["properties"]["schema_version"]["const"] == "1.0.0"
    assert run_schema["properties"]["schema_version"]["const"] == "1.0.0"
