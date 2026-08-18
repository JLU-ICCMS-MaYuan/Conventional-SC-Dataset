"""
KG Graph Tools — Neo4j 图查询函数，供 RAG Agent 调用。

每个函数返回 LLM 可直接理解的 dict，不依赖 FastAPI。
"""
from __future__ import annotations

import os
import re
from typing import Any

from neo4j import GraphDatabase

_DRIVER = None


def _driver():
    global _DRIVER
    if _DRIVER is None:
        _DRIVER = GraphDatabase.driver(
            os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
            auth=(
                os.environ.get("NEO4J_USER", "neo4j"),
                os.environ.get("NEO4J_PASSWORD", "scwiki123"),
            ),
        )
    return _DRIVER


def _pick(d: dict, *keys: str) -> dict:
    """从 dict 中挑出指定 key"""
    return {k: d.get(k) for k in keys if d.get(k)}


def _node_ref(node: Any) -> dict[str, Any]:
    """返回不依赖 Neo4j element_id 的业务节点引用。"""
    labels = list(node.labels)
    identifier = (
        node.get("paper_id")
        or node.get("formula")
        or node.get("name")
        or node.get("id")
    )
    return {"labels": labels, "id": identifier}


def _edge_record(relation: Any, traversal_from: Any, traversal_to: Any) -> dict[str, Any]:
    """同时记录图中真实方向与本次路径遍历方向。"""
    relation_type = relation.type
    return {
        "source": _node_ref(relation.start_node),
        "target": _node_ref(relation.end_node),
        "type": relation_type,
        "directed": relation_type != "SHARES_STRUCTURE",
        "traversal_source": _node_ref(traversal_from),
        "traversal_target": _node_ref(traversal_to),
    }


# ═══════════════════════════════════════════════
# Tool 1: 搜索论文
# ═══════════════════════════════════════════════

def search_papers(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """按标题模糊搜索论文"""
    with _driver().session() as s:
        result = s.run(
            "MATCH (p:Paper) WHERE coalesce(p.title, p.import_label, '') CONTAINS $q "
            "RETURN p.paper_id AS id, coalesce(p.title, p.import_label) AS title, p.year AS year "
            "ORDER BY p.year DESC LIMIT $limit",
            q=query, limit=limit,
        )
        return [dict(r) for r in result]


# ═══════════════════════════════════════════════
# Tool 2: 论文上下文
# ═══════════════════════════════════════════════

def get_paper_context(paper_id: int) -> dict[str, Any]:
    """一篇论文的完整上下文：基本信息 + 研究材料 + 关联论文 + 前驱工作 + 作者"""
    with _driver().session() as s:
        # 基本信息
        row = s.run(
            "MATCH (p:Paper {paper_id: $pid}) RETURN p", pid=paper_id
        ).single()
        if not row:
            return {"error": f"paper {paper_id} not found"}

        node = row["p"]
        paper = {
            "paper_id": node.get("paper_id"),
            "title": node.get("title") or node.get("import_label", ""),
            "year": node.get("year", ""),
            "journal": node.get("journal", ""),
            "summary": node.get("summary", "")[:300],
            "paper_type": node.get("paper_type", ""),
            "methodology": node.get("methodology", ""),
            "key_finding": node.get("key_finding", ""),
        }

        # 研究材料
        materials = s.run(
            "MATCH (p:Paper {paper_id: $pid})-[r:STUDIES]->(m:Material) "
            "RETURN m.formula AS formula, r.role AS role, r.evidence AS evidence "
            "LIMIT 10",
            pid=paper_id,
        ).data()

        # 关联论文
        related = s.run(
            "MATCH (p:Paper {paper_id: $pid})-[r:RELATES_TO]-(q:Paper) "
            "RETURN q.paper_id AS id, coalesce(q.title, q.import_label) AS title, type(r) AS relation, "
            "r.label AS label, r.importance AS importance "
            "ORDER BY r.importance DESC LIMIT 10",
            pid=paper_id,
        ).data()

        # 前驱工作
        builds_on = s.run(
            "MATCH (p:Paper {paper_id: $pid})-[r:BUILDS_ON]->(q:Paper) "
            "RETURN q.title AS title, q.paper_id AS id, r.work AS work, "
            "q.work_hint AS hint LIMIT 10",
            pid=paper_id,
        ).data()

        # 作者
        authors = s.run(
            "MATCH (p:Paper {paper_id: $pid})<-[r:AUTHORED]-(res:Researcher) "
            "RETURN res.name AS name LIMIT 20",
            pid=paper_id,
        ).data()

    return {
        "paper": paper,
        "materials": materials,
        "related_papers": related,
        "builds_on": builds_on,
        "authors": [a["name"] for a in authors],
    }


# ═══════════════════════════════════════════════
# Tool 3: 材料上下文
# ═══════════════════════════════════════════════

def get_material_context(formula: str) -> dict[str, Any]:
    """材料完整上下文：研究论文 + 物性参数"""
    with _driver().session() as s:
        papers = s.run(
            "MATCH (p:Paper)-[r:STUDIES]->(m:Material {formula: $f}) "
            "RETURN p.paper_id AS id, p.title AS title, p.year AS year, "
            "r.role AS role ORDER BY p.year DESC LIMIT 20",
            f=formula,
        ).data()

        props = s.run(
            "MATCH (m:Material {formula: $f})-[:HAS_PROPERTY]->(prop:Property) "
            "RETURN prop.name AS name, prop.value AS value, prop.unit AS unit, "
            "prop.pressure_gpa AS pressure "
            "ORDER BY prop.value DESC LIMIT 15",
            f=formula,
        ).data()

    return {"formula": formula, "papers": papers, "properties": props}


# ═══════════════════════════════════════════════
# Tool 4: 图遍历
# ═══════════════════════════════════════════════

def traverse_graph(
    paper_id: int,
    depth: int = 2,
    relations: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """从论文出发多跳遍历关联节点"""
    rel_filter = ""
    if relations:
        types = [t.strip() for t in relations.split(",") if t.strip()]
        if not types or any(not re.fullmatch(r"[A-Z][A-Z0-9_]*", item) for item in types):
            raise ValueError("关系类型只能包含大写字母、数字和下划线")
        rel_filter = ":" + "|".join(types)

    with _driver().session() as s:
        result = s.run(
            f"MATCH path = (p:Paper {{paper_id: $pid}})-[r{rel_filter}*1..{depth}]-(q) "
            "WHERE q:Paper OR q:Material "
            "WITH relationships(path) AS rels, nodes(path) AS ns "
            "UNWIND ns AS n WITH DISTINCT n, rels "
            "RETURN n, size(rels) AS degree "
            "ORDER BY degree DESC LIMIT $limit",
            pid=paper_id, limit=limit,
        )
        nodes = []
        edges = []
        seen = set()
        for r in result:
            n = r["n"]
            eid = n.element_id
            if eid not in seen:
                seen.add(eid)
                d: dict[str, Any] = dict(n.items())
                d.pop("author_list", None)
                d.pop("abstract", None)
                d["_label"] = list(n.labels)
                nodes.append(d)

        # 节点间的关系
        paper_ids = [n.get("paper_id") for n in nodes if n.get("paper_id")]
        if len(paper_ids) >= 2:
            edge_rows = s.run(
                "MATCH (a:Paper)-[r:RELATES_TO|DEVELOPS_TO|STUDIES|BUILDS_ON]->(b) "
                "WHERE a.paper_id IN $ids AND b.paper_id IN $ids "
                "RETURN a.paper_id AS source, b.paper_id AS target, type(r) AS type "
                "LIMIT 50",
                ids=paper_ids,
            ).data()
            edges = [dict(e) for e in edge_rows]

    return {"center": paper_id, "depth": depth, "node_count": len(nodes), "nodes": nodes, "edges": edges}


# ═══════════════════════════════════════════════
# Tool 5: 最短路径
# ═══════════════════════════════════════════════

def find_path(from_id: int, to_id: int, max_depth: int = 4) -> dict[str, Any]:
    """两篇论文之间的最短发展路径"""
    with _driver().session() as s:
        row = s.run(
            f"MATCH (a:Paper {{paper_id: $from}}), (b:Paper {{paper_id: $to}}) "
            f"MATCH path = shortestPath((a)-[*..{max_depth}]-(b)) "
            "RETURN nodes(path) AS ns, relationships(path) AS rs",
            **{"from": from_id, "to": to_id},
        ).single()

        if not row:
            return {"path": [], "length": 0, "message": f"{max_depth}步内无路径"}

        nodes = []
        for n in row["ns"]:
            d: dict[str, Any] = dict(n.items())
            d.pop("author_list", None)
            d.pop("abstract", None)
            d["_label"] = list(n.labels)
            nodes.append(d)

        edges = []
        for index, relation in enumerate(row["rs"]):
            edges.append(_edge_record(relation, row["ns"][index], row["ns"][index + 1]))

    return {"path": nodes, "edges": edges, "length": len(edges)}


# ═══════════════════════════════════════════════
# Tool 定义列表（供 LLM function calling 使用）
# ═══════════════════════════════════════════════

TOOL_DEFINITIONS = [
    {
        "name": "search_papers",
        "description": "按标题模糊搜索论文。当用户提到某个研究方向、材料名或关键词时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索词，如材料化学式、方法名、作者名"},
                "limit": {"type": "integer", "description": "返回数量上限，默认10"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_paper_context",
        "description": "获取一篇论文的完整上下文：基本信息、研究的材料、关联论文、前驱工作、作者列表。"
                       "当用户询问某篇具体论文的细节时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "integer", "description": "论文 paper_id"},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "get_material_context",
        "description": "获取一种超导材料的完整上下文：哪些论文研究过它、关键物性参数（Tc、压力等）。"
                       "当用户询问某种具体材料的超导性质时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "formula": {"type": "string", "description": "材料化学式，如 LaH10、H3S"},
            },
            "required": ["formula"],
        },
    },
    {
        "name": "traverse_graph",
        "description": "从一篇论文出发，在知识图谱中多跳遍历，发现关联论文和材料。"
                       "当用户询问研究脉络、发展方向、相关工作时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "paper_id": {"type": "integer", "description": "起点论文 paper_id"},
                "depth": {"type": "integer", "description": "遍历深度 1-4，默认2"},
                "relations": {"type": "string", "description": "限定关系类型，逗号分隔，如 STUDIES,RELATES_TO"},
                "limit": {"type": "integer", "description": "返回节点上限，默认20"},
            },
            "required": ["paper_id"],
        },
    },
    {
        "name": "find_path",
        "description": "查找两篇论文之间在知识图谱中的最短发展路径。"
                       "当用户询问两篇论文或两个发现之间的关系/脉络时使用。",
        "parameters": {
            "type": "object",
            "properties": {
                "from_id": {"type": "integer", "description": "起点论文 paper_id"},
                "to_id": {"type": "integer", "description": "终点论文 paper_id"},
                "max_depth": {"type": "integer", "description": "最大搜索深度 1-6，默认4"},
            },
            "required": ["from_id", "to_id"],
        },
    },
]

# Tool 执行路由
TOOL_EXECUTORS = {
    "search_papers": search_papers,
    "get_paper_context": get_paper_context,
    "get_material_context": get_material_context,
    "traverse_graph": traverse_graph,
    "find_path": find_path,
}
