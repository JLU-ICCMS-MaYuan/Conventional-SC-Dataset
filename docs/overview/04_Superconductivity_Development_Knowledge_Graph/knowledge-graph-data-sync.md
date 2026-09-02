# 知识图谱数据同步

## 功能说明

引用图不依赖 Neo4j 同步。论文 PDF 上传后由独立 GROBID 服务解析参考文献，Python 只保存可追溯的解析结果；Go 在公开查询时从 MySQL 实时投影引用边。

## 当前流程

1. 上传 Worker 找到正文 PDF，调用 `processFulltextDocument`，从 TEI 的 `biblStruct` 中提取 DOI、题名、作者、年份和原始引文。
2. 解析状态与参考文献先放入 Redis 草稿，校对页默认显示前 5 条，其余由用户展开；GROBID 不可用时保留 `unavailable` 状态，不阻断人工校对。
3. 提交论文时，服务端把当前版本的解析结果写入 `paper_reference_extractions` 和 `paper_references`，按 DOI 精确匹配，或按规范化题名加不冲突年份做唯一匹配。
4. 论文审核通过后，重试该论文的出边，并扫描历史 `unmatched/ambiguous` 记录。目标论文以后进入 SC-Wiki 时，未匹配引文可以形成关系。
5. 论文升版时，系统先读取旧版本主 PDF，重新调用 GROBID，再把新解析结果写入新版本；旧版本引用不会通过版本级联继续作为新版本事实。若主 PDF 不可用或 GROBID 失败，新版本只记录 `unavailable/failed` 状态，不保留旧引用。论文删除时先清理引用源记录和图谱标记。

## 事实边界

- MySQL 的 `paper_references` 是引用事实唯一来源。LLM 不得从正文、`builds_on` 或自由文本生成引用边，也不能用模糊相似度自动造边。
- GROBID 解析结果不是“100% 成功”保证；结构化结果、失败信息和未匹配原文都必须保留，便于人工复核或以后重试。
- Neo4j 和 `graph.json` 仍可被旧功能使用，但不会影响本引用图的边、节点或被引次数。

## 运行配置

- Compose 服务：`grobid` 使用 `lfoppiano/grobid:0.8.1`，健康检查 `/api/isalive`。
- Python 与 Worker 使用 `GROBID_URL=http://grobid:8070`，并等待 `grobid` 健康后启动。
- 迁移：`alembic/versions/20260902_0004_paper_citation_graph.py`。迁移前会检查 `papers.year`，发现空值时明确失败，必须先补全。

## 代码与测试

- 解析、匹配和重试：`backend/services/citation_graph.py`
- Worker：`backend/ingest/upload_jobs.py`
- 提交与审核触点：`backend/api/rag.py`、`goserver/handlers/admin.go`
- Schema 测试：`tests/02_maintenance_and_verification/test_issue81_citation_graph_schema.py`
