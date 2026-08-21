# 注册、登录与 JWT

## 功能说明

通过邮箱、密码和唯一公开用户名创建用户，验证邮箱凭据后签发 JWT，并为受保护 API 提供当前用户身份。

## 当前行为

- Go API `POST /api/auth/register` 要求邮箱、密码和全站唯一的 `username`，实名可以省略；使用 bcrypt 保存密码哈希，新用户默认 `is_approved=false` 且不能自行修改用户名。
- 用户主动选择的 `username` 为 3–32 位，以字母开头且只含字母、数字和下划线；保留名称及 `sc_` 前缀不区分大小写禁止使用，普通用户名唯一性区分大小写。
- 匿名接口 `GET /api/auth/username-availability` 提供失焦可用性提示，注册最终写入仍由数据库唯一索引处理并发冲突。
- Go API `POST /api/auth/login` 只接受邮箱和密码，校验审批状态后返回 JWT、用户名、角色和一次更名资格，不返回实名。
- 历史账号迁移后获得 `sc_` 加 12 位安全随机字符的临时用户名，可通过 `PATCH /api/auth/username` 成功自行更名一次；失败不消耗资格。
- 前端 `AuthContext` 将 token 和不含实名的用户信息保存到 `localStorage`；自助更名或超级管理员给自己更名后立即替换本地用户对象，通用 API 客户端自动附加 `Authorization: Bearer`。
- Go 中间件保护 `/api` 登录路由组和 `/api/admin` 管理员路由组；Python 结构接口也通过安全模块解析当前用户或管理员。

## 工作流程

用户提交邮箱、密码、用户名和可选实名；服务校验用户名并创建待审批用户；用户获批后只使用邮箱和密码登录；前端保存 JWT 与公开用户名；后续上传记录、管理后台、图表组合等请求携带 token；Go 或 Python 认证逻辑按接口所在服务执行权限检查。

## 约束

- JWT 使用 HS256，Go 服务要求 `JWT_SECRET_KEY` 存在。
- 未审批用户不能登录 Go API。
- `users.username` 使用 `ascii_bin` 唯一索引，允许 `Alice` 与 `alice` 共存并拒绝完全相同的重复值。
- 实名继续保存在服务端并可在注册时采集，但账号客户端响应和身份界面不展示该字段。
- 前端仍保留邮箱验证码步骤并调用 `/api/auth/verify-email`；当前 Go 主路由未注册该端点，Python `auth_routes` 也未在 `backend/main.py` 中 include，邮箱验证闭环需继续核验。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/handlers/username.go`
- `goserver/middleware/auth.go`
- `goserver/handlers/username_test.go`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/components/AuthDialog.tsx`
- `frontend/src/components/UsernameField.tsx`
- `backend/api/auth_routes.py`（存在但当前 Python 主应用未 include）
- `backend/username_policy.py`
- `backend/security.py`
- `backend/email_service.py`
- `alembic/versions/20260821_0006_add_public_usernames.py`
- `tests/test_username_policy.py`
- `tests/07_researcher_community_forum/test_issue31_public_username.py`

## 相关变更记录

- [Feature #31：唯一公开用户名与贡献榜身份](../../specs/31-community-ranking-visuals/spec.md)
- [GitHub Issue #31](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/31)

## 已知问题

- 邮箱验证前端流程与当前后端注册路由不完全一致。
