# 注册、登录与 JWT

## 功能说明

通过邮箱和密码创建用户，验证密码后签发 JWT，并为受保护 API 提供当前用户身份。

## 当前行为

- Go API `POST /api/auth/register` 接收邮箱、密码、姓名和是否申请管理员，使用 bcrypt 保存密码哈希，新用户默认 `is_approved=false`。
- Go API `POST /api/auth/login` 校验邮箱、密码和审批状态，成功后返回 JWT 与用户角色信息。
- 前端 `AuthContext` 将 token 和用户信息保存到 `localStorage`，通用 API 客户端自动附加 `Authorization: Bearer`。
- Go 中间件保护 `/api` 登录路由组和 `/api/admin` 管理员路由组；Python 结构接口也通过安全模块解析当前用户或管理员。

## 工作流程

用户提交注册表单；服务创建待审批用户；用户获批后登录；前端保存 JWT；后续上传记录、管理后台、图表组合等请求携带 token；Go 或 Python 认证逻辑按接口所在服务执行权限检查。

## 约束

- JWT 使用 HS256，Go 服务要求 `JWT_SECRET_KEY` 存在。
- 未审批用户不能登录 Go API。
- 前端仍保留邮箱验证码步骤并调用 `/api/auth/verify-email`；当前 Go 主路由未注册该端点，Python `auth_routes` 也未在 `backend/main.py` 中 include，邮箱验证闭环需继续核验。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/middleware/auth.go`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/components/AuthDialog.tsx`
- `backend/api/auth_routes.py`（存在但当前 Python 主应用未 include）
- `backend/security.py`
- `backend/email_service.py`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 邮箱验证前端流程与当前后端注册路由不完全一致。
