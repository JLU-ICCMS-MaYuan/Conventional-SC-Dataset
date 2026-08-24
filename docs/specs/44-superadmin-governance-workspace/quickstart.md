# 快速验收：超级管理员工作台

1. user 和 admin 访问 `/superadmin`，确认 403 且未请求专属数据。
2. superadmin 进入页面，确认复用审核模块并可访问图表、快讯、申请、用户和审计。
3. 管理员直接调用图表/快讯写接口，确认 403；公开读取保持成功。
4. 带原因封禁普通用户，确认旧 Token 失效、登录和写操作失败、公开页标注封禁。
5. 解封后使用旧 Token 仍失败，新登录成功。
6. 注销用户，确认资料和头像移除，历史论文/贡献/审核/审计计数不减少。
7. 尝试操作自己和最后一名 active superadmin，确认失败且无审计半记录。
8. 检查三类审计分页与角色权限。

```bash
cd goserver && go test ./...
python3 -m pytest tests/02_maintenance_and_verification -q
cd frontend && npx vitest run --config ../vitest.config.ts && npm run build
docker compose -f docker/compose.yaml config
```
