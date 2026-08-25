# 超导知识图谱

## 功能说明

展示超导文献知识图谱快照，并提供论文节点展开、关系筛选、上下文详情和 Neo4j 工具查询入口。

## 当前行为

- Go 服务启动时从 `SC_WIKI_DATA_DIR/graph.json` 加载图谱快照，公开 `/api/knowledge-graph/overview`、`/papers/:paper_id`、`/papers/:paper_id/neighbors` 和 `/stats`。
- 前端 `/knowledge` 使用 `vis-network` 渲染图谱，按关系类型着色，支持点击节点、边、展开邻居和按关系类型筛选。
- 点击论文节点后，前端会调用 `/api/papers/:id` 加载论文详情并在侧栏展示。
- Python 侧另有 `/api/kg/*` 接口，委托 `backend.rag.tools.neo4j` 查询 Neo4j，支持论文搜索、论文上下文、材料上下文、多跳遍历和最短路径。
- 历史总结曾记录 639 篇论文、1459 种材料等数据规模；这些是特定数据快照，不作为当前部署的实时数量，当前数量需从运行中的图数据库和 `graph.json` 重新核验。

## 工作流程

公开页面优先请求 Go 知识图谱快照接口；Go 服务从内存中的 `graph.json` 节点和边生成概览或邻居数据。需要图数据库上下文时，Python KG 接口通过 Neo4j driver 执行 Cypher 查询并返回论文、材料、属性或路径信息。

## 约束

- Go 页面图谱依赖 `graph.json` 是否存在和格式是否正确。
- Python Neo4j 工具依赖 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD` 和图数据库数据。
- Go 快照图谱和 Python Neo4j 图谱是两条不同数据路径，二者同步关系需单独核验。

## 代码与测试

- Go API：`goserver/handlers/knowledge_graph.go`
- Go 路由：`goserver/main.go`
- Python API：`backend/api/kg.py`
- Neo4j 工具：`backend/rag/tools/neo4j.py`
- 页面：`frontend/src/pages/KnowledgeGraphPage.tsx`
- 测试：`tests/04_superconductivity_knowledge_graph/`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- `graph.json`、MySQL 和 Neo4j 三者之间的数据同步时机待核验。
- 旧版“关系提取、论文富化、Neo4j 同步”脚本在当前仓库中未找到，不能把历史流水线描述为当前可执行入口。
