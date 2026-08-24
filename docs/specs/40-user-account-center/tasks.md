# 实施任务：用户中心与账户安全

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/account-api.md](contracts/account-api.md)

## 阶段 1：准备

- [x] T001 在 `alembic/versions/` 增加资料字段和资料审计表，并同步 Go/Python 模型。
- [x] T002 在 `docker/compose*.yaml` 增加头像持久卷与 Go 配置。

## 阶段 2：基础能力

- [x] T003 [P] 新增 ORCID、研究方向和资料 DTO 校验器及单元测试。
- [x] T004 [P] 在账户处理器中集中实现头像格式、大小、裁剪、替换能力及测试。
- [x] T005 实现 `GET /api/auth/me` 并让 AuthContext 启动时刷新服务端用户。

## 阶段 3：用户故事 1——维护科研身份资料（P1）

- [x] T006 [US1] 先编写本人资料、ORCID 并发冲突、审计事务和头像失败测试。
- [x] T007 [US1] 实现 `goserver/handlers/account.go` 的资料与头像接口。
- [x] T008 [US1] 新增 `frontend/src/pages/AccountPage.tsx` 和资料分区组件。
- [x] T009 [US1] 将 #31 用户名编辑迁入用户中心，并收敛 `AppShell.tsx` 菜单。

## 阶段 4：用户故事 2——安全修改密码（P1）

- [x] T010 [US2] 编写当前密码错误、成功递增版本、旧 JWT 失效测试。
- [x] T011 [US2] 实现改密接口与账户安全 UI，成功后退出登录。

## 阶段 5：用户故事 3——进入角色工作台（P2）

- [x] T012 [US3] 实现三角色动态导航和工作入口，并增加路由行为测试。

## 最终阶段：完善与跨故事事项

- [x] T013 扩展 Vitest 账户测试并完成响应式、键盘与构建验收。
- [x] T014 更新认证、数据模型和部署 Overview。

## 依赖与执行顺序

- #39 的身份基础阻断 T005/T010；T003、T004 可并行。
- 资料模型完成后 #41 和 #42 才可实施。

## 需求覆盖

| 来源 | 任务 |
|---|---|
| FR-001、FR-002、FR-003、FR-004、FR-005、FR-011、FR-012 | T005、T008-T009、T012-T013 |
| FR-006、FR-007、FR-008、FR-009 | T001-T004、T006-T008 |
| FR-010 | T010-T011 |
| SC-001、SC-002、SC-003、SC-004 | T006、T010、T013-T014 |

## MVP 与增量策略

先交付可保存的文字资料和安全改密，再加入头像与角色工作入口，始终保持现有用户名能力可用。
