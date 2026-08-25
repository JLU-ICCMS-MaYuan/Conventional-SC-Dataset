# 超导发展知识图谱

## 功能边界

该功能负责以图结构组织论文、材料与物性之间的关系，支持图谱快照展示与 Neo4j 多跳遍历查询。它不负责图谱数据的自动生产——当前 Neo4j 同步（`backend/ingest/sync_neo4j.py`）不在上传链路中自动触发。

## 小功能目录

| 小功能 | 职责 | 依赖 |
| --- | --- | --- |
| [超导知识图谱](superconductivity-knowledge-graph.md) | 展示 `graph.json` 快照和 Neo4j 工具查询 | Go API、Python KG API、Neo4j |

## 功能组成

```text
超导发展知识图谱
└── 超导知识图谱（graph.json 快照 + Neo4j Paper/Material/Property 遍历）
```

## 关联关系

Go 服务启动时加载 `graph.json` 快照提供前端图谱展示；Python `/api/kg` 提供 `traverse`、`path` 等多跳查询，数据来自 Neo4j。图谱内容来源于 01 上传并经 02 审核的论文数据，但同步动作当前需要独立运行，是否自动触发待核验。
