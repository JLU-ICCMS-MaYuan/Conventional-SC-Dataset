"""S1 使用的确定性二元相关性排名指标。"""

from __future__ import annotations

import math
from collections.abc import Collection, Sequence


def recall_at_k(ranked_ids: Sequence[str], gold_ids: Collection[str], k: int) -> float:
    """返回前 k 项召回的 gold evidence 比例。"""

    if not gold_ids or k <= 0:
        return 0.0
    return len(set(ranked_ids[:k]) & set(gold_ids)) / len(set(gold_ids))


def all_evidence_success_at_k(
    ranked_ids: Sequence[str], gold_ids: Collection[str], k: int
) -> float:
    """前 k 项覆盖全部 gold evidence 时返回 1，否则返回 0。"""

    if not gold_ids or k <= 0:
        return 0.0
    return float(set(gold_ids).issubset(set(ranked_ids[:k])))


def mean_reciprocal_rank(
    ranked_ids: Sequence[str], gold_ids: Collection[str], max_k: int | None = None
) -> float:
    """返回首个相关结果的倒数排名；单题值可跨题取均值。"""

    if not gold_ids:
        return 0.0
    candidates = ranked_ids if max_k is None else ranked_ids[:max_k]
    for rank, item_id in enumerate(candidates, start=1):
        if item_id in gold_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(ranked_ids: Sequence[str], gold_ids: Collection[str], k: int) -> float:
    """计算前 k 项的二元相关性 nDCG。"""

    unique_gold = set(gold_ids)
    if not unique_gold or k <= 0:
        return 0.0
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, item_id in enumerate(ranked_ids[:k], start=1)
        if item_id in unique_gold
    )
    ideal_hits = min(len(unique_gold), k)
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))
    return dcg / idcg
