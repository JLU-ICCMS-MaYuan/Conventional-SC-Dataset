# 管理后台使用手册

本手册覆盖管理员/超级管理员的创建、登录、审核流程、安全配置以及常见问题，路径示例已使用占位信息（域名
om、邮箱 user@example.com）。

---

## 1. 账号与权限

| 角色 | 权限 |
|------|------|
| 匿名 | 浏览 |
| 普通用户 | 浏览/上传文献（未审核） |
| 管理员 | 审核/反审核文献，查看个人审核记录 |
| 超级管理员 | 具备管理员权限；审批管理员申请；查看管理员列表 |

---

## 2. 创建超级管理员

```bash
python -m backend.create_superadmin
```

按提示输入邮箱、姓名、密码。也可使用环境变量：
```bash
export SUPERADMIN_EMAIL="user@example.com"
export SUPERADMIN_PASSWORD="your_secure_password"
export SUPERADMIN_NAME="管理员姓名"
python -m backend.create_superadmin
```

---

## 3. 登录与注册入口

- 管理员登录页：`https://example.com/admin/login`
- 管理员注册页：`https://example.com/admin/register`（提交后等待超级管理员审批）
- 超级管理员面板：登录后访问 `/admin/superadmin`
- 管理员审核面板：`/admin/dashboard`
- 我的审核记录：`/admin/my-reviews`

---

## 4. 审批流程

### 管理员注册
1) 访问 `/admin/register`，填写邮箱、姓名、密码。
2) 收取邮件验证码（未配置 SMTP 时会打印到控制台）。
3) 提交后等待超级管理员审批。

### 超级管理员审批
1) 登录 `/admin/login`，进入 `/admin/superadmin`。
2) 在“待审批管理员”列表中批准/拒绝。
3) 系统会向申请人发送结果邮件（若 SMTP 已配置）。

---

## 5. 文献审核流程

1) 管理员登录 `/admin/dashboard` 查看待审核文献。
2) 可按关键词/年份/状态筛选。
3) 打开文献卡片，点击“标记为已审核”或“取消审核”。
4) 系统记录审核人与时间，前端显示审核状态徽章。

---

```bash
export SMTP_SERVER="smtp.example.com"
export SMTP_PORT="587"              # 或 465
export SMTP_USERNAME="user@example.com"

---

## 7. JWT 安全配置

生产环境必须设置足够随机的密钥：
```bash
export JWT_SECRET_KEY="a_very_long_random_string_at_least_32_chars"
```

---

## 8. 常见问题

**Q: 忘记超级管理员密码？**
运行 `python -m backend.create_superadmin` 重新设置同邮箱，会保持超级管理员身份。

**Q: 邮件收不到？**
- 检查 SMTP 配置/授权码；
- 查看后端日志；
- 开发模式下验证码会打印在控制台。

**Q: 无法登录后台？**
确认账号是否已被超级管理员批准；检查 JWT 配置与服务器时间同步。

**Q: 如何重置数据库？**
删除 `data/superconductor.db`，运行 `python -m backend.init_db`，然后重新创建超级管理员。

---

## 9. 安全建议

- 使用 HTTPS（示例域名 `example.com` 仅为占位）
- 不要在代码中硬编码密码/授权码，使用环境变量或密钥服务
- 定期审查管理员列表（`/admin/superadmin`）
- 结合自动备份，确保出现误操作时可快速回滚