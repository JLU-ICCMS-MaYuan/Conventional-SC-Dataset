"""Agent Tools — 把 neo4j/chroma/mysql 函数包装为 LangChain Tool"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.tools import tool

from backend.rag.tools.neo4j import (
    search_papers as neo4j_search_papers,
    get_paper_context,
    get_material_context,
    traverse_graph,
    find_path,
)


@tool
def search_papers(query: str, limit: int = 10) -> str:
    """按标题模糊搜索论文。输入可以是材料化学式、方法名、作者名、或研究方向关键词。
    返回匹配的论文ID和标题列表。"""
    results = neo4j_search_papers(query, limit=limit)
    if not results:
        return "未找到匹配论文。"
    return json.dumps(results, ensure_ascii=False, indent=2)


@tool
def paper_context(paper_id: int) -> str:
    """获取一篇论文的完整上下文：基本信息、研究材料、关联论文、前驱工作、作者。
    当你已获得 paper_id 并想了解该论文的详细内容时使用。"""
    ctx = get_paper_context(paper_id)
    if "error" in ctx:
        return ctx["error"]
    # 截断长文本
    ctx["paper"].pop("summary", None)
    return json.dumps(ctx, ensure_ascii=False, indent=2, default=str)


@tool
def material_info(formula: str) -> str:
    """获取一种超导材料的研究全貌：哪些论文研究过它、关键物性参数（Tc、压力等）。
    当用户询问某种具体材料时使用，如 LaH10、H3S。"""
    ctx = get_material_context(formula)
    return json.dumps(ctx, ensure_ascii=False, indent=2, default=str)


@tool
def explore_graph(paper_id: int, depth: int = 2) -> str:
    """从一篇论文出发，在知识图谱中多跳遍历，发现关联论文和材料。
    用于探索研究脉络、发现相关工作时使用。"""
    result = traverse_graph(paper_id, depth=depth, limit=20)
    # 只返回摘要信息，不返回完整节点
    summary = {
        "center_paper_id": result["center"],
        "depth": result["depth"],
        "node_count": result["node_count"],
        "edge_count": len(result["edges"]),
        "nodes": [
            {"paper_id": n.get("paper_id"), "title": n.get("title", "")[:80]}
            for n in result["nodes"]
            if n.get("paper_id")
        ],
        "edges": result["edges"],
    }
    return json.dumps(summary, ensure_ascii=False, indent=2, default=str)


@tool
def paper_path(from_id: int, to_id: int) -> str:
    """查找两篇论文之间的最短发展路径。展示 A 到 B 的学术脉络。
    当用户询问两篇论文之间的关系或发展历史时使用。"""
    result = find_path(from_id, to_id)
    if "message" in result:
        return result["message"]
    # 简化路径，只保留关键信息
    path_summary = {
        "length": result["length"],
        "path": [
            {"label": n.get("_label", []), "paper_id": n.get("paper_id"),
             "title": n.get("title", "")[:80] if n.get("title") else str(n.get("_label"))}
            for n in result["path"]
        ],
    }
    return json.dumps(path_summary, ensure_ascii=False, indent=2, default=str)


@tool
def search_literature(question: str, top_k: int = 10) -> str:
    """语义搜索相关文献片段。输入完整的自然语言问题，返回相关论文的文本内容。
    当需要获取论文原文中的具体信息时使用。这是唯一能搜索论文正文内容的工具。"""
    from backend.rag.tools.chroma import search_chunks

    try:
        items = search_chunks(question, top_k=top_k)
        if not items:
            return "未找到相关文献片段。"
        return json.dumps(items, ensure_ascii=False, indent=2)
    except Exception as e:
        return f"搜索失败: {e}"


@tool
def query_properties(predicate: str, condition: str = ">0") -> str:
    """查询超导材料的物性数据表。支持的属性：
    - 'Tc' 或 '超导温度' (单位 K)
    - 'pressure' 或 '压力' (单位 GPa)
    - 'lambda' 或 '电声耦合' (无量纲)
    condition 格式如 '>200' 或 '<100'。"""
    import re

    FIELD_MAP = {
        "Tc": "超导温度(AD)", "超导温度": "超导温度(AD)",
        "pressure": "压力", "压力": "压力",
        "lambda": "电声耦合lambda", "电声耦合": "电声耦合lambda",
    }
    predicate = FIELD_MAP.get(predicate, predicate)

    m = re.match(r"([><]=?)\s*([\d.]+)", condition)
    op = m.group(1) if m else ">"
    val = m.group(2) if m else "0"

    # 同步调用异步函数
    import asyncio
    async def _run():
        from backend.rag.tools.mysql import query as kg_query
        return await kg_query(predicate, operator=op, value=val)

    try:
        results = asyncio.run(_run())
    except Exception as e:
        return f"查询失败: {e}"

    if not results:
        return "未找到匹配的数据。"
    top = results[:20]
    items = [{"subject": r["subject"], "predicate": r["predicate"],
              "value": r["object"], "paper_id": r.get("paper_id")}
             for r in top]
    return json.dumps(items, ensure_ascii=False, indent=2)


# 所有可用 tool 列表
ALL_TOOLS = [
    search_papers,
    paper_context,
    material_info,
    explore_graph,
    paper_path,
    search_literature,
    query_properties,
]
