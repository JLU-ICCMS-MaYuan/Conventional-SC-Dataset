# 技术研究：引用图谱

**GitHub Issue**：[ #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)

## R1：GROBID 作为本地引用解析器

**决策**：在 Docker Compose 部署独立 GROBID 服务，Worker 用 `processFulltextDocument` 获取 TEI，再解析文末 `biblStruct`。不使用 LLM 从 PDF 文本猜参考文献。

**理由**：GROBID 官方说明其 PDF 全文服务包含参考文献解析、DOI/题名/作者/年份提取和引用上下文识别；项目许可证为 Apache-2.0。其结果有 F1 指标而非 100% 承诺，因此解析失败必须成为可保存状态，不能被误写为“没有引用”。

**备选方案**：继续用 PyMuPDF 文本加 LLM 解析。拒绝，因为不同期刊引用格式会使提示词输出不可追溯、不可稳定重跑。

**证据**：[GROBID README](https://github.com/grobidOrg/grobid)、[GROBID 服务 API](https://grobid.readthedocs.io/en/latest/Grobid-service/)、[Docker 文档](https://grobid.readthedocs.io/en/latest/Grobid-docker/)。

## R2：MySQL 是引用事实权威

**决策**：原始参考文献、匹配状态和人工标记存 MySQL；图 API 直接查询 MySQL。旧 Neo4j 只可作为未来可重建投影。

**理由**：当前 `sync_neo4j.py` 把 `builds_on` 自由文本写为 `BUILDS_ON`，甚至会建立 `paper_id=-1` 的占位节点，不能代表真实引用关系。图谱公开端点当前又经 Go 转发 Python/Neo4j，增加两个数据权威会让引用计数和版本过滤失真。

**备选方案**：直接扩展 Neo4j 并由它保存引用。拒绝，因为论文审核、版本和删除完整性已经由 MySQL 管理。

**证据**：`backend/ingest/sync_neo4j.py`、`goserver/handlers/knowledge_graph.go`、`docs/specs/33-paper-lineage-integrity/data-model.md`。

## R3：引用记录保存原文，图边按论文去重

**决策**：一条 bibliography item 一条 `paper_references`；同一引用论文对同一被引论文的多条记录，在图和库内被引计数中只算一次。

**理由**：原文保存保证解析可复核、支持后续重新匹配；将重复参考文献直接视为多条图边会夸大被引量且造成渲染重复。

**备选方案**：只保存 `(citing_paper_id, cited_paper_id)`。拒绝，因为未入库引用、解析字段、歧义和错误无法保留。

## R4：保守自动匹配与未来重试

**决策**：规范 DOI 精确匹配优先；无 DOI 时只对规范化题名完全相同且年份不冲突的唯一候选匹配。新 Paper 批准后扫描未匹配参考文献重试。

**理由**：错误边会直接伪造科研发展史，漏匹配可在未来数据到来时补齐。题名模糊相似度或 LLM 判定不能在无人审核时产生事实边。

**备选方案**：模糊相似度阈值自动匹配。拒绝，因为短标题、预印本/正式版和同题系列论文存在高误配风险。

## R5：分页邻居代替固定深度或全图加载

**决策**：每次展开仅请求一个方向的一页，前端默认大小为 5，显示精确剩余数；没有产品层面的固定深度或全局节点上限。

**理由**：用户可持续深入任一分支，但不会因为一篇被引用数百次的论文一次生成数百个 DOM 和物理节点。传输层仍限制单请求最大 50，防止异常客户端无分页读取。

**备选方案**：固定三层、总计 31 节点。拒绝，因为会隐藏用户主动希望继续查看的上游路径。

## R6：复用当前论文级分类

**决策**：Material family 通过 `paper_material_families` 当前版本多选关联筛选；常规/非常规则直接使用 #80 的 `papers.superconductor_kind`。`unknown` 不进入两种视图。

**理由**：这与当前唯一事实来源一致；不再把已退役的 `material_states.superconductor_kind` 重新引入图查询。

**证据**：`goserver/models/models.go`、`alembic/versions/20260902_0002_paper_material_families.py`、`alembic/versions/20260902_0003_paper_superconductor_kind.py`。

## R7：论文年份与外部引文年份分开约束

**决策**：`papers.year` 必须存在；`paper_references.year` 可以为空。

**理由**：SC-Wiki 论文需要稳定的时间轴和发展历程排序，空年份会让节点无法定位。外部参考文献的年份可能被 GROBID 漏解析，不能因此丢掉原始引文或伪造年份。迁移在已有空值时停止，要求先由管理员补全。
