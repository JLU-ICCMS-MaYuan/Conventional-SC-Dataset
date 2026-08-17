"""20题 development pilot 的配额与证据门测试。"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.scaffold import assert_development_question, iter_jsonl, load_json  # noqa: E402


EXPECTED_QUOTA = {
    "numeric_fact": 3,
    "mechanism": 3,
    "literature_metadata": 2,
    "graph_single_hop": 3,
    "graph_multi_hop": 3,
    "hybrid": 3,
    "unanswerable": 3,
}


def test_development_pilot_has_frozen_twenty_question_quota() -> None:
    records = list(iter_jsonl(TEST_ROOT / "fixtures/development-pilot-20.jsonl"))

    assert len(records) == 20
    assert Counter(record["question_type"] for record in records) == EXPECTED_QUOTA
    assert len({record["question_id"] for record in records}) == 20
    for record in records:
        assert_development_question(record)


def test_development_pilot_cannot_claim_pdf_verified_evidence() -> None:
    records = iter_jsonl(TEST_ROOT / "fixtures/development-pilot-20.jsonl")

    assert all(
        not evidence.get("pdf_verified", False)
        for record in records
        for evidence in record["gold_evidence"]
    )


def test_gold_evidence_schema_requires_pdf_locator_when_verified() -> None:
    schema = load_json(TEST_ROOT / "benchmark/schemas/gold-evidence.schema.json")
    conditional = schema["allOf"][0]

    assert conditional["if"]["properties"]["pdf_verified"]["const"] is True
    assert set(conditional["then"]["required"]) == {
        "doi", "pdf_sha256", "pdf_page", "locator", "content_sha256"
    }
