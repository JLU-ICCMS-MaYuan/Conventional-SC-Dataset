# 快速验收：邮箱验证注册

## 前置条件

- 空白测试邮箱、可用 Redis、测试 SMTP 或显式 fake sender。
- 应用通过 Docker Compose 启动。

## 路径

1. 注册合法用户名、邮箱和至少 10 位密码，确认页面进入验证码步骤且不存在管理员选项。
2. 检查邮件收到 6 位码，60 秒内重发被限制。
3. 提交错误码 5 次，确认旧码失效；重发后提交新码。
4. 确认验证成功自动进入 `/account`，刷新仍保持登录。
5. 使用已消费验证码重放，确认失败。
6. 检查数据库和生产日志不存在验证码明文。

## 验证命令

```bash
cd goserver && go test ./...
python3 -m pytest tests/02_maintenance_and_verification -q
cd frontend && npm run build
docker compose -f docker/compose.yaml config
```
