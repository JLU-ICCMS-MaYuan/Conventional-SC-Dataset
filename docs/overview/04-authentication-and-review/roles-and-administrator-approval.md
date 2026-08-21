# 角色与管理员审批

## 功能说明

管理 `user`、`admin` 和 `superadmin` 三类角色，以及管理员申请的批准状态和角色调整。

## 当前行为

- Go 登录接口只允许 `is_approved=true` 的用户登录。
- Go 管理员中间件将 `admin` 和 `superadmin` 视为管理员；管理路由要求登录且具备管理员角色。
- 超级管理员状态由前端 `isSuper` 控制用户管理页可见性；用户名更名和更名审计接口还通过后端 `SuperAdminRequired` 强制限制，普通管理员调用返回 `403`。
- 超级管理员可以为任意账号带原因修改用户名；用户名更新和只追加审计事件在同一事务完成，管理员给自己更名后前端立即同步当前会话身份。
- 用户记录保存 `username`、`role`、`is_approved`、`is_email_verified`、`approved_at` 等字段；实名不是公开身份字段。

## 工作流程

用户注册时可以申请管理员角色；账户进入未审批状态；管理员或超级管理员在后台调整角色与审批状态；用户获批后可登录；后续请求由 Go 中间件和前端角色判断共同限制可访问页面与端点。

## 约束

- 角色值限制为 `user`、`admin`、`superadmin`。
- 用户管理页面只对前端识别出的 superadmin 展示，但后端 `PUT /api/admin/users/:id/permissions` 当前位于管理员路由组，细粒度 superadmin 限制需继续核验。
- 超级管理员更名必须提供 1–500 字符原因；更名不恢复或消耗历史账号的自助更名资格。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/middleware/auth.go`
- `goserver/models/models.go`
- `backend/security.py`
- `backend/models.py`
- `frontend/src/pages/AdminPage.tsx`
- `goserver/handlers/username_test.go`

## 相关变更记录

- [Feature #31：唯一公开用户名与贡献榜身份](../../specs/31-community-ranking-visuals/spec.md)

## 已知问题

- 角色兼容字段的最终移除计划不属于当前事实。
