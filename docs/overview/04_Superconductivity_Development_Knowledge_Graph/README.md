# 超导发展知识图谱

## 功能边界

该功能负责以图结构组织论文、材料与物性之间的关系，支持图谱快照展示与 Neo4j 多跳遍历查询。它不负责图谱数据的自动生产——当前 Neo4j 同步（`backend/ingest/sync_neo4j.py`）不在上传链路中自动触发。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [超导知识图谱](superconductivity-knowledge-graph.md) | 展示 `graph.json` 快照和 Neo4j 工具查询 | Go API、Python KG API、Neo4j |
| [知识图谱数据同步](knowledge-graph-data-sync.md) | 审批通过后自动同步到 Neo4j，或全量同步历史数据 | MySQL、Neo4j、审批流程 |
| [知识图谱边关系](knowledge-graph-edges.md) | 定义和生成论文、材料、作者间的关系边 | AI 提取、同步脚本 |
| [知识图谱节点标题](knowledge-graph-node-titles.md) | 为 Paper 节点生成凝练标题，替代冗长原标题 | AI 生成、数据库字段 |

## 功能组成

```text
超导发展知识图谱
├── 超导知识图谱（graph.json 快照 + Neo4j Paper/Material/Property 遍历）
├── 知识图谱数据同步（审批自动同步 + 全量同步脚本）
├── 知识图谱边关系（BUILDS_ON/RELATES_TO/STUDIES/AUTHORED/SHARES_STRUCTURE）
└── 知识图谱节点标题（AI 生成凝练标题 + 优雅降级）
```

## 关联关系

Go 服务启动时加载 `graph.json` 快照提供前端图谱展示；Python `/api/kg` 提供 `traverse`、`path` 等多跳查询，数据来自 Neo4j。图谱内容来源于 01 上传并经 02 审核的论文数据，审批通过后自动同步到 Neo4j（增量），或手动运行 `sync_neo4j.py` 全量同步。节点标题由 AI 在论文提取时自动生成（15-30 字凝练版），边关系包括论文依赖（`BUILDS_ON`，当前目标为占位符）、论文相关性（`RELATES_TO`，未实现）、论文研究材料（`STUDIES`）、作者署名（`AUTHORED`）和材料结构相似性（`SHARES_STRUCTURE`）。
