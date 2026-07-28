"""知识图谱 API — 论文关系图查询"""

from __future__ import annotations

import json as _json
from pathlib import Path

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/knowledge-graph", tags=["knowledge-graph"])

GRAPH_FILE = Path(__file__).resolve().parents[2] / "data" / "graph.json"

RELATION_LABELS = {
    "first_discovery": "首次发现",
    "experimental_validation": "实验验证",
    "theoretical_basis": "理论基础",
    "correction_or_dispute": "修正或争议",
    "development_extension": "发展延续",
    "material_system_extension": "材料体系扩展",
    "same_research_direction": "同方向里程碑",
    "supporting_evidence": "支撑证据",
}

RELATION_COLORS = {
    "first_discovery": "#e53935",
    "experimental_validation": "#43a047",
    "theoretical_basis": "#1e88e5",
    "correction_or_dispute": "#fb8c00",
    "development_extension": "#8e24aa",
    "material_system_extension": "#00acc1",
    "same_research_direction": "#546e7a",
    "supporting_evidence": "#78909c",
}


def _load_graph():
    if not GRAPH_FILE.exists():
        return {"nodes": [], "edges": []}
    with open(GRAPH_FILE) as f:
        return _json.load(f)


def _build_index(graph: dict) -> dict:
    """构建 node_id → node 和 node_id → neighbors 索引"""
    node_map = {n["id"]: n for n in graph.get("nodes", [])}
    adj = {}
    for e in graph.get("edges", []):
        adj.setdefault(e["source"], []).append(e)
        adj.setdefault(e["target"], []).append(e)
    return node_map, adj


@router.get("/overview")
def overview(limit: int = Query(10, ge=1, le=100)):
    """首页图谱：按 importance 降序取 top-K 边"""
    graph = _load_graph()
    if not graph["edges"]:
        return {"nodes": [], "edges": [], "message": "请先运行 backend/merge_relations.py"}

    edges = sorted(graph["edges"], key=lambda e: e.get("importance", 0), reverse=True)[:limit]
    used = set()
    for e in edges:
        used.add(e["source"])
        used.add(e["target"])
    nodes = [n for n in graph["nodes"] if n["id"] in used]

    # 附加关系颜色
    for e in edges:
        e["color"] = RELATION_COLORS.get(e.get("type", ""), "#999")

    return {
        "nodes": nodes,
        "edges": edges,
        "data_scope": "综述论文关系 (importance排序)",
        "total_edges": len(graph["edges"]),
        "relation_types": list(RELATION_LABELS.keys()),
    }


@router.get("/papers/{paper_id}/neighbors")
def paper_neighbors(
    paper_id: str,
    limit: int = Query(10, ge=1, le=50),
    relation_types: str | None = Query(None, description="逗号分隔的关系类型"),
):
    """展开论文节点的一层关联"""
    graph = _load_graph()
    node_map, adj = _build_index(graph)

    node = node_map.get(paper_id)
    if not node:
        return {"error": "node not found", "center": paper_id}

    # 收集关联边
    related_edges = adj.get(paper_id, [])
    allowed = set(relation_types.split(",")) if relation_types else None

    # 按 importance 排序取 top
    filtered = [e for e in related_edges if not allowed or e.get("type") in allowed]
    filtered.sort(key=lambda e: e.get("importance", 0), reverse=True)
    selected = filtered[:limit]

    # 收集新节点
    neighbor_ids = set()
    for e in selected:
        if e["source"] != paper_id:
            neighbor_ids.add(e["source"])
        if e["target"] != paper_id:
            neighbor_ids.add(e["target"])

    new_nodes = [node_map[nid] for nid in neighbor_ids if nid in node_map]

    for e in selected:
        e["color"] = RELATION_COLORS.get(e.get("type", ""), "#999")

    return {
        "center": node,
        "new_nodes": new_nodes,
        "new_edges": selected,
        "has_more": len(filtered) > limit,
    }


@router.get("/papers/{paper_id}")
def paper_detail(paper_id: str):
    """论文节点详情"""
    graph = _load_graph()
    node_map, adj = _build_index(graph)

    node = node_map.get(paper_id)
    if not node:
        return {"error": "node not found"}

    related = adj.get(paper_id, [])
    rel_summary = {}
    for e in related:
        t = e.get("type", "")
        if t not in rel_summary:
            rel_summary[t] = []
        neighbor = e["target"] if e["source"] == paper_id else e["source"]
        rel_summary[t].append({
            "neighbor": neighbor,
            "label": node_map.get(neighbor, {}).get("label", "")[:60] if neighbor in node_map else "",
            "evidence": e.get("evidence", "")[:200],
        })

    return {
        "node": node,
        "relation_count": len(related),
        "relations": rel_summary,
    }


@router.get("/stats")
def graph_stats():
    """图谱统计"""
    graph = _load_graph()
    node_map, adj = _build_index(graph)

    type_counts = {}
    for e in graph["edges"]:
        t = e.get("type", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    # 按 degree 排 top 节点
    degrees = {nid: len(adj.get(nid, [])) for nid in node_map}
    top_nodes = sorted(degrees.items(), key=lambda x: x[1], reverse=True)[:10]

    return {
        "total_nodes": len(graph["nodes"]),
        "total_edges": len(graph["edges"]),
        "relation_types": type_counts,
        "top_nodes": [
            {"id": nid, "degree": deg, "label": node_map.get(nid, {}).get("label", "")[:60]}
            for nid, deg in top_nodes
        ],
    }
