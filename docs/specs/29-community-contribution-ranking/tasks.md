# 实施任务：社区贡献排行榜

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：建立可追踪的数据结构与跨语言模型。

- [x] T001 新增审核事件及旧数据回填迁移 `alembic/versions/20260820_0004_add_paper_review_events.py`
- [x] T002 [P] 同步 SQLAlchemy 审核事件模型 `backend/models.py`
- [x] T003 [P] 同步 GORM 审核事件模型 `goserver/models/models.go`

## 阶段 2：基础能力

**目的**：先建立测试、可选认证和共享聚合基础，阻断全部用户故事。

- [x] T004 在 `goserver/handlers/stats_test.go` 增加统计口径、稳定排序、Top 20、个人排名和隐私测试，并在 `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py` 增加前端页面契约测试
- [x] T005 [P] 在 `goserver/middleware/auth.go` 实现公开端点所需的可选认证并补充 `goserver/middleware/auth_test.go`
- [x] T006 在 `goserver/handlers/admin.go` 与 `goserver/handlers/stats.go` 提取并复用事务化审核事件写入逻辑

## 阶段 3：用户故事 1——查看社区贡献榜（P1，MVP）

**目标**：匿名访问者可以看到准确参与人数和两个公开 Top 20。

**独立验收**：使用 25 名以上贡献者数据核对人数、口径、榜单长度、同分顺序和公开字段。

### 测试

- [x] T007 [US1] 运行并修正 `goserver/handlers/stats_test.go` 的失败测试，确认实现前可复现缺口

### 实施

- [x] T008 [US1] 在 `goserver/handlers/stats.go` 实现常数次 SQL 聚合、稳定排名、参与人数和最小公开 DTO
- [x] T009 [US1] 在 `goserver/main.go` 注册 `GET /api/community/contributions` 公共路由
- [x] T010 [US1] 在 `frontend/src/pages/share.tsx` 增加贡献概览和双 Top 20 的响应类型、加载与展示，并通过 `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py` 验证页面契约

## 阶段 4：用户故事 2——查看我的全量排名（P2）

**目标**：登录用户在 Top 20 内外均看到本人两项准确排名，匿名用户看不到个人数据。

**独立验收**：分别以 Top 20 内、Top 20 外、零贡献和匿名身份核对响应与界面。

### 测试

- [x] T011 [US2] 在 `goserver/handlers/stats_test.go` 与 `goserver/middleware/auth_test.go` 完成登录、匿名、零贡献和 Top 20 外排名测试

### 实施

- [x] T012 [US2] 在 `goserver/handlers/stats.go` 依据可选认证附加本人全量排名
- [x] T013 [US2] 在 `frontend/src/pages/share.tsx` 增加“我的排名”及未登录、零贡献状态，并扩展 `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py`

## 阶段 5：用户故事 3——获取最新榜单（P3）

**目标**：榜单每小时被动刷新，并支持用户立即刷新和失败恢复。

**独立验收**：新增贡献后分别验证缓存命中、手动绕过、一小时自动获取和失败保留旧数据。

### 测试

- [x] T014 [US3] 在 `goserver/handlers/stats_test.go` 完成一小时缓存、强制刷新和并发重建行为测试

### 实施

- [x] T015 [US3] 在 `goserver/handlers/stats.go` 实现一小时 Redis 缓存、`refresh=true` 绕过和生成时间
- [x] T016 [US3] 在 `frontend/src/pages/share.tsx` 实现每小时定时器、刷新按钮、最后更新时间及失败保留，并扩展 `tests/07_researcher_community_forum/test_issue29_contribution_ranking.py`

## 阶段 6：审核历史集成

**目标**：所有有效审核准确记账且重试不重复计数。

- [x] T017 在 `goserver/handlers/admin_review_event_test.go` 增加审核事件写入、无变化和请求重试的数据库交互测试，并由批量审核复用同一写入函数
- [x] T018 在 `goserver/handlers/admin.go` 实现单篇审核事务、`review_request_id` 幂等与事件写入
- [x] T019 在 `goserver/handlers/stats.go` 实现批量审核逐论文事件、派生幂等键和事务写入
- [x] T020 在 `frontend/src/pages/AdminPage.tsx` 为单篇和批量审核生成并发送稳定的 `review_request_id`

## 最终阶段：完善与跨故事事项

- [x] T021 运行 `go test ./...`、TypeScript 检查、Vite 生产构建和受影响 Python 测试，并完成可在当前环境执行的 `quickstart.md` 回归验证
- [x] T022 使用 `big-project-overview-maintainer` 更新 `docs/overview/05-visualization-and-metrics/researcher-contribution-ranking.md` 及目录说明
- [x] T023 对照 FR、SC、验收场景和当前代码执行 converge，并记录未完成差距

## 阶段 8：收敛任务

- [x] T024 [差距：partial，来源：FR-005–FR-006、SC-003] 使用 `sqlmock` 与 `miniredis` 补充审核事件写入、幂等、缓存 TTL、强制刷新和并发重建测试，涉及 `goserver/handlers/admin_review_event_test.go` 与 `goserver/handlers/stats_test.go`
- [ ] T025 [差距：partial，来源：SC-004–SC-005] 在部署环境执行 `alembic upgrade head` 并完成 `docs/specs/29-community-contribution-ranking/quickstart.md` 的浏览器端到端验收

## 依赖与执行顺序

- T001–T003 可在不同文件上并行，但迁移字段与模型命名必须一致。
- T004–T006 阻断全部用户故事；先观察失败测试，再实现基础能力。
- US1 是 MVP，US2 复用 US1 的全量排序结果，US3 复用其快照生成逻辑。
- T017–T020 必须在最终榜单验收前完成，否则审核榜没有可靠事实来源。
- 同一文件上的任务保持串行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001–FR-004、SC-001 / US1 | T004、T007–T010 | 统计口径、稳定排序、Top 20 和页面展示 |
| FR-005–FR-006、FR-014、SC-003 | T001–T006、T017–T020 | 审核历史、回填、事务与幂等 |
| FR-007、SC-002 / US1 | T004、T008、T021 | 最小 DTO 与敏感字段测试 |
| FR-008–FR-009 / US2 | T005、T011–T013 | 可选认证与本人全量排名 |
| FR-010–FR-013、SC-004 / US3 | T014–T016 | 缓存、刷新、时间和失败保留 |
| SC-005 | T021–T023 | 自动验证、文档回写与最终收敛 |

## MVP 与增量策略

1. 完成审核事件和基础聚合能力。
2. 实施并独立验收 US1 的公开双榜单。
3. 增加 US2 本人排名，再增加 US3 刷新体验。
4. 完成审核写入集成、全量回归和 Overview 收敛。
