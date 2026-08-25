# 注册、登录与 JWT

## 功能说明

通过邮箱、密码和唯一公开用户名创建用户，注册后直接登录并签发 JWT，为受保护 API 提供当前用户身份。

## 当前行为

- Go API `POST /api/auth/register` 要求邮箱、至少 10 位密码和全站唯一的 `username`，实名可以省略；注册固定创建 `user`，不再接受管理员角色申请，兼容字段 `is_approved` 直接为 true。
- 用户主动选择的 `username` 为 3–32 位，以字母开头且只含字母、数字和下划线；保留名称及 `sc_` 前缀不区分大小写禁止使用，普通用户名唯一性区分大小写。
- 匿名接口 `GET /api/auth/username-availability` 提供失焦可用性提示，注册最终写入仍由数据库唯一索引处理并发冲突。
- 邮箱验证当前停用。注册直接写入 `is_email_verified=true`，不调用 SMTP；响应声明无需验证，前端随即使用注册邮箱和密码登录并进入用户中心。
- `POST /api/auth/verify-email` 与 `POST /api/auth/resend-verification` 暂时保留兼容，但正常注册流程不会调用。
- Go API `POST /api/auth/login` 只接受邮箱和密码，要求 `account_status=active`，返回 JWT、用户名、角色和一次更名资格，不返回实名。
- 用户写入失败时，只有 MySQL `1062` 唯一键冲突返回“邮箱或用户名已被占用”；其他数据库错误返回“注册失败”并记录服务端错误。
- 历史账号迁移后获得 `sc_` 加 12 位安全随机字符的临时用户名，可通过 `PATCH /api/auth/username` 成功自行更名一次；失败不消耗资格。
- 前端 `AuthContext` 将 token 和不含实名的用户信息保存到 `localStorage`，启动时通过 `GET /api/auth/me` 刷新服务端身份；通用 API 客户端自动附加 `Authorization: Bearer`。
- JWT 包含 `session_version`。Go 和 Python 权限解析都会校验数据库中的账号状态与会话版本；改密、封禁、注销或角色变化会递增版本，使旧 JWT 立即失效。

## 工作流程

用户提交邮箱、密码、用户名和可选实名；服务直接创建已启用的普通账号，前端随后自动登录、保存 JWT 并进入用户中心。后续上传、用户中心和工作台请求携带 token；中间件同时验证签名、会话版本、账号状态和角色。

## 约束

- JWT 使用 HS256，Go 服务要求 `JWT_SECRET_KEY` 存在。
- 邮箱验证停用期间，登录不检查 `is_email_verified`；账号封禁或注销后仍不能登录或继续使用旧 Token。
- `users.username` 使用 `ascii_bin` 唯一索引，允许 `Alice` 与 `alice` 共存并拒绝完全相同的重复值。
- 邮箱不进入公开资料 DTO；真实姓名由用户选择填写，填写后会在公开研究身份页展示。
- 当前注册不依赖 SMTP 或 Redis；重新启用邮箱验证前需要恢复注册、登录和前端验证码流程的一致行为，并验收 SMTP 可达性。

## 代码与测试

- `goserver/handlers/auth.go`
- `goserver/handlers/username.go`
- `goserver/middleware/auth.go`
- `goserver/handlers/username_test.go`
- `frontend/src/context/AuthContext.tsx`
- `frontend/src/components/AuthDialog.tsx`
- `frontend/src/components/UsernameField.tsx`
- `backend/username_policy.py`
- `backend/security.py`
- `alembic/versions/20260824_0009_add_account_identity_governance.py`
- `alembic/versions/20260821_0006_add_public_usernames.py`
- `tests/test_username_policy.py`
- `tests/07_researcher_community_forum/test_issue31_public_username.py`

## 相关变更记录

- [Feature #31：唯一公开用户名与贡献榜身份](../../specs/31-community-ranking-visuals/spec.md)
- [GitHub Issue #31](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/31)

## 已知问题

- 当前未提供忘记密码或邮箱变更流程。
- 邮箱所有权未经验证，任何能接收系统页面的人都可以用尚未占用的邮箱字符串创建账户；在开放公网注册前应重新启用邮箱验证。
