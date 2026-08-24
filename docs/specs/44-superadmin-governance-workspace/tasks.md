# 实施任务：超级管理员工作台与账号治理

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/superadmin-api.md](contracts/superadmin-api.md)

## 阶段 1：准备

- [x] T001 完成 `account_status/session_version` 与治理审计模型的迁移回归及 Go/Python 同步。

## 阶段 2：基础能力

- [x] T002 为 user/admin/superadmin 路由、图表/快讯写权限和 active 状态编写失败测试。
- [x] T003 在 `goserver/main.go` 建立 superadmin 路由组并迁移高权限接口。

## 阶段 3：用户故事 1——统一高权限工作台（P1）

- [x] T004 [US1] 新增薄 `SuperAdminPage.tsx`，复用 `AdminPage.tsx` 的概览和审核逻辑并组合图表、快讯能力。
- [x] T005 [US1] 接入管理员申请、用户治理和审计懒加载面板。

## 阶段 4：用户故事 2——安全治理账号（P1，MVP）

- [x] T006 [US2] 先编写封禁、解封、注销、自操作、最后超管、会话失效和事务审计测试。
- [x] T007 [US2] 在 `goserver/handlers/governance.go` 实现明确的用户治理动作端点。
- [x] T008 [US2] 在治理面板统一实现后果说明、原因输入和二次确认流程。

## 阶段 5：用户故事 3——查看不可变审计（P2）

- [x] T009 [US3] 实现资料、用户名和治理审计分页 API 与只读面板。

## 最终阶段：完善与跨故事事项

- [x] T010 完成 Go 事务测试、MySQL 离线迁移 SQL、Vitest、构建、Compose、quickstart 和 Overview 验收。

## 依赖与执行顺序

- #38、#40、#42、#43 阻断本 Feature；T001-T003 阻断全部故事。
- T004 只在共享审核模块稳定后实施；T006/T007 阻断治理 UI。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001、FR-002、FR-003、FR-004、FR-011、FR-012 | T002-T005、T009 |
| FR-005、FR-006、FR-007、FR-008、FR-009、FR-010 | T001、T006-T008 |
| SC-001、SC-002、SC-003、SC-004、SC-005 | T002、T006、T009-T010 |

## MVP 与增量策略

先建立后端安全边界和可审计治理，再组合工作台面板；任何 UI 上线前直接 API 越权测试必须通过。
