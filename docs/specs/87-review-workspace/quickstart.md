# 快速验证：审核编辑页元数据与成功返回工作台

**GitHub Issue**：[#87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)

**日期**：2026-09-03

## 自动化验证

```bash
cd frontend && npx vitest run --config ../vitest.config.ts ../tests/02_identity_governance/admin-edit-page.test.tsx
cd frontend && npm run build
```

预期：目标 Vitest 用例和 TypeScript/Vite 生产构建均通过。

## 手工验证

1. 以超级管理员登录，进入论文审核并打开任意论文编辑页。
   预期：元数据区显示“上传者”和“记录”。
2. 选择“通过”并提交审核。
   预期：接口成功后立即返回 `/superadmin`。
3. 以管理员重复提交。
   预期：接口成功后立即返回 `/admin`。
4. 模拟审核接口失败。
   预期：留在编辑页，并显示“审核失败”。
