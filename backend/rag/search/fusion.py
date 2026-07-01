"""
fusion.py — 多路召回融合模块。

使用 RRF（Reciprocal Rank Fusion）算法合并多条搜索路径的结果。
RRF 公式：score = Σ 1/(k + rank_i)，其中 k 是常数（通常 60）。
"""

from __future__ import annotations

from typing import Any


RRF_K = 60.0  # RRF 常数


def rrf_fuse(
    *result_lists: list[dict],
) -> list[dict]:
    """RRF 融合多条搜索结果。

    Args:
        *result_lists: 每条搜索路径返回的结果列表

    Returns:
        融合排序后的结果列表（含 score）
    """
    scores: dict[str, dict] = {}
    sources: dict[str, list[str]] = {}

    for path_idx, results in enumerate(result_lists):
        for rank, item in enumerate(results):
            item_id = _item_key(item)

            if item_id not in scores:
                scores[item_id] = dict(item)
                scores[item_id]["rrf_score"] = 0.0
                scores[item_id]["fusion_from"] = []
                sources[item_id] = []

            # RRF 累加
            scores[item_id]["rrf_score"] += 1.0 / (RRF_K + rank)
            sources[item_id].append(str(path_idx))

    # 按 RRF 分数降序排列
    fused = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return fused


def _item_key(item: dict) -> str:
    """生成结果项的唯一键，用于去重。"""
    type_ = item.get("type", "unknown")
    id_ = item.get("id")
    if id_ is not None:
        return f"{type_}_{id_}"
    # fallback: 对于 chunks 用 content 前 50 字符
    content = item.get("content", "")
    return f"chunk_{hash(content[:50])}"


def merge_superconductor_and_chunk_results(
    superconductor_results: list[dict],
    chunk_results: list[dict],
) -> dict:
    """将超导体搜索结果和文本 chunks 搜索结果合并为统一的响应。

    Args:
        superconductor_results: sql_search 返回的超导体列表
        chunk_results: vector_search 返回的 chunks 列表

    Returns:
        {"superconductors": [...], "chunks": [...], "papers": [...]}
    """
    # 从 chunks 中提取涉及的 paper_id
    paper_ids = set()
    for chunk in chunk_results:
        pid = chunk.get("paper_id")
        if pid:
            paper_ids.add(pid)

    return {
        "superconductors": superconductor_results,
        "chunks": chunk_results[:5],  # 只保留最相关的 5 个
        "related_paper_ids": sorted(paper_ids),
    }
