# 实施任务：邮箱验证注册

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/auth-api.md](contracts/auth-api.md)

## 阶段 1：准备

- [x] T001 在 `alembic/versions/` 新增账号身份基础迁移并同步 `backend/models.py`、`goserver/models/models.go`。
- [x] T002 在 `goserver/config/config.go` 与 `docker/compose.yaml` 增加 SMTP 配置。

## 阶段 2：基础能力

- [x] T003 [P] 为 `goserver/cache/cache.go` 增加验证码单次消费和原子限流能力及测试。
- [x] T004 [P] 新增 `goserver/services/email.go` 的邮件接口、SMTP 实现和安全 fake sender。
- [x] T005 更新 `goserver/middleware/auth.go`，让 JWT 携带并校验会话版本与账号状态。

## 阶段 3：用户故事 1——验证邮箱并开始使用（P1，MVP）

- [x] T006 [US1] 为注册固定 user、发送失败、正确/错误/过期/重复验证和自动登录编写 Go 失败测试。
- [x] T007 [US1] 在 `goserver/handlers/auth.go` 实现注册、验证和登录契约，并在 `goserver/main.go` 注册路由。
- [x] T008 [US1] 更新 `frontend/src/context/AuthContext.tsx` 和 `frontend/src/components/AuthDialog.tsx`，移除注册审批并实现验证后自动登录。

## 阶段 4：用户故事 2——安全重发与纠错（P2）

- [x] T009 [US2] 为冷却、邮箱/IP小时与日额度、账号枚举保护编写测试。
- [x] T010 [US2] 实现重发接口、倒计时和错误反馈。

## 最终阶段：完善与跨故事事项

- [x] T011 扩展 `vitest.config.ts` 并增加注册验证行为测试。
- [x] T012 更新认证与部署 Overview，运行 quickstart 全部验证。

## 依赖与执行顺序

- T001/T002 阻断生产接口；T003、T004 可并行；T005 阻断 token 签发。
- US1 完成后实施 US2；管理员申请依赖本 Feature。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001、FR-002、FR-006、FR-007、FR-008 | T006-T008 |
| FR-003、FR-004、FR-005、FR-009、FR-010 | T003-T005、T009-T010 |
| SC-001、SC-002、SC-003、SC-004 | T006、T009、T011-T012 |

## MVP 与增量策略

先交付不可注入角色且可完成验证的注册闭环，再增加重发体验和完整额度反馈。
