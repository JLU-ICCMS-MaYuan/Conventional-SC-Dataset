# 知识图谱数据同步

## 功能说明

实现论文审批通过后自动同步到 Neo4j 知识图谱，以及历史数据的全量同步，确保图数据库与 MySQL 的论文、材料、作者数据保持一致。

## 当前行为

- **自动增量同步**：管理员审批论文通过后，Go 服务器（`goserver/handlers/admin.go` 的 `ReviewPaper()`）调用 Python 后端的 `POST /api/rag/papers/{id}/publish` 端点。该端点先将论文分块索引到 Qdrant（向量搜索），然后同步到 Neo4j（知识图谱）。同步内容包括：创建 `Paper` 节点（包含 `paper_id`、`title`、`knowledge_graph_title`、`doi`、`year`、`journal` 等属性），创建 `Researcher` 节点和 `AUTHORED` 关系（基于 `authors` 字段）。同步失败不影响 Qdrant 索引成功，使用 `MERGE` 保证幂等性。
- **手动全量同步**：管理员运行 `backend/ingest/sync_neo4j.py` 脚本（可选 `--clear` 清空图并重建约束，`--workers N` 指定并行度）。脚本从 MySQL 读取已审批论文、材料、物性数据，批量创建 Neo4j 节点和关系。同步内容包括：`Paper` 节点及其完整字段、`Material` 节点（从 `key_properties` 提取）、`Researcher` 节点、`STUDIES` 关系（论文 → 材料，基于 `research_materials` 和 `material_relations`）、`AUTHORED` 关系、`BUILDS_ON` 关系（基于 `builds_on` 字段，但目标是占位符）、`SHARES_STRUCTURE` 关系（材料间，基于空间群和晶体结构匹配）。
- **同步时机**：审批通过时自动触发增量同步；历史论文或数据修复需手动运行全量同步脚本。部署前审批的论文不会自动同步到 Neo4j。
- **数据一致性**：增量同步使用 `MERGE` 确保幂等性（重复发布不会创建重复节点）。全量同步可通过 `--clear` 清空图并重建，避免历史脏数据残留。

## 工作流程

新论文上传后，AI 提取元数据并保存到 MySQL。管理员在审核页面点击"通过"，Go 服务器标记 `review_status = 'approved'` 并调用 Python 发布端点。Python 后端读取论文数据，先嵌入分块并写入 Qdrant，再连接 Neo4j 创建 `Paper` 节点和 `Researcher` 节点及关系，最后返回索引和同步结果。用户刷新知识图谱页面即可看到新论文节点。历史论文需管理员在服务器上运行 `sync_neo4j.py`，脚本按批次并行处理全部已审批论文。

## 约束

- 增量同步依赖 Go 服务器审批流程正确调用 Python 发布端点。如果调用失败或 Python 服务不可达，论文不会同步到 Neo4j。
- 全量同步脚本直连 MySQL 和 Neo4j，需要正确的环境变量（`NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`）和数据库连接权限。
- 同步时间：单篇论文增量同步 < 1 秒；全量同步取决于论文数量和并行度（4 workers 同步 50 篇约 10 秒）。
- `graph.json` 快照（Go 服务器加载）与 Neo4j 数据是两条独立路径，当前未自动同步，需单独维护。
- 论文删除时需手动调用 `delete_paper_from_graph(paper_id)`（`backend/rag/tools/neo4j.py`）清理 Neo4j 节点，或重新全量同步。

## 代码与测试

- 增量同步：`backend/api/rag.py` `publish_approved_paper()` 端点
- 全量同步：`backend/ingest/sync_neo4j.py` `KGSync` 类
- 审批触发：`goserver/handlers/admin.go` `ReviewPaper()` → `publishApprovedPaperAt()`
- Neo4j 工具：`backend/rag/tools/neo4j.py` `_driver()`、`delete_paper_from_graph()`
- 环境配置：`dev.yaml` 或 `.env` 中的 `NEO4J_URI`、`NEO4J_USER`、`NEO4J_PASSWORD`

## 相关变更记录

- [Issue #70：知识图谱节点专用标题](../../specs/70-knowledge-graph-title/spec.md) - 增量同步逻辑中添加 `knowledge_graph_title` 字段

## 已知问题

- 历史论文（自动同步功能部署前审批的）需要手动运行 `sync_neo4j.py` 全量同步。
- 论文修改后（如更新标题、作者）不会自动重新同步到 Neo4j，需重新发布或全量同步。
- 论文删除时 Neo4j 节点不会自动清理，需手动调用删除函数或重新全量同步。
- `graph.json` 与 Neo4j 数据未自动同步，Go API 知识图谱快照可能与 Python Neo4j API 数据不一致。
- 全量同步的 `--clear` 选项会删除全部图数据并重建，在生产环境需谨慎使用，建议先备份 Neo4j 数据。
