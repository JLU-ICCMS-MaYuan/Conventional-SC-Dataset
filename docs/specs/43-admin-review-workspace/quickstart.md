# 快速验收：管理员工作台

1. 普通用户访问 `/admin`，确认 403 和“返回用户中心”。
2. 管理员访问，确认标题正确且只有概览、论文审核。
3. 检查网络请求不存在用户、图表、快讯、申请和审计接口。
4. 完成论文筛选、详情、编辑、批准、拒绝和批量审核。
5. 超级管理员访问 `/admin`，确认自动进入 `/superadmin`。
6. 模拟论文接口 403、500 和空列表，确认三种反馈不同。
7. 在窄屏检查 tabs、表格和编辑表单无页面级横向溢出。

```bash
cd goserver && go test ./...
cd frontend && npx vitest run --config ../vitest.config.ts && npm run build
```
