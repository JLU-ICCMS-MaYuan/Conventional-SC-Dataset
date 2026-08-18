"""S1 排名指标的独立手算验收样例。"""

from __future__ import annotations

import math
import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TEST_ROOT))

from benchmark.metrics.ranking import (  # noqa: E402
    all_evidence_success_at_k,
    mean_reciprocal_rank,
    ndcg_at_k,
    recall_at_k,
)


def test_recall_and_all_evidence_coverage_use_gold_ids() -> None:
    ranked = ["noise", "e1", "e2", "late"]
    gold = {"e1", "e2"}

    assert recall_at_k(ranked, gold, 1) == 0.0
    assert recall_at_k(ranked, gold, 2) == 0.5
    assert recall_at_k(ranked, gold, 3) == 1.0
    assert all_evidence_success_at_k(ranked, gold, 2) == 0.0
    assert all_evidence_success_at_k(ranked, gold, 3) == 1.0


def test_mrr_uses_first_relevant_rank() -> None:
    assert mean_reciprocal_rank(["noise", "e1", "e2"], {"e1", "e2"}) == 0.5
    assert mean_reciprocal_rank(["noise"], {"e1"}) == 0.0


def test_ndcg_matches_independent_binary_relevance_example() -> None:
    ranked = ["noise", "e1", "e2"]
    expected = (1 / math.log2(3) + 1 / math.log2(4)) / (
        1 / math.log2(2) + 1 / math.log2(3)
    )

    assert ndcg_at_k(ranked, {"e1", "e2"}, 3) == expected


def test_empty_gold_is_defined_as_zero() -> None:
    assert recall_at_k(["e1"], set(), 1) == 0.0
    assert mean_reciprocal_rank(["e1"], set()) == 0.0
    assert ndcg_at_k(["e1"], set(), 1) == 0.0
    assert all_evidence_success_at_k(["e1"], set(), 1) == 0.0
