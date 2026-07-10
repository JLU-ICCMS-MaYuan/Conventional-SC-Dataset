"""
导入 paper-paper 关系到 Neo4j
用法: python backend/kg_import_relations.py [--clear]
"""
import json
import os
import sys
from pathlib import Path

from neo4j import GraphDatabase

NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "scwiki123")

GRAPH_FILE = Path("/home/work/workshop/bak/graph.json")

MERGE_NODE = """
MERGE (p:Paper {id: $id})
SET p.label = $label, p.paper_id = $paper_id
"""

MERGE_EDGE = """
MATCH (a:Paper {id: $source})
MATCH (b:Paper {id: $target})
MERGE (a)-[r:RELATES_TO {type: $rel_type}]->(b)
SET r.label = $rel_label, r.importance = $importance, r.evidence = $evidence
"""

CLEAR = "MATCH (n:Paper) DETACH DELETE n"


def main():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    if "--clear" in sys.argv:
        print("清空 Paper 节点...")
        with driver.session() as s:
            s.run(CLEAR)
        print("完成")

    if not GRAPH_FILE.exists():
        print(f"{GRAPH_FILE} 不存在，请先运行 merge_relations.py")
        return

    with open(GRAPH_FILE) as f:
        graph = json.load(f)

    nodes = graph["nodes"]
    edges = graph["edges"]
    print(f"导入 {len(nodes)} 节点, {len(edges)} 边...")

    # 导入节点
    with driver.session() as s:
        for i, n in enumerate(nodes):
            s.run(MERGE_NODE, {
                "id": n["id"],
                "label": n.get("label", "")[:200],
                "paper_id": n.get("paper_id"),
            })
            if (i + 1) % 200 == 0:
                print(f"  节点: {i+1}/{len(nodes)}")

    print(f"  节点完成: {len(nodes)}")

    # 导入边
    with driver.session() as s:
        for i, e in enumerate(edges):
            s.run(MERGE_EDGE, {
                "source": e["source"],
                "target": e["target"],
                "rel_type": e.get("type", "unknown"),
                "rel_label": e.get("label", ""),
                "importance": e.get("importance", 0),
                "evidence": e.get("evidence", "")[:500],
            })
            if (i + 1) % 200 == 0:
                print(f"  边: {i+1}/{len(edges)}")

    print(f"  边完成: {len(edges)}")

    # 统计
    with driver.session() as s:
        r = s.run("MATCH (p:Paper) RETURN count(p) AS cnt").single()
        print(f"Neo4j Paper节点: {r['cnt']}")
        r2 = s.run("MATCH ()-[r:RELATES_TO]->() RETURN count(r) AS cnt").single()
        print(f"Neo4j RELATES_TO边: {r2['cnt']}")

    driver.close()
    print("导入完成")


if __name__ == "__main__":
    main()
