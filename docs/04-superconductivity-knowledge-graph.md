# IV. 超导发展知识图谱

## 功能定义

Superconductivity Development Knowledge Graph 是 SC-Wiki 围绕论文、材料、物性、研究者和论文间学术关系构建的图数据库系统。它包含 Neo4j 图数据库（639 篇论文、1459 种材料、1481 位研究者、6753 条关系）、前端可视化页面（`/knowledge`）和两套 API（用户可视化 API + RAG Agent API）。

## 当前状态

当前状态已落地。Neo4j 图数据库包含 Paper、Material、Property、Researcher 四种节点和 STUDIES、RELATES_TO、BUILDS_ON、AUTHORED、HAS_PROPERTY 五种关系。前端 `/knowledge` 页面提供 vis-network 力导向图可视化。API 层分为用户面向的 `/api/knowledge-graph/*`（读 graph.json）和 RAG Agent 面向的 `/api/kg/*`（读 Neo4j）。

## What Exists Today

### Neo4j 图数据库

| 节点类型 | 数量 | 说明 |
|---------|------|------|
| Paper | 639 | 论文节点，含 title/year/journal/summary/methodology/key_finding 等 |
| Material | 1459 | 材料节点，以 chemical_formula 为唯一标识 |
| Property | 316 | 物性节点（Tc/λ/ω_log），含 pressure 条件 |
| Researcher | 1481 | 研究者节点，从 author_list JSON 解析 |

| 关系类型 | 数量 | 说明 |
|---------|------|------|
| STUDIES | 1416 | Paper → Material（discovers/investigates/predicts） |
| RELATES_TO | 771 | Paper → Paper（8 种子类型：首次发现/实验验证/理论基础等） |
| BUILDS_ON | 541 | Paper → Paper，前驱工作依赖 |
| AUTHORED | 3709 | Researcher → Paper |
| HAS_PROPERTY | 316 | Material → Property |

### 前端可视化

`/knowledge` 页面：vis-network 力导向图。支持节点选中高亮（1-hop 邻居清晰，其余透明）、展开节点（BFS 遍历锁定子图）、关系类型筛选、边证据原文展示、论文详情侧边栏。

### API

用户可视化 API（`/api/knowledge-graph/*`，读 graph.json）：
- `GET /overview` — 首页图谱 top-K 边
- `GET /papers/{id}/neighbors` — 展开一层关联
- `GET /papers/{id}` — 论文详情
- `GET /stats` — 图谱统计

RAG Agent API（`/api/kg/*`，读 Neo4j）：
- `GET /traverse?paper_id=&depth=` — 多跳图遍历
- `GET /path?from_paper=&to_paper=` — 最短路径
- `GET /around?paper_id=` — 论文上下文（材料+关联+前驱+作者）
- `GET /material/{formula}` — 材料全貌（研究论文+物性）
- `GET /search?q=` — 模糊搜索

### 构建流水线

位于 `backend/ingest/kg/`，7 步流水线：
1. `extract_relations.py` — LLM 从 34 篇综述提取论文间关系
2. `fix_resolve.py` — V2+V1 双通道解析 paper_id
3. `merge_relations.py` — 合并去重 → graph.json (771 边/335 节点)
4. `kg_enrich.py` — LLM 富化 638 篇论文（7 项结构化数据）
5. `kg_sync.py` — MySQL + clean_results → Neo4j 全量同步
6. `kg_import_relations.py` — graph.json → Neo4j RELATES_TO 边
7. API 暴露 → `/api/knowledge-graph/*` + `/api/kg/*`

## Code and API Evidence

核心代码：
- `backend/ingest/kg/` — KG 构建流水线
- `backend/rag/tools/neo4j.py` — Neo4j 图查询工具
- `backend/rag/tools/mysql.py` — MySQL 物性查询
- `backend/api/knowledge_graph.py` — 用户可视化 API
- `backend/api/kg.py` — RAG Agent API
- `frontend/src/pages/KnowledgeGraphPage.tsx` — 可视化页面

页面入口：
- `/knowledge` — 知识图谱可视化

## Data Sources

Neo4j 数据来源：
- MySQL `papers` 表 → Paper 节点基础字段
- MySQL `superconductors` 表 → Material 节点
- MySQL `superconductor_records` 表 → Property 节点 + HAS_PROPERTY
- `data/clean_results/*.json` → Paper 节点的 LLM 富化字段（methodology/builds_on/key_finding 等）
- `graph.json` → Paper-Paper RELATES_TO 关系

## Limitations

- SHARES_STRUCTURE 关系返回 0（Material.space_group 字段未填充）
- BUILDS_ON 的 target 使用 paper_id:-1 占位符（未做模糊匹配）

## Future Direction

- BUILDS_ON 占位符匹配到真实 paper_id
- 挂载 Inspiration Agent 的图遍历推理
- 按年份切片的时序演化分析
- Node2Vec / GraphSAGE 材料相似度 embedding
