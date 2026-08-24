# 邮箱验证认证 API

## `POST /api/auth/register`

输入：`email`、`username`、`password`、可选 `real_name`。不接受角色或管理员申请字段。

成功：`202`，返回 `requires_email_verification=true`、规范化后的掩码邮箱和 `resend_after_seconds=60`。

错误：`400` 校验失败，`409` 邮箱/用户名冲突，`429` 超额，`503` 邮件或限流服务不可用。

## `POST /api/auth/verify-email`

输入：`email`、`code`。

成功：`200`，返回 `access_token`、`token_type='bearer'`、`user`；验证码原子消费。

错误：`400` 统一表示无效、过期或已消费；`429` 表示尝试次数或额度达到上限。

## `POST /api/auth/resend-verification`

输入：`email`。

成功：`202`，无论邮箱是否存在都使用不泄漏账号状态的响应文案。

错误：`429` 带 `Retry-After`；`503` 表示邮件或限流服务不可用。

## `POST /api/auth/login`

保持邮箱和密码登录。未验证邮箱返回 `403`、稳定错误码 `email_not_verified`，不得复用管理员资格或账号封禁文案。
