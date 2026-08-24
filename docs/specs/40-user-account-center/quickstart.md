# 快速验收：用户中心与账户安全

1. 分别以 user/admin/superadmin 登录，确认左侧名称和工作入口正确。
2. 打开头像菜单，确认仅有退出登录。
3. 保存姓名、机构、合法 ORCID 和 10 个以内研究方向；刷新后保持。
4. 尝试错误校验位、重复 ORCID、第 11 个标签和超长标签，确认字段级错误。
5. 上传 JPEG/PNG/WebP，确认裁剪后显示；上传伪装格式或超过 2 MiB 文件必须失败；删除恢复首字符。
6. 修改姓名和机构，使用超级管理员 API 验证审计；普通用户读取审计应为 403。
7. 修改密码后确认自动退出，旧 Token 失败，新密码可登录。

```bash
cd goserver && go test ./...
cd frontend && npx vitest run --config ../vitest.config.ts && npm run build
python3 -m pytest tests/02_maintenance_and_verification -q
docker compose -f docker/compose.yaml config
```
