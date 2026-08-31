"""动态知识图谱 API — 从 Neo4j 实时生成图数据"""

from __future__ import annotations

from fastapi import APIRouter, Query

from backend.rag.tools.neo4j import _driver

router = APIRouter(prefix="/api/knowledge-graph-live", tags=["kg-live"])


@router.get("/overview")
def get_live_overview(limit: int = Query(30, ge=1, le=100)):
    """从 Neo4j 动态生成知识图谱总览"""
    with _driver().session() as s:
        papers = s.run("""
            MATCH (p:Paper)
            RETURN p.paper_id AS paper_id,
                   coalesce(p.title, p.import_label, 'Untitled') AS title,
                   p.year AS year, p.doi AS doi
            ORDER BY p.year DESC
            LIMIT $limit
        """, limit=limit).data()

        edges = s.run("""
            MATCH (p1:Paper)-[r]->(p2:Paper)
            WHERE type(r) IN ['RELATES_TO', 'BUILDS_ON']
            RETURN p1.paper_id AS source, p2.paper_id AS target,
                   type(r) AS type,
                   coalesce(r.importance, 0.5) AS importance,
                   coalesce(r.evidence, '') AS evidence,
                   coalesce(r.label, type(r)) AS label
            LIMIT $limit * 3
        """, limit=limit).data()

        total_edges = s.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]

    nodes = [
        {
            "id": f"paper_{p['paper_id']}",
            "label": p['title'][:100] if p['title'] else f"Paper {p['paper_id']}",
            "year": p.get('year'),
            "doi": p.get('doi'),
        }
        for p in papers
    ]

    formatted_edges = [
        {
            "source": f"paper_{e['source']}",
            "target": f"paper_{e['target']}",
            "type": e['type'],
            "importance": float(e['importance']),
            "evidence": e.get('evidence', ''),
            "from": f"paper_{e['source']}",
            "to": f"paper_{e['target']}",
        }
        for e in edges
    ]

    return {
        "nodes": nodes,
        "edges": formatted_edges,
        "total_edges": total_edges,
        "message": f"从 Neo4j 加载了 {len(nodes)} 个节点和 {len(formatted_edges)} 条边"
    }


@router.get("/papers/{paper_id}/neighbors")
def get_paper_neighbors(paper_id: str, limit: int = Query(10, ge=1, le=50)):
    """获取论文的邻居节点"""
    if paper_id.startswith("paper_"):
        pid = int(paper_id[6:])
    else:
        pid = int(paper_id)

    with _driver().session() as s:
        neighbors = s.run("""
            MATCH (p:Paper {paper_id: $pid})-[r]-(neighbor:Paper)
            RETURN DISTINCT neighbor.paper_id AS paper_id,
                   coalesce(neighbor.title, neighbor.import_label, 'Untitled') AS title,
                   neighbor.year AS year,
                   neighbor.doi AS doi
            LIMIT $limit
        """, pid=pid, limit=limit).data()

        neighbor_ids = [n['paper_id'] for n in neighbors]
        all_ids = [pid] + neighbor_ids

        edges = s.run("""
            MATCH (p1:Paper)-[r]->(p2:Paper)
            WHERE p1.paper_id IN $ids AND p2.paper_id IN $ids
              AND type(r) IN ['RELATES_TO', 'BUILDS_ON']
            RETURN p1.paper_id AS source, p2.paper_id AS target,
                   type(r) AS type,
                   coalesce(r.importance, 0.5) AS importance,
                   coalesce(r.evidence, '') AS evidence,
                   coalesce(r.label, type(r)) AS label
        """, ids=all_ids).data()

    new_nodes = [
        {
            "id": f"paper_{n['paper_id']}",
            "label": n['title'][:100] if n['title'] else f"Paper {n['paper_id']}",
            "year": n.get('year'),
            "doi": n.get('doi'),
        }
        for n in neighbors
    ]

    new_edges = [
        {
            "source": f"paper_{e['source']}",
            "target": f"paper_{e['target']}",
            "type": e['type'],
            "importance": float(e['importance']),
            "evidence": e.get('evidence', ''),
            "from": f"paper_{e['source']}",
            "to": f"paper_{e['target']}",
        }
        for e in edges
    ]

    return {
        "new_nodes": new_nodes,
        "new_edges": new_edges,
    }


@router.get("/stats")
def get_graph_stats():
    """图谱统计信息"""
    with _driver().session() as s:
        paper_count = s.run("MATCH (p:Paper) RETURN count(p) AS count").single()["count"]
        edge_count = s.run("MATCH ()-[r]->() RETURN count(r) AS count").single()["count"]
        
        rel_stats = s.run("""
            MATCH ()-[r]->()
            RETURN type(r) AS type, count(*) AS count
        """).data()

        top_papers = s.run("""
            MATCH (p:Paper)
            OPTIONAL MATCH (p)-[r]-()
            WITH p, count(r) AS degree
            WHERE degree > 0
            RETURN p.paper_id AS paper_id,
                   coalesce(p.title, p.import_label, 'Untitled') AS title,
                   degree
            ORDER BY degree DESC
            LIMIT 10
        """).data()

    relation_types = {r['type']: r['count'] for r in rel_stats}

    return {
        "total_nodes": paper_count,
        "total_edges": edge_count,
        "relation_types": relation_types,
        "top_nodes": [
            {
                "id": f"paper_{p['paper_id']}",
                "label": p['title'][:60],
                "degree": p['degree']
            }
            for p in top_papers
        ]
    }
