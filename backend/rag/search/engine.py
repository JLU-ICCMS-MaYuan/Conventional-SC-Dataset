"""
engine.py — 统一搜索接口。

对外暴露 search() 函数，自动路由到合适的搜索策略。
支持 4 种搜索模式 + 语义搜索：
  1. formula: 精确化学式
  2. elements_exact: 精确元素体系
  3. elements_combination: 元素子集
  4. elements_contained: 包含元素
  5. semantic: 自然语言语义搜索
"""

from __future__ import annotations

import re
from typing import Any

from backend.rag.database import async_session_factory
from backend.rag.search.sql_search import (
    get_paper_detail,
    get_superconductor_records,
    search_by_elements_combination,
    search_by_elements_contained,
    search_by_elements_exact,
    search_by_formula,
    search_papers,
)
from backend.rag.search.fusion import merge_superconductor_and_chunk_results

# ── 搜索模式映射 ──────────────────────────────────────────────────────────
# 对应 example.md 中的 4 种搜索方式

SEARCH_MODES = {
    "formula": "按化学式精确搜索，如 LaH10、H3S",
    "elements_exact": "精确元素体系，如 La-H 只返回 H-La",
    "elements_combination": "元素子集组合，如 La-H-S 返回 H-La、H-S、H-La-S",
    "elements_contained": "包含元素，如 La-H 返回所有含 La 和 H 的体系",
    "semantic": "自然语言语义搜索",
    "paper": "搜索论文",
}


def detect_search_mode(query: str) -> str:
    """自动识别用户输入的搜索模式。

    规则：
    - 包含大写字母 + 数字 → formula（如 LaH10, H3S, CaH6）
    - 包含 - 连接的元素 → elements（如 La-H, Ba-Cu-O）
    - 中文/英文句子 → semantic
    - 不是以上 → paper
    """
    query = query.strip()

    # 化学式：纯字母数字组合，LaH10 / H3S / CaH6 格式
    # 排除包含中文的
    if not re.search(r"[一-鿿]", query) and re.search(
        r"^[A-Z][a-z]?\d*([A-Z][a-z]?\d*)*$", query
    ):
        return "formula"

    # 元素体系：纯元素符号用 - 连接
    if re.search(r"^[A-Z][a-z]?(-[A-Z][a-z]?)+$", query):
        return "elements_exact"

    # 包含中文字符 → 语义搜索
    if re.search(r"[一-鿿]", query):
        return "semantic"

    # 英文句子
    if len(query.split()) > 2:
        return "semantic"

    return "paper"


async def search(
    query: str,
    mode: str | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    """统一搜索入口。

    Args:
        query: 搜索关键词
        mode: 搜索模式（None 时自动检测）
        top_k: 返回结果数量

    Returns:
        {"mode": str, "superconductors": [...], "chunks": [...],
         "papers": [...], "related_paper_ids": [...]}
    """
    if mode is None:
        mode = detect_search_mode(query)

    result: dict[str, Any] = {
        "mode": mode,
        "query": query,
        "superconductors": [],
        "chunks": [],
        "papers": [],
        "related_paper_ids": [],
    }

    async with async_session_factory() as session:
        # ── SQL 搜索 ────────────────────────────────────────────────────
        superconductors = []

        if mode == "formula":
            superconductors = await search_by_formula(session, query)
            result["superconductors"] = superconductors

        elif mode in ("elements_exact", "elements"):
            # 解析 La-H → ["La", "H"]
            elements = [e.strip() for e in query.split("-")]
            superconductors = await search_by_elements_exact(session, elements)
            result["superconductors"] = superconductors

        elif mode == "elements_combination":
            elements = [e.strip() for e in query.split("-")]
            result["superconductors"] = await search_by_elements_combination(session, elements)

        elif mode == "elements_contained":
            elements = [e.strip() for e in query.split("-")]
            result["superconductors"] = await search_by_elements_contained(session, elements)

        elif mode == "paper":
            papers = await search_papers(session, query, limit=top_k)
            result["papers"] = papers

        # ── 语义搜索（对所有模式都执行，作为补充） ─────────────────────
        if mode == "semantic" or not result["superconductors"]:
            try:
                from backend.rag.search.vector_search import search_by_semantics

                chunks = await search_by_semantics(query, top_k=top_k)
                result["chunks"] = chunks
                result["related_paper_ids"] = sorted(
                    set(c["paper_id"] for c in chunks if c.get("paper_id"))
                )
            except Exception as e:
                result["chunks"] = []
                result["search_note"] = f"语义搜索不可用: {e}"

        # ── 如果 SQL 结果为空，回退到语义搜索 ──────────────────────────
        if not result["superconductors"] and not result["papers"] and not result["chunks"]:
            result["search_note"] = "未找到相关结果，请尝试换一种搜索方式"

        # ── 统计 ────────────────────────────────────────────────────────
        result["total"] = (
            len(result["superconductors"])
            + len(result["chunks"])
            + len(result["papers"])
        )

    return result


async def search_semantic_only(query: str, top_k: int = 10) -> dict:
    """仅执行语义搜索（不执行 SQL 搜索）。"""
    result = {"mode": "semantic", "query": query}

    async with async_session_factory() as session:
        try:
            from backend.rag.search.vector_search import search_by_semantics

            chunks = await search_by_semantics(query, top_k=top_k)
            result["chunks"] = chunks
            result["related_paper_ids"] = sorted(
                set(c["paper_id"] for c in chunks if c.get("paper_id"))
            )
        except Exception as e:
            result["chunks"] = []
            result["search_note"] = f"语义搜索不可用: {e}"

    result["total"] = len(result.get("chunks", []))
    return result
