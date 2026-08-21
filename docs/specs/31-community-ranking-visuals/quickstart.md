# 快速验收：唯一公开用户名与贡献榜身份

## 自动化验证

```bash
python -m pytest -q \
  tests/07_researcher_community_forum \
  tests/test_username_policy.py \
  tests/test_import_export.py

cd goserver
go test ./...

cd ../frontend
npm run build
```

## 数据迁移验证

1. 在测试库准备至少两个没有 `username` 的历史用户。
2. 执行 `alembic upgrade head`。
3. 确认每个历史账号用户名匹配 `^sc_[a-z0-9]{12}$`、互不相同且 `username_change_allowed=true`。
4. 确认 `username` 唯一索引允许 `Alice` 与 `alice`，拒绝第二个完全相同的 `Alice`。

## 浏览器验收

1. 注册页输入非法、保留、`sc_` 前缀和已占用名称，确认失焦检查显示原因。
2. 使用合法用户名和邮箱注册，确认账号响应与菜单不显示实名。
3. 使用历史账号登录，确认头像菜单出现一次“设置用户名”；冲突失败后仍可重试，成功后入口消失。
4. 使用超级管理员在用户管理中带原因更名，确认审计列表新增一条完整记录。
5. 打开社区贡献榜，确认上传榜和审核榜只显示用户名，更名后刷新立即生效。
6. 确认双榜贡献条存在，桌面个人排名同行，窄屏换行无溢出。
7. 对同一论文用两个不同请求键重复提交相同状态和意见，确认审核榜累计两次；用相同请求键重试时确认只累计一次。

## 预期结果

- 登录始终使用邮箱。
- 客户端不显示或接收实名。
- 所有更名规则、审计和缓存行为符合 [API 契约](contracts/username-api.md)。
- Issue #29 的排名与刷新测试无回归。
- 390px 宽度下页面没有横向滚动，两个榜单纵向排列且贡献次数完整可见。
