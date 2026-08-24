# 快速验收：公开科研身份页

1. 未登录打开有完整资料的 `/users/:username`，确认六类公开字段可见且邮箱不可见。
2. 查看普通用户、管理员、超级管理员，确认只有后两者显示角色。
3. 清空姓名和机构，确认对应区域消失。
4. 从贡献榜、审核记录和本人用户中心各进入一次。
5. 检查页面存在 robots noindex，离开页面后其他页面不受影响。
6. 修改用户名，确认旧地址 404、新地址可用。
7. 封禁后确认主页保留并标注；注销后确认资料移除且历史贡献匿名化。

```bash
cd goserver && go test ./...
cd frontend && npx vitest run --config ../vitest.config.ts && npm run build
```
