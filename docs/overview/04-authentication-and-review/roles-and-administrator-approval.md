# 角色与管理员审批

## 功能说明

管理 `user`、`admin` 和 `superadmin` 三类角色，以及管理员申请的批准状态和角色调整。

## 当前行为

- Go 登录接口只允许 `is_approved=true` 的用户登录。
- Go 管理员中间件将 `admin` 和 `superadmin` 视为管理员；管理路由要求登录且具备管理员角色。
- 超级管理员状态主要由前端 `isSuper` 控制用户管理页可见性；后端用户更新接口挂在管理员路由组下。
- 用户记录保存 `role`、`is_approved`、`is_email_verified`、`approved_at` 等字段。

## 工作流程

用户注册时可以申请管理员角色；账户进入未审批状态；管理员或超级管理员在后台调整角色与审批状态；用户获批后可登录；后续请求由 Go 中间件和前端角色判断共同限制可访问页面与端点。

## 约束

- 角色值限制为 `user`、`admin`、`superadmin`。
- 用户管理页面只对前端识别出的 superadmin 展示，但后端 `PUT /api/admin/users/:id/permissions` 当前位于管理员路由组，细粒度 superadmin 限制需继续核验。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/middleware/auth.go`
- `goserver/models/models.go`
- `backend/security.py`
- `backend/models.py`
- `frontend/src/pages/AdminPage.tsx`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 角色兼容字段的最终移除计划不属于当前事实。
