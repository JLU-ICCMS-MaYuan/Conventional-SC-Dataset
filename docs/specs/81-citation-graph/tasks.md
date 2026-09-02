# 实施任务：基于引用关系的超导论文发展知识图谱

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：基础能力

**目的**：为引用事实建立唯一持久化模型与本地解析服务。

- [x] T001 在 `alembic/versions/20260902_0004_paper_citation_graph.py` 创建引用解析、参考文献和里程碑表及当前版本/删除完整性约束，并落实 `papers.year` 非空迁移前检查。
- [x] T002 [P] 在 `backend/models.py` 与 `goserver/models/models.go` 定义三张新表模型和 Paper 关联。
- [x] T003 [P] 在 `docker/compose.yaml` 添加 GROBID 服务、healthcheck、Python/Worker 地址配置与依赖。
- [x] T004 在 `tests/02_maintenance_and_verification/test_issue81_citation_graph_schema.py` 覆盖新 Schema、唯一键、状态约束、外键语义和年份约束。

## 阶段 2：用户故事 1——解析、保存与匹配引用（P1，MVP）

**目标**：上传和审核生命周期形成可追溯的引用记录与可延迟补全关系。

**独立验收**：上传引用 A 的 B，先后审核两篇论文后能自动形成 B -> A；解析故障仅留下状态，不产生边。

### 测试

- [x] T005 [P] [US1] 在 `backend/tests/test_citation_graph.py` 编写 GROBID TEI 解析、DOI 优先、题名年份保守匹配、歧义保留和重试匹配测试。
- [x] T006 [P] [US1] 在 `backend/tests/test_citation_graph.py` 编写版本替换和重复原始引文去重计数测试；在科学数据升版测试中验证新版本重新解析引用。

### 实施

- [x] T007 [US1] 新增 `backend/services/citation_graph.py`，封装 GROBID HTTP/TEI 解析、DOI/题名规范化、引用持久化和匹配重试。
- [x] T008 [US1] 修改 `backend/ingest/upload_jobs.py`，在既有 Worker 中调用 T007 并把解析状态和候选写入草稿。
- [x] T009 [US1] 修改 `backend/api/rag.py` 与 `backend/ingest/scientific_drafts.py`，在提交、升版和批准后持久化/重试当前版本引用，并在提交时校验年份。

## 阶段 3：用户故事 2、3——公开图查询和渐进展开（P1）

**目标**：直接从 MySQL 返回分类概览、标题搜索和可分页的上下游引用图。

**独立验收**：A/B/C 菱形关系只出现一个 A；双向第一页为五条以内并返回准确 `remaining_count`。

### 测试

- [x] T010 [P] [US2] 在 `goserver/handlers/knowledge_graph_test.go` 覆盖审核边界、分类组合、`unknown`、库内去重被引次数和标题搜索。
- [x] T011 [P] [US3] 在 `goserver/handlers/knowledge_graph_test.go` 覆盖方向、分页排序、剩余数量、重复节点与循环安全形态。

### 实施

- [x] T012 [US2] 重写 `goserver/handlers/knowledge_graph.go`，以 MySQL 实现概览、搜索、节点详情和统计，禁止代理 Neo4j。
- [x] T013 [US3] 在 `goserver/main.go` 注册搜索、分页展开与节点端点，保持现有概览路径兼容。
- [x] T014 [US2] 修改 `frontend/src/pages/KnowledgeGraphPage.tsx`，按 `paper_id` 去重、用库内引用数映射圆点、加入分类筛选和标题搜索固定。
- [x] T015 [US3] 修改 `frontend/src/pages/KnowledgeGraphPage.tsx`，实现双向分页展开和“尚有 N 篇”交互，不自动递归加载。

## 阶段 4：用户故事 4——人工里程碑（P2）

**目标**：管理员可维护源头与突破，读者可查看。

### 测试

- [x] T016 [P] [US4] 在 `goserver/handlers/knowledge_graph_test.go` 覆盖管理员/超级管理员写入、普通用户拒绝、整体替换和未审核论文拒绝。

### 实施

- [x] T017 [US4] 新增 `goserver/handlers/paper_graph_marks.go` 并在 `goserver/main.go` 注册管理员整体替换路由。
- [x] T018 [US4] 修改 `frontend/src/pages/KnowledgeGraphPage.tsx`，显示里程碑并在管理员详情区提供标记编辑。

## 最终阶段：完善与验证

- [x] T019 [P] 更新 `docs/overview/04_Superconductivity_Development_Knowledge_Graph/README.md`、上传解析与论文查询 Overview，记录已实现事实。
- [x] T020 运行 [quickstart.md](quickstart.md) 中可用的 Python、Vitest、构建、Go 和 Compose 配置验证；隔离 MySQL 升版回归测试保留为需显式提供 `FRESH_MYSQL_DATABASE_URL` 的环境验收。
- [x] T021 对照 Spec 执行收敛检查，确认分类契约与引用图需求无冲突。

## 依赖与执行顺序

- T001 阻断 T002、T007、T012 和 T017。
- T003 阻断真实 GROBID 验收，但不阻断 TEI 单元测试。
- T005、T006 先于 T007–T009；T010、T011 先于 T012–T015；T016 先于 T017。
- T014 与 T015 同文件，必须串行；T017 与 T018 以 API 契约为顺序。
- T019、T020、T021 依赖所有功能故事。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001–FR-004 / SC-001–SC-002 | T001–T009 | 解析、保存、匹配与重试 |
| FR-005–FR-007 / SC-003 | T010、T012–T014 | 当前公开图、分类和节点形态 |
| FR-008–FR-010 / SC-004 | T011、T013–T015 | 分页、去重和循环安全 |
| FR-011 / SC-005 | T016–T018 | 人工标记权限与展示 |
| FR-012–FR-013 / SC-006–SC-007 | T001、T009、T012、T019–T021 | MySQL 权威、年份完整性、文档和验证 |

## MVP 与增量策略

1. 完成 T001–T013 后，引用事实和 MySQL 图 API 已可独立验收。
2. 完成 T014–T015 后，读者可用界面浏览发展脉络。
3. 完成 T017–T018 后，加入人工科研里程碑。
