"""Inspiration Agent 检索策略层。

5 种思考模式各有不同的检索策略（语义查询关键词 + 元数据过滤 + KG 开关），
但共享同一 RAG + KG 底层调用。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalStrategy:
    """一种思考模式的检索策略配置。"""
    name: str
    section_filter: list[str] = field(default_factory=list)
    semantic_boost: list[str] = field(default_factory=list)
    kg_enabled: bool = False
    kg_filter: dict | None = None
    collection: str | None = None  # Chroma 集合，None 用默认 paper_chunks


# 文件夹 → ChromaDB 集合名映射（与 ingest_split_collections.py 保持一致）
FOLDER_COLLECTION_MAP: dict[str, str] = {
    "理论-三元": "theoretical_ternary_chunks",
    "理论-二元": "theoretical_binary_chunks",
    "理论-四元": "theoretical_quaternary_chunks",
    "理论-五元": "theoretical_quinary_chunks",
    "理论-六元": "theoretical_senary_chunks",
    "固体氢": "solid_hydrogen_chunks",
    "氢化物超导机理研究": "mechanism_chunks",
    "氢化物非谐研究": "anharmonic_chunks",
    "分子动力学研究": "molecular_dynamics_chunks",
    "机器学习领域应用": "machine_learning_chunks",
    "实验-二元": "experimental_binary_chunks",
    "实验-三元": "experimental_ternary_chunks",
    "实验-四元": "experimental_quaternary_chunks",
    "综述": "review_chunks",
    "upload": "upload_chunks",
}

RETRIEVAL_STRATEGIES: dict[str, RetrievalStrategy] = {
    "gap_detector": RetrievalStrategy(
        name="文献缺口探测",
        section_filter=["conclusion", "future_work", "outlook"],
        semantic_boost=[
            "research gap", "remains unclear", "future work",
            "beyond the scope", "requires further", "open question",
            "尚未解决", "有待研究", "需要进一步",
        ],
        kg_enabled=False,
        collection="review_chunks",  # 优先搜索综述文献
    ),
    "analogy_engine": RetrievalStrategy(
        name="类比推荐引擎",
        section_filter=["discussion", "results"],
        semantic_boost=[
            "chemical precompression", "charge transfer",
            "electron-phonon coupling", "hydrogen cage",
            "mechanism", "chemical pressure",
        ],
        kg_enabled=True,
        kg_filter={"by_elements": True},
        collection="theoretical_ternary_chunks",  # 理论预测+机制类比
    ),
    "contradiction_catalyst": RetrievalStrategy(
        name="矛盾证据催化",
        section_filter=["results", "discussion"],
        semantic_boost=[
            "discrepancy", "different", "however",
            "unexpected", "anomalous", "contradiction",
            "不一致", "差异", "矛盾",
        ],
        kg_enabled=True,
        kg_filter={"by_formula": True, "cross_paper": True},
        collection="experimental_binary_chunks",  # 实验数据对比矛盾
    ),
    "composition_walker": RetrievalStrategy(
        name="成分空间漫步",
        section_filter=[],
        semantic_boost=[
            "doping", "substitution", "ternary", "alloying",
            "掺杂", "替换", "三元", "四元",
        ],
        kg_enabled=True,
        kg_filter={"by_elements": True, "include_candidates": True},
        collection="theoretical_binary_chunks",  # 二元是最佳替换起点
    ),
    "counterfactual_reasoner": RetrievalStrategy(
        name="反事实推理",
        section_filter=[],
        semantic_boost=[
            "metastable", "pressure quenching", "template",
            "molecular cation", "quasi-hydrogen cage",
            "ambient pressure", "亚稳", "淬火", "常压",
        ],
        kg_enabled=True,
        kg_filter={"max_pressure": 10},
        collection="solid_hydrogen_chunks",  # 固体氢→常压超导的终极目标
    ),
}


def get_strategy(mode: str) -> RetrievalStrategy:
    """获取指定模式的检索策略。

    Args:
        mode: 模式名（gap_detector 等）

    Returns:
        对应的 RetrievalStrategy，未知模式返回 gap_detector 策略

    Raises:
        ValueError: mode 为空字符串
    """
    if not mode:
        raise ValueError("mode must not be empty")
    return RETRIEVAL_STRATEGIES.get(mode, RETRIEVAL_STRATEGIES["gap_detector"])


async def execute_retrieval(
    mode: str,
    search_queries: list[str],
    top_k: int = 10,
    collections: list[str] | None = None,
) -> dict[str, Any]:
    """执行检索：RAG 语义搜索 + 可选 KG 查询。"""
    import sys as _sys
    import time as _time
    _t0 = _time.time()

    strategy = get_strategy(mode)
    search_collections = collections if collections else (
        [strategy.collection] if strategy.collection else ["paper_chunks"]
    )
    boosted_query = " ".join(search_queries + strategy.semantic_boost)

    _sys.stderr.write(f"[Retrieval] 搜索集合: {search_collections} | boosted_query={boosted_query[:150]}\n")
    _sys.stderr.flush()

    # ── RAG 检索（多集合） ──
    chunks: list[dict] = []
    try:
        from backend.rag.search.vector_search import search_by_semantics

        seen_ids: set[str] = set()
        all_results: list[dict] = []

        for coll in search_collections:
            try:
                sr = await search_by_semantics(boosted_query, top_k=top_k, collection=coll)
                new = 0
                for r in sr:
                    if r["id"] not in seen_ids:
                        seen_ids.add(r["id"])
                        all_results.append(r)
                        new += 1
                _sys.stderr.write(f"[Retrieval]   {coll}: {len(sr)} hits, {new} new (scores: "
                                 f"{[f'{r.get(\"score\",0):.3f}' for r in sr[:3]]})\n")
                _sys.stderr.flush()
            except Exception as e:
                _sys.stderr.write(f"[Retrieval]   {coll}: 失败 ({e})\n")
                _sys.stderr.flush()

        all_results.sort(key=lambda r: r.get("score", 0), reverse=True)
        chunks = all_results[:min(8, len(all_results))]
        _sys.stderr.write(f"[Retrieval] 合并: {len(all_results)} total → top-{len(chunks)} "
                         f"(scores: {[f'{r.get(\"score\",0):.3f}' for r in chunks[:5]]})\n")
        _sys.stderr.flush()
    except Exception as e:
        _sys.stderr.write(f"[Retrieval] 检索异常: {e}\n")
        _sys.stderr.flush()

    # ── KG 查询 ──
    kg_results: list[dict] = []
    if strategy.kg_enabled:
        try:
            from backend.rag.knowledge_graph import query as kg_query

            if strategy.kg_filter:
                if "max_pressure" in strategy.kg_filter:
                    kg_results = await kg_query("压力", operator="<",
                                                value=str(strategy.kg_filter["max_pressure"]))
                else:
                    kg_results = await kg_query("超导温度(AD)", operator=">", value="0")
                    kg_results.sort(
                        key=lambda r: float(r["object"]) if r["object"].replace(".", "", 1).isdigit() else 0,
                        reverse=True,
                    )
                    kg_results = kg_results[:20]
        except Exception:
            pass

    return {
        "chunks": chunks or [],
        "kg_results": kg_results,
        "mode": mode,
    }


def format_rag_context(retrieval_result: dict[str, Any]) -> str:
    """将检索结果格式化为 LLM 可读的文本。

    Args:
        retrieval_result: execute_retrieval 的返回值

    Returns:
        格式化的文本，包含 KG 数据和文献片段
    """
    parts = []

    kg_results = retrieval_result.get("kg_results", [])
    if kg_results:
        parts.append("【相关超导材料数据】")
        for r in kg_results[:15]:
            pid = f" [PID_{r['paper_id']}]" if r.get("paper_id") else ""
            parts.append(f"  {r['subject']}: {r['object']}K{pid}")

    chunks = retrieval_result.get("chunks", [])
    if chunks:
        parts.append("\n【相关文献片段】")
        for c in chunks[:5]:
            pid = f" [PID_{c['paper_id']}]" if c.get("paper_id") else ""
            parts.append(f"  {c['content'][:300]}{pid}")

    return "\n".join(parts) if parts else ""
