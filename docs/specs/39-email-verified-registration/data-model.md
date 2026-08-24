# 数据模型：邮箱验证注册

## 用户扩展

- `is_email_verified BOOLEAN NOT NULL DEFAULT 0`：继续作为邮箱最终验证事实。
- `session_version BIGINT NOT NULL DEFAULT 0`：JWT 会话版本，供本 Feature 签发并由账户安全与治理复用。
- `account_status VARCHAR(20) NOT NULL DEFAULT 'active'`：`active/banned/deactivated`，本 Feature 仅建立字段和认证校验。
- 旧 `verification_code`、`verification_expires` 不再作为生产验证码存储；迁移完成后移除或保持未使用并在后续安全迁移删除。

## Redis 邮箱验证挑战

- Key：规范化邮箱的不可逆派生标识。
- 值：验证码 HMAC/摘要、失败次数、创建时间。
- TTL：300 秒。
- 验证成功：原子比较并删除；失败：原子增加次数，第 5 次后删除。

## Redis 发送额度

- 邮箱与 IP 分别建立小时和日计数器。
- 首次增加时原子设置到期时间。
- 超额请求返回 `429` 和 `Retry-After`。

## 历史数据迁移

- 已能正常使用的历史账号回填 `is_email_verified=1`、`account_status='active'`。
- 不改变 `user/admin/superadmin` 角色。
- 新注册账号固定 `role='user'`，验证后成为可登录账号。
