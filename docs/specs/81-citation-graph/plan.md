# 实施计划：基于引用关系的超导论文发展知识图谱

**GitHub Issue**：[ #81](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/81)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)

## 摘要

新增 MySQL 引用记录与人工里程碑表。Python Worker 调用 GROBID 并保存引用，Python 提交流程负责持久化与重试匹配；Go API 直接从 MySQL 生成公开图投影和管理员标记接口；React 页面按页扩展图节点。旧 Neo4j 引用式页面不再承担引用事实查询。

## 技术上下文

- **语言与版本**：Python 3、Go、TypeScript 5.6、React 19。
- **主要依赖**：FastAPI、SQLAlchemy、Alembic、GORM、Gin、MUI、vis-network、Vitest、pytest。
- **数据存储**：MySQL 为引用事实权威；Redis 为短期上传草稿；Neo4j 不写入本 Feature 的引用事实。
- **外部服务**：Docker Compose 内 GROBID HTTP 服务；Worker 超时后保存 `unavailable` 状态。
- **测试体系**：`backend/tests/` 与 `tests/` 的 pytest、`goserver/*_test.go`、Vitest 与 `npm run build`。
- **性能目标**：默认图响应最多 30 个概览节点或 5 个邻居；单次请求最多 50 个邻居。
- **兼容约束**：只读当前已审核论文，保留 #70、#79、#80 分类契约；不把旧 `builds_on` 转成引用。
- **数据完整性**：论文主表 `year` 非空；迁移先检查历史空值，提交和审核接口返回明确的 `year_required`。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| `AGENTS.md` | GitHub Issue 为协作权威，Spec 与 Issue 双向链接 | #81 与本目录互链 | 通过 |
| #79 | Material family 为论文级多选 | 图查询以当前版本关联 `EXISTS` 过滤 | 通过 |
| #80 | Superconductor type 为论文级单选 | 图查询读取 `papers.superconductor_kind` | 通过 |
| #33 | 当前 revision 是公开内容边界 | 源端引用记录绑定 revision，图过滤两端已审核当前版本 | 通过 |
| Spec FR-010 | 不以 DAG 删除事实 | 数据库不做环约束；查询按 ID 去重 | 通过 |
| 用户确认 Q53 | `papers.year` 必须有值 | ORM、迁移、提交和审核共同校验 | 通过 |

## 源代码结构

```text
alembic/versions/20260902_0004_paper_citation_graph.py  # 新表与约束
backend/services/citation_graph.py                       # GROBID TEI、持久化、匹配和重试
backend/ingest/upload_jobs.py                            # Worker 中的 GROBID 阶段
backend/api/rag.py                                       # 提交、升版与批准后匹配触点
backend/models.py                                        # Python ORM
goserver/models/models.go                                # Go ORM
goserver/handlers/knowledge_graph.go                     # MySQL 公开图 API
goserver/handlers/paper_graph_marks.go                   # 管理员里程碑 API
goserver/main.go                                         # 路由与权限
frontend/src/pages/KnowledgeGraphPage.tsx                # 分类、搜索、分页展开 UI
docker/compose.yaml                                      # GROBID 服务、Worker 依赖和配置
```

**结构选择**：解析和匹配逻辑集中在一个 Python 服务，避免在上传、提交、审核重复实现 DOI/题名规则。Go 只负责公开查询和权限受控标记，避免通过 HTTP 再转发 Neo4j。前端只保存当前视图，节点唯一键始终为 `paper_id`。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001–FR-004 / US1 | `citation_graph.py`、Worker、提交与批准触点 | GROBID TEI 与自动重试 pytest |
| FR-005–FR-010 / US2–US3 | 引用表、`knowledge_graph.go`、图页面 | Go 查询测试、前端分页/去重测试 |
| FR-011 / US4 | `paper_graph_marks.go`、管理员路由 | 权限和整体替换 Go 测试 |
| FR-012 | 直接 MySQL 查询 | 路由测试不调用 Neo4j |

## 阶段与依赖

1. 建立 Schema、Python/Go 模型和 GROBID 服务配置。
2. 在 Worker、提交与批准路径持久化、匹配和重试引用。
3. 用 MySQL 替换公开图 API，并增加管理员里程碑维护。
4. 改造图谱页面，完成分类、搜索和分页展开。
5. 执行跨层测试、构建和 quickstart。

## 必要复杂度

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 原始参考文献与图边分离 | 必须保留未匹配引文和匹配依据 | 只存边会丢失原文和未来重试能力 |
| Python 持久化 + Go 查询 | 上传/审核事实由 Python 产生，公开 API 已由 Go 承担 | 继续 Go 转发 Neo4j 会出现第二个事实来源 |
