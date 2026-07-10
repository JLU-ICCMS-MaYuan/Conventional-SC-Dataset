# 领域文档迁移实施记录

> **面向代理执行者：** 此记录原计划要求使用
> `superpowers:subagent-driven-development` 或 `superpowers:executing-plans`
> 按任务执行。迁移已在 `mayuan` 分支完成并提交。

**目标：** 用经代码和测试验证的领域文档替代七个混合“规划与现状”的编号功能目录，
使其成为 SC-Wiki 当前行为的权威说明。

**结构：** `docs/domains/` 描述稳定业务与模块边界；`docs/operations/` 描述已验证的
运行约束；项目记忆库只链接它们，不重复细节。确认的当前事实被吸收后，编号功能文档
被删除；未实现能力不被写为当前事实。

**技术栈：** Markdown、GitHub Issues、FastAPI、React、SQLAlchemy、Alembic、
RAG/ChromaDB。

## 全局约束

- 只记录能由代码、测试、配置或已关联 GitHub Issue 支持的行为。
- 不保留 `docs/01-*` 至 `docs/07-*` 的副本。
- 尚未承诺的能力使用 GitHub `type:idea`；已验证但尚未文档化的事实使用
  `type:doc-debt`。
- 每份领域页必须链接代码入口、关键测试、相关运行/决策文档和已知缺口。
- 本迁移不修改业务代码、迁移、依赖或既有未提交前端文件。

---

## 勘察依据

| 文件 | 角色 | 是否阅读 | 原因 | 来源 |
| --- | --- | --- | --- | --- |
| `backend/main.py` | FastAPI 组合根 | 是 | 确定活跃路由和 SPA 行为。 | 代码勘察 |
| `backend/models.py` | 主目录数据模型 | 是 | 确定持久化业务实体。 | 代码勘察 |
| `backend/api/admin.py` | 审核治理 API | 是 | 核验审核和可见性事实。 | 代码勘察 |
| `backend/api/structures.py` | 结构生命周期 API | 是 | 核验上传、审核和代表结构选择。 | 代码勘察 |
| `backend/api/rag.py` | RAG HTTP 边界 | 是 | 核验 RAG 接口和访问规则。 | 代码勘察 |
| `backend/rag/rag/engine.py` | RAG 编排 | 是 | 核验意图、关系查询、向量与流式流程。 | 代码勘察 |
| `backend/api/tc_predict.py` | Tc 估算 API | 是 | 核验输入和非持久化行为。 | 代码勘察 |
| `frontend/src/App.tsx` | 用户路由图 | 是 | 区分已暴露页面和规划 UI。 | 代码勘察 |
| `start.sh` | 运行启动路径 | 是 | 核验迁移、种子和 Uvicorn 顺序。 | 运行勘察 |
| `backend/rag/config.py` | RAG 运行配置 | 是 | 核验独立数据资产和环境变量。 | 运行勘察 |
| `docs/01-*` 至 `docs/07-*` | 历史混合文档 | 是 | 提取事实后删除全部 28 份文件。 | 文档勘察 |

## 任务 1：建立领域与运行索引

**文件：**

- 新建：`docs/domains/README.md`
- 新建：`docs/operations/README.md`
- 修改：`docs/README.md`
- 修改：`docs/memory/README.md`

- [x] 将 `docs/domains/` 定义为业务和模块行为的唯一当前事实层。
- [x] 将 `docs/operations/` 定义为部署、持久化、环境、导入和恢复的唯一当前事实层。
- [x] 从文档根目录和项目记忆库增加链接，且不复制详细内容。
- [x] 验证索引新增的本地 Markdown 链接全部可解析。

## 任务 2：回填目录、检索与贡献领域

**文件：**

- 新建：`docs/domains/core-superconductor-catalog.md`
- 新建：`docs/domains/search-and-external-catalogs.md`
- 新建：`docs/domains/contribution-upload-and-review.md`
- 新建：`docs/domains/crystal-structure-lifecycle.md`

**证据：** `backend/models.py`、`backend/api/papers.py`、`backend/api/admin.py`、
`backend/api/structures.py`、`backend/services/structure_storage.py`、
`frontend/src/App.tsx`，以及 `tests/01_*`、`tests/02_*`、`tests/03_*`。

- [x] 记录每个领域的实体、模块边界、公开行为、不变量、代码入口、测试和已知缺口。
- [x] 明确 `CompoundPage` 的普通文献上传调用尚非端到端闭环能力。
- [x] 记录结构审核后的代表结构选择规则及其 API/测试证据。
- [ ] 将统一上传、批量清洗和未核验 UI 工作流转为关联的 GitHub Idea 或文档债。

## 任务 3：回填 RAG、关系查询、估算与指标领域

**文件：**

- 新建：`docs/domains/rag-and-knowledge-graph.md`
- 新建：`docs/domains/tc-prediction.md`
- 新建：`docs/domains/researcher-contribution-metrics.md`

**证据：** `backend/api/rag.py`、`backend/rag/service.py`、
`backend/rag/rag/engine.py`、`backend/rag/knowledge_graph.py`、
`backend/rag/ingest/pipeline.py`、`backend/api/tc_predict.py`，以及
`tests/04_*` 至 `tests/07_*`。

- [x] 只将知识图谱描述为 RAG 内部关系查询投影，而非公开独立图谱产品。
- [x] 记录 RAG 的独立数据库/向量资产和 PDF 摄入边界，并标注认证与审核整合缺口。
- [x] 记录 Tc 估算为即时 CONTCAR/PDOS 特征计算，且没有持久化预测历史。
- [x] 将历史“社区/论坛”命名收敛为可验证的研究者贡献指标，不承诺论坛能力。

## 任务 4：回填运行手册

**文件：**

- 新建：`docs/operations/runtime-and-deployment.md`
- 新建：`docs/operations/data-and-rag-assets.md`
- 新建：`docs/operations/import-and-recovery.md`
- 修改：`docs/deploy.md`

**证据：** `start.sh`、`Procfile`、`backend/main.py`、`backend/database.py`、
`alembic/env.py`、`backend/init_db.py`、`backend/rag/config.py`、
`backend/import_data.py`、`backend/rag/ingest/*.py`、`.gitignore` 和
`docs/deploy.md`。

- [x] 将 `start.sh` 记录为完整启动路径，并说明直接使用 `Procfile` 的限制。
- [x] 记录主库、RAG 关系库和 Chroma 资产的独立持久化责任。
- [x] 记录破坏性导入和集合重建的备份、验证、恢复和外部 API 成本前置条件。
- [x] 删除引用缺失 `.env.example` 或允许跳过初始化的历史部署说法。

## 任务 5：记录文档债并删除历史文档

**文件：**

- 删除：`docs/01-decentralized-uploading/`
- 删除：`docs/02-maintenance-and-verification/`
- 删除：`docs/03-data-search-and-database-discovery/`
- 删除：`docs/04-superconductivity-knowledge-graph/`
- 删除：`docs/05-rag-question-answering/`
- 删除：`docs/06-ai-assisted-tc-estimation/`
- 删除：`docs/07-researcher-community-forum/`
- 修改：`docs/README.md`

- [ ] 为主/RAG 同步和前端构建输入等事实缺口创建或关联 GitHub `type:doc-debt`。
- [ ] 为论坛、独立图谱和其他历史规划能力创建或关联 GitHub `type:idea`。
- [x] 在确认事实已进入 `docs/domains/` 或 `docs/operations/` 后删除全部 28 份旧文档。
- [x] 用新的领域和运行导航替换七模块表格。

## 任务 6：验证迁移

- [x] 运行 `git diff --check`。
- [x] 验证没有 Markdown 链接指向已删除的 `docs/01-*` 至 `docs/07-*`。
- [x] 验证每个领域页包含证据路径和已知缺口。
- [ ] 仅为重新核验的行为运行针对性测试；不得修复无关测试失败。
- [x] 确认 `git status --short` 只显示获准的文档变更和既有用户变更。

## 执行说明

- 创建 GitHub Issue 不在当时确认的迁移范围内，两项 Issue 转化任务保留为后续工作。
- `sc-wiki` Conda 环境下使用 `PYTHONPATH=.` 运行基线测试，结果为 125 个通过、
  1 个失败、7 个跳过。失败的 RAG 页面测试期望 `frontend_build/index.html`，但提交的
  静态资产位于 `frontend/static/`；本次没有修改业务代码来处理该既有部署不一致。
