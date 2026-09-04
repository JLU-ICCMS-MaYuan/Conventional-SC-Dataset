# 实施任务：审核编辑页元数据与成功返回工作台

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

## 阶段 1：用户故事 1——核对审核元数据（P1）

**目标**：审核入口可见上传者并提供历史入口。

**独立验收**：列表夹具中的上传者和历史入口显示在红框操作区域，空上传者有稳定回退。

- [x] T001 [US1] 在 `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx` 增加列表上传者、历史入口和无记录列的回归测试。
- [x] T002 [US1] 在 `frontend/src/pages/AdminPage.tsx` 的论文列表操作区域渲染上传者和“历史”按钮，不显示物性记录数量。

## 阶段 2：用户故事 2——成功后返回工作台（P1）

**目标**：审核成功后立即回到当前角色工作台。

**独立验收**：超级管理员进入 `/superadmin`，管理员进入 `/admin`，失败时不导航。

- [x] T003 [US2] 在 `tests/02_identity_governance/admin-edit-page.test.tsx` 增加管理员、超级管理员成功导航及失败停留的失败回归测试。
- [x] T004 [US2] 在 `frontend/src/pages/AdminPaperEditPage.tsx` 的 `handleEditReview` 成功分支调用 `navigate(workspacePath)`。

## 最终阶段：验证与文档

- [x] T005 运行 `tests/02_identity_governance/admin-edit-page.test.tsx` 和前端生产构建，并记录结果。
- [x] T006 使用 `big-project-overview-maintainer` 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md` 的已实现审核行为。

## 依赖与执行顺序

- T001 在 T002 前执行；T003 在 T004 前执行。
- T002 与 T004 修改同一页面文件，串行执行。
- T005 依赖 T001 至 T004；T006 依赖真实实现与验证结果。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001/FR-002 / US1 | T001-T002 | 元数据展示与空值边界 |
| FR-003/FR-004 / US2 | T003-T004 | 按角色导航与失败不跳转 |
| SC-004 | T005 | 前端生产构建 |

## Phase 3: Convergence - 真实接口与文献处理历史

**差距来源**：T001-T006 仅对前端夹具做了元数据断言；真实 `GET /api/admin/papers/:id`
此前没有返回 `uploader_name`，且没有上传/修改/审核统一历史。因此旧任务不能作为本 Feature
已完成的证据。T028 进一步收敛掉未被需求使用的记录数展示。

### 基础与迁移

- [x] T007 在 `tests/01_decentralized_uploading/test_issue51_fresh_mysql_migration.py` 增加迁移后表结构与外键断言；旧审核事件转化、上传回填和意见保留由隔离 MySQL 升级路径验收。
- [x] T008 在 `alembic/versions/20260903_0002_paper_history_events.py` 修复 MySQL 外键索引依赖顺序，并支持从半执行状态继续，将 `paper_review_events` 演进为唯一的 `paper_history_events`。
- [x] T009 [P] 在 `backend/models.py` 与 `goserver/models/models.go` 将 `PaperReviewEvent` 演进为 `PaperHistoryEvent`，并定义不可变事件字段与关系。
- [x] T010 在 `backend/services/paper_history.py` 与 `goserver/handlers/paper_history.go` 建立对应的历史事件创建辅助，校验事件类型、审核字段和操作标识幂等性。

### 用户故事 1：真实元数据（P1）

**独立验收**：真实管理端列表对有/无上传者返回正确字段，详情不重复返回上传者且不返回 `record_count`；列表显示正确。

- [x] T011 [US1] 在 `goserver/handlers/paper_detail_test.go` 为管理端列表和详情接口增加真实上传者、空值回退、不重复返回上传者和不返回 `record_count` 的回归测试。
- [x] T012 [US1] 在 `goserver/handlers/admin.go` 组装管理端列表/详情 DTO 并加载上传者，不计算物性数量。

### 用户故事 2：历史时间线（P1）

**独立验收**：管理员可查看时间线，普通用户不能读取；审核事件显示每位审核人的意见。

- [x] T013 [US2] 在 `goserver/handlers/paper_history_test.go` 新增历史 API 的管理员授权、排序、未知上传者和审核意见测试。
- [x] T014 [US2] 在 `goserver/main.go` 与 `goserver/handlers/admin.go` 注册并实现 `GET /api/admin/papers/:id/history`。
- [x] T015 [US2] 在 `tests/01_decentralized_uploading/admin-paper-classification-review.test.tsx` 覆盖列表历史入口、按需加载和时间线展示；入口文案由 T028 修订为“历史”。
- [x] T016 [US2] 在 `frontend/src/pages/AdminPage.tsx`、`frontend/src/i18n/zh/admin.ts` 与 `frontend/src/i18n/en/admin.ts` 实现列表历史入口和时间线 Dialog。

### 用户故事 3：可信写入、统计与删除（P1）

**独立验收**：上传、实际修改和每次审核各追加一次；两段保存不重复；统计和删除保持正确。

- [x] T017 [US3] 在 `backend/tests/test_upload_workflow.py` 覆盖新上传与上传请求重试只写一条 `uploaded` 历史。
- [x] T018 [US3] 在 `backend/api/rag.py` 的待审论文创建事务中追加 `uploaded` 事件，并使用 `upload_task_id` 幂等。
- [x] T019 [US3] 在 `goserver/handlers/admin_review_event_test.go` 覆盖审核事件迁移、空意见、审核重试和当前最终状态不回退。
- [x] T020 [US3] 在 `goserver/handlers/admin.go` 将审核与论文级修改接入历史写入，比较实际变更并使用 `history_operation_id`。
- [x] T021 [US3] 在 `backend/tests/test_scientific_draft_rewrite.py` 覆盖科学数据实际变更、同值保存和操作标识去重。
- [x] T022 [US3] 在 `backend/api/rag.py` 与 `backend/services/scientific_draft_rewrite.py` 接收 `history_operation_id`、判断语义变化并追加或去重 `modified` 事件。
- [x] T023 [US3] 在 `frontend/src/pages/AdminPaperEditPage.tsx` 让一次“保存修改”向两段请求传递同一 `history_operation_id`。
- [x] T024 [P] [US3] 在 `goserver/handlers/contribution_ranking_test.go` 与 `goserver/handlers/stats.go` 只统计 `reviewed` 事件。
- [x] T025 [P] [US3] 在 `goserver/handlers/paper_deletion_test.go` 与 `goserver/handlers/paper_deletion.go` 将处理历史加入物理删除拓扑。

### 验证与文档

- [x] T026 运行 Alembic 新库迁移、目标 Go/Python/Vitest 回归测试和 `cd frontend && npm run build`，将 SC-001 至 SC-008 的对应证据回写 `docs/specs/87-review-workspace/quickstart.md`。
- [x] T027 使用 `big-project-overview-maintainer` 更新 `docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md`，只记录已落地的处理历史行为。

## 真实数据库验收

- 已使用临时隔离 MySQL 库完成从空库到 `networked_news_discovery` 的完整升级，并验证 `paper_history_events` 的事件字段和两条外键；当前本地库也已从半执行状态恢复到 head。

## 收敛依赖

- T007-T010 阻断所有新写入、读取、统计和删除工作。
- T011-T012、T013-T016 可在基础完成后并行；同一文件内任务仍串行。
- T017-T025 在历史模型和辅助写入可用后按上传、审核、编辑、统计、删除顺序执行。
- T026 依赖全部实现任务；T027 只能在真实实现与验证后执行。

## Phase 4: Convergence - 元数据区收敛为上传者与历史

**差距来源**：用户确认红框位于管理工作台论文列表每行的操作区域；原有 `record_count` 统计和
“物性记录”展示不是所需功能，且容易被误认为处理历史。历史入口应从列表直接打开。

- [x] T028 在 `goserver/handlers/admin.go`、`frontend/src/pages/{AdminPage,AdminPaperEditPage}.tsx`、中英文文案与目标测试中移除列表/详情 `record_count`、所有物性记录数量展示和“处理记录”文案；将“历史”入口放到论文列表每行操作区域，保留历史 API 和时间线，并验证新契约。

**T028 验证记录（2026-09-04）**：Go 全量测试通过；目标 Vitest `12 passed`；前端生产构建通过。
全量 Vitest 为 `211 passed, 3 failed`，失败位于既有科学数据空态和新闻采集用例，不属于本 Feature。

## Phase 5: Convergence - 上传者链接与图标化历史入口

**差距来源**：用户进一步确认上传者需要跳转公开用户页，历史入口需要与操作区其他动作保持图标按钮一致。

- [x] T029 在 `frontend/src/pages/AdminPage.tsx` 将有用户名的上传者链接到 `/users/:username`，并将历史文字按钮改为带 Tooltip/无障碍名称的 `HistoryIcon` 按钮；补充目标 Vitest、Spec 与 Overview 交互契约。

**T029 验证记录（2026-09-04）**：目标 Vitest `12 passed`；前端生产构建通过；`git diff --check` 通过。

## 收敛需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001/FR-002 / US1 | T011-T012 | 真实详情元数据与页面展示 |
| FR-003/FR-004 / US2 | T013-T016 | 管理端时间线与权限 |
| FR-005 至 FR-009 / US3 | T007-T010、T017-T023 | 迁移、回填、上传、审核、修改与去重 |
| FR-010 | T024 | 审核贡献统计过滤 |
| FR-011 | T025 | 物理删除无孤儿历史 |
| FR-012 | T003-T004、T026 | 既有审核成功角色导航回归 |
| SC-001 至 SC-008 | T026-T027 | 全量验证与当前事实回写 |
| 修订 FR-001/FR-002、SC-001 | T028 | 移除无需求的物性记录数量，将上传者与“历史”入口放入论文列表操作区域 |
| 修订 FR-002 | T029 | 上传者跳转公开用户页，历史入口改为仅图标按钮并保留 Tooltip/无障碍名称 |
