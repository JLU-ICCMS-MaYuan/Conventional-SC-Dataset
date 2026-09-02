# 知识图谱节点标题

## 功能说明

为知识图谱的 Paper 节点生成和展示专用标题，高度凝练论文核心贡献（15-30 字），替代冗长的原始标题，提升图谱可读性。

## 当前行为

- MySQL `papers` 表包含 `knowledge_graph_title VARCHAR(200)` 字段，存储凝练标题。
- AI 提取论文时（`backend/ingest/upload_jobs.py` 的 `SUMMARY_SYSTEM_PROMPT`）自动生成知识图谱标题：要求包含核心发现、材料体系名称，突出历史地位（"首次"）或突破性质（"高温"/"常压"），避免系列编号和冗长修饰。
- 引用图 API（`goserver/handlers/knowledge_graph.go`）优先返回 `knowledge_graph_title`，对已有论文降级到 `title`。
- 引用图的公开节点直接来自 MySQL，不需要把短标题同步到 Neo4j；历史 Neo4j 页面仍可按原流程使用该字段。
- 前端知识图谱页面（`/knowledge`）从 API 获取节点数据时，`nodes[].label` 字段即为凝练标题，无需前端额外处理。

**示例对比**：

| 原始标题 | 知识图谱标题 |
|---------|-------------|
| Further experiments with liquid helium. V. The disappearance of the resistance of mercury | 首次发现超导体 Hg |
| High-temperature superconductivity in cuprate superconductors | 铜氧化物高温超导 |
| Theory of Superconductivity | BCS 超导理论 |

## 工作流程

新论文上传后，AI 从标题、摘要、正文提取元数据时同时生成知识图谱标题并保存到 `papers.knowledge_graph_title`。前端请求引用图总览或邻居节点时，Go API 直接查询 MySQL 并优先返回凝练标题；对于未生成标题的历史论文，fallback 到原始 `title`。

## 约束

- 字段长度限制 VARCHAR(200)，实际建议 ≤ 30 字（中文）或 15 词（英文）。
- 生成质量依赖 AI 模型理解论文核心贡献的能力，可能需要人工审核优化。
- 历史论文需要手动补充标题或重新生成富化字段。
- 标题更新后引用图查询直接读取 MySQL；旧 Neo4j 页面仍需重新发布或单独同步。

## 代码与测试

- 数据库迁移：`alembic/versions/20260831_175226_add_knowledge_graph_title.py`
- 模型定义：`backend/models.py` `Paper.knowledge_graph_title`
- AI 生成：`backend/ingest/upload_jobs.py` `SUMMARY_SYSTEM_PROMPT`
- 展示 API：`goserver/handlers/knowledge_graph.go` `/overview`、`/papers/{id}/neighbors`、`/search`、`/stats`
- 同步逻辑：`backend/api/rag.py` `publish_approved_paper()`、`backend/ingest/sync_neo4j.py`
- 前端页面：`frontend/src/pages/KnowledgeGraphPage.tsx`

## 相关变更记录

- [Issue #70：知识图谱节点专用标题](../../specs/70-knowledge-graph-title/spec.md)

## 已知问题

- 未生成标题的历史论文需手动补充：通过数据库 `UPDATE` 或重新触发发布端点。
- 暂无管理界面支持手动编辑标题，需直接操作数据库或 Neo4j。
- 同一材料体系多篇论文可能生成相似标题，缺少唯一性约束和质量评分机制。
