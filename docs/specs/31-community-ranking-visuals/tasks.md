# 实施任务：唯一公开用户名与贡献榜身份

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/](contracts/)

## 阶段 1：准备

- [x] T001 核对 Issue #31、迁移链、Go/Python认证入口、用户模型和前端身份展示文件
- [x] T002 完成需求澄清、数据模型、接口契约、计划和质量检查表

## 阶段 2：基础能力

- [x] T003 [P] 在 `tests/07_researcher_community_forum/test_issue31_public_username.py` 增加迁移、隐私和前端契约测试
- [x] T004 [P] 在 `goserver/handlers/username_test.go` 增加格式、保留名、大小写和更名事务测试
- [x] T005 [P] 在 `backend/test_username_policy.py` 或现有测试目录增加 Python 策略测试
- [x] T006 在 `alembic/versions/20260821_0006_add_public_usernames.py` 实现字段、随机回填、大小写敏感唯一索引和审计表
- [x] T007 [P] 更新 `backend/models.py` 和 `goserver/models/models.go` 的用户与审计模型

## 阶段 3：用户故事 1——唯一用户名注册（P1）

- [x] T008 [US1] 在 `goserver/handlers/username.go` 实现统一用户名策略和可用性接口
- [x] T009 [US1] 更新 `goserver/handlers/admin.go` 的注册、登录客户端 DTO 和并发冲突处理
- [x] T010 [US1] 更新 `goserver/main.go` 注册公开用户名和登录用户路由
- [x] T011 [US1] 更新 `backend/username_policy.py`、`backend/api/auth_routes.py` 和 `backend/email_service.py` 的备用契约与用户名邮件称呼
- [x] T012 [US1] 更新 `frontend/src/context/AuthContext.tsx`、`frontend/src/lib/username.ts`、`frontend/src/components/UsernameField.tsx` 和 `frontend/src/components/AuthDialog.tsx` 的注册体验

## 阶段 4：用户故事 2——历史账号一次自助更名（P1）

- [x] T013 [US2] 在 `goserver/handlers/username.go` 实现原子自助更名和缓存失效
- [x] T014 [US2] 在 `frontend/src/components/AppShell.tsx` 实现用户名身份展示、非阻断提醒和一次更名对话框

## 阶段 5：用户故事 3——超级管理员审计更名（P1）

- [x] T015 [US3] 在 `goserver/middleware/auth.go`、`goserver/handlers/username.go` 和 `goserver/main.go` 实现超管权限、更名事务与审计查询
- [x] T016 [US3] 在 `frontend/src/pages/AdminPage.tsx` 实现用户名用户表、更名原因对话框和审计列表

## 阶段 6：用户故事 4——贡献榜统一身份（P1）

- [x] T017 [US4] 更新 `goserver/handlers/stats.go` 和 `goserver/handlers/contribution_ranking_test.go` 使用用户名及兼容别名
- [x] T018 [US4] 更新 `frontend/src/pages/share.tsx` 和 Issue #31 UI 测试只展示 `username`

## 阶段 7：用户故事 5——贡献条与个人排名布局（P2）

- [x] T019 [US5] 在 `frontend/src/pages/share.tsx` 实现双榜独立归一化贡献条
- [x] T020 [US5] 在 `frontend/src/pages/share.tsx` 实现桌面同行、窄屏换行的个人排名布局

## 最终阶段：兼容、验证与文档

- [x] T021 [P] 更新 `backend/scripts/create_superadmin.py`、`backend/scripts/import_data.py` 和 `backend/scripts/export_data.py` 兼容非空用户名
- [x] T022 修复受模型约束影响的现有测试夹具并执行 Go、Pytest、TypeScript 和 Vite 构建
- [x] T023 按 `quickstart.md` 验证迁移、注册、自助更名、审计和榜单回归
- [x] T024 使用 Overview 维护流程更新认证、数据模型和贡献排行文档，并同步 Issue #31 Documentation Impact

## 阶段 9：实施收敛补充

- [x] T025 [US1] 在 `backend/models.py` 使用 MySQL 类型变体保留 `ascii_bin` 并让 SQLite 测试建表兼容
- [x] T026 [US4] 在 `goserver/handlers/admin.go` 和 `goserver/handlers/admin_review_event_test.go` 确保同一论文每次实际审核计数且相同请求键保持幂等
- [x] T027 [US5] 在 `frontend/src/components/AppShell.tsx`、`frontend/src/pages/share.tsx` 和 Issue #31 UI 测试消除窄屏横向溢出并让双榜纵向排列
- [x] T028 [US2] 在 `backend/scripts/import_data.py` 和 `tests/test_import_export.py` 保持合法 `sc_` 历史用户名导入导出稳定
- [x] T029 [US3] 在 `frontend/src/context/AuthContext.tsx` 和 `frontend/src/pages/AdminPage.tsx` 同步超级管理员给自己更名后的当前会话身份

## 依赖与执行顺序

- T003–T005 先建立失败测试；T006–T007 阻断全部用户故事。
- US1 建立账号契约后，US2、US3 和 US4 才能实施。
- T013 与 T015 同改 `username.go`，必须串行。
- T017 完成后实施 T018；T019–T020 已落地但需纳入回归。
- T021 可在前端实现后并行，T022–T024 最后串行。

## 需求覆盖

| 来源 | 任务 |
|------|------|
| FR-001–FR-004 / SC-001–SC-002 | T003–T008 |
| FR-005–FR-008 / US1 | T008–T012 |
| FR-009 / US2 / SC-003 | T004、T013–T014 |
| FR-010–FR-011 / US3 / SC-004 | T004、T015–T016 |
| FR-012–FR-014 / US4 / SC-005–SC-006 | T013、T015、T017–T018 |
| FR-015–FR-016 / US5 / SC-007 | T003、T019–T020 |
| FR-017 / SC-008 | T022–T023、T025、T027–T029 |
| FR-018 / SC-009 | T026 |

## MVP 与增量策略

1. 数据迁移和注册先建立唯一用户名。
2. 交付历史自助更名与超管审计纠错。
3. 切换贡献榜和全部身份界面。
4. 完成脚本兼容、全量验证和文档回写。
