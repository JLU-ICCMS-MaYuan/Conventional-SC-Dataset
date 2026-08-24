# 实施任务：管理员资格申请与审批

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/admin-application-api.md](contracts/admin-application-api.md)

## 阶段 1：准备

- [x] T001 在 `alembic/versions/` 新增申请与治理审计表，并同步 Go/Python 模型。

## 阶段 2：基础能力

- [x] T002 为单一 pending、状态转换和审批事务编写 Go 事务测试，并验证 MySQL 迁移 SQL。

## 阶段 3：用户故事 1——申请管理员（P1，MVP）

- [x] T003 [US1] 实现 `goserver/handlers/admin_applications.go` 的提交和本人历史接口。
- [x] T004 [US1] 在 `AccountPage.tsx` 增加管理员申请条件、快照和状态分区。

## 阶段 4：用户故事 2——撤回与重申（P2）

- [x] T005 [US2] 实现撤回条件更新、再次申请及前端交互测试。

## 阶段 5：用户故事 3——审批与降级（P1）

- [x] T006 [US3] 先编写 user/admin/superadmin 权限、并发审批、拒绝原因和降级审计测试。
- [x] T007 [US3] 实现 `/api/superadmin/admin-applications/**` 和降级接口。
- [x] T008 [US3] 在可独立测试的 `SuperAdminGovernance.tsx` 中接入管理员申请审批面板。

## 最终阶段：完善与跨故事事项

- [x] T009 完成迁移、前端构建、端到端 quickstart 和角色 Overview 更新。

## 依赖与执行顺序

- #39、#40、#38 阻断本 Feature；T001/T002 阻断全部故事。
- US1 可独立交付，US3 UI 最终由 #44 集成。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001、FR-002、FR-003、FR-004、FR-007 | T002-T005 |
| FR-005、FR-006、FR-008、FR-009 | T001-T002、T006-T008 |
| SC-001、SC-002、SC-003、SC-004 | T002、T006、T009 |

## MVP 与增量策略

先提供资料完整用户的申请与历史，再加入撤回，最后接入超级管理员审批和降级。
