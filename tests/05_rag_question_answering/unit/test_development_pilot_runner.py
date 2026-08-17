"""development pilot runner 的公共行为。"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.runners.development_pilot import inspect_question, run_pilot  # noqa: E402


def test_unavailable_required_tool_blocks_question() -> None:
    question = {
        "question_id": "q1", "question_type": "mechanism",
        "question": "这个机制的证据是什么？", "answerability": "answerable",
        "required_tools": ["search_literature"],
    }
    result = inspect_question(
        question,
        {"status": "blocked_dependency"},
        {"tools": {"search_literature": {"available": False, "reason": "missing_key"}}},
    )

    assert result["status"] == "blocked_tool"
    assert result["pdf_verified"] is False


def test_runner_refuses_to_overwrite_experiment_directory(tmp_path: Path) -> None:
    kwargs = {
        "questions_path": TEST_ROOT / "fixtures/development-pilot-20.jsonl",
        "temporary_gold_path": TEST_ROOT / "fixtures/development-temporary-gold.jsonl",
        "capabilities_path": TEST_ROOT / "fixtures/development-capabilities.json",
        "output_root": tmp_path,
        "experiment_id": "same-id",
    }
    metadata = run_pilot(**kwargs)

    assert metadata["question_count"] == 20
    with pytest.raises(FileExistsError):
        run_pilot(**kwargs)
