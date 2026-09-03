# 实施计划：审核编辑页元数据与成功返回工作台

**GitHub Issue**：[#87](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/87)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

仅修改 `AdminPaperEditPage` 的元数据渲染与审核成功分支，并在现有页面集成测试中覆盖角色路由。后端详情模型已经携带所需数据，不新增接口、状态或数据迁移。

## 技术上下文

- **语言与版本**：TypeScript、React、Vite。
- **主要依赖**：React Router、Material UI、Vitest、Testing Library。
- **数据存储**：不适用；只消费现有 `GET /api/admin/papers/:id` 响应。
- **测试体系**：Vitest，测试位于 `tests/02_identity_governance/`。
- **目标平台**：浏览器单页应用。
- **性能目标**：不增加网络请求。
- **约束**：保留既有审核失败提示；不修改工作树中已存在的无关改动。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| Spec FR-001/FR-002 | 展示上传者与记录数 | 使用详情对象已有字段与已有 i18n 键 | 通过 |
| Spec FR-003/FR-004 | 成功返回、失败停留 | 仅在 `api.post` 成功后调用已有 `workspacePath` | 通过 |
| AGENTS.md | 简体中文文档、独立提交 | 文档与代码最小改动，验证后只暂存本 Feature 文件 | 通过 |

## 源代码结构

```text
frontend/src/pages/AdminPaperEditPage.tsx
tests/02_identity_governance/admin-edit-page.test.tsx
docs/overview/02_Decentralized_Maintenance_and_Verification/literature-and-record-review.md
```

**结构选择**：在页面组件中直接消费详情字段，不建立新的映射层；`workspacePath` 已封装角色分支，导航复用该值，避免重复判断角色。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001/FR-002 | `AdminPaperEditPage` 元数据 Chip | 页面集成测试 |
| FR-003/FR-004 | `handleEditReview` 成功/异常分支 | 页面集成测试 |
| FR-005 | 既有 `admin.thUploader`、`admin.recordsChip` | 中文测试与字典复用检查 |

## 阶段与依赖

1. 先扩展页面集成测试，建立现状失败信号。
2. 修改页面元数据与成功导航。
3. 执行目标测试和前端生产构建。
4. 同步已实现行为到审核功能总览。
