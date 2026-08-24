# 实施任务：公开科研身份页

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[contracts/public-profile-api.md](contracts/public-profile-api.md)

## 阶段 1：准备

- [x] T001 定义 `goserver/handlers/public_profile.go` 的显式公开 DTO 和状态映射测试。

## 阶段 2：基础能力

- [x] T002 实现匿名公开资料与头像读取接口，并在 `goserver/main.go` 注册。

## 阶段 3：用户故事 1——查看公开资料（P1，MVP）

- [x] T003 [US1] 先编写字段白名单、角色标识、空字段、封禁和注销测试。
- [x] T004 [US1] 新增 `frontend/src/pages/PublicUserPage.tsx` 并在 `LazyRoutes.tsx` 注册路由和 noindex 生命周期。

## 阶段 4：用户故事 2——从科研活动进入（P2）

- [x] T005 [US2] 在 `frontend/src/pages/share.tsx`、共享审核记录和用户中心增加用户名链接。
- [x] T006 [US2] 增加入口与 #31 排行榜 DTO 回归测试。

## 阶段 5：用户故事 3——治理状态（P2）

- [x] T007 [US3] 接入封禁标识和注销匿名化，并验证贡献外键不被破坏。

## 最终阶段：完善与跨故事事项

- [x] T008 完成匿名访问、响应式、键盘、构建和 Overview 验收。

## 依赖与执行顺序

- #40 阻断 T001-T004；#44 提供完整封禁/注销行为后完成 T007。
- T005 可在公开页稳定后实施。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001、FR-002、FR-003、FR-004、FR-005、FR-006、FR-008 | T001-T004 |
| FR-007、FR-010 | T005-T006 |
| FR-009 | T003、T007 |
| SC-001、SC-002、SC-003、SC-004 | T003、T006-T008 |

## MVP 与增量策略

先交付匿名白名单页面，再接入口和治理状态；任何阶段都不扩张排行榜响应。
