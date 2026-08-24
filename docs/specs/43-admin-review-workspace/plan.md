# 实施计划：管理员工作台

**GitHub Issue**：[#43](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/43)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

从 1100 余行的 `AdminPage` 提取 `ReviewWorkspace` 和 `WorkspaceOverview`，让 AdminPage 只组合这两个模块。新增 RoleRoute 与 ForbiddenPage，把权限错误和空数据分开处理。

## 技术上下文

- **语言与版本**：React 19、TypeScript 5、Go 1.25。
- **主要依赖**：MUI、React Router、Vitest、Gin。
- **数据存储**：不新增；复用论文与审核事件。
- **测试体系**：Vitest/Testing Library、Go 权限和审核回归测试。
- **目标平台**：桌面/平板/移动 Web。
- **性能目标**：管理员不加载超级管理员数据；审核请求数不因抽取增加。
- **约束**：单一审核实现、明确 403、保持现有审核规则。
- **规模范围**：概览和一个审核工作区。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| FR-003 | 不加载高权限数据 | AdminPage 不引用治理组件/API | 通过 |
| FR-005 | 单一审核实现 | 抽取共享组件与 hooks | 通过 |
| #38 | 后端权限为最终边界 | admin 路由组只注册审核 API | 通过 |
| Impeccable | 产品 UI 一致与响应式 | MUI 现有组件、scrollable tabs、响应式网格 | 通过 |

## Feature 文档结构

```text
docs/specs/43-admin-review-workspace/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/workspace-ui.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
frontend/src/components/workspace/ReviewWorkspace.tsx
frontend/src/components/workspace/WorkspaceOverview.tsx
frontend/src/components/RoleRoute.tsx
frontend/src/pages/AdminPage.tsx
frontend/src/pages/ForbiddenPage.tsx
frontend/src/LazyRoutes.tsx
```

**结构选择**：按业务能力抽取共享组件，而不是按角色复制页面；AdminPage 保持薄组合层。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/006/007/008 | RoleRoute、ForbiddenPage | 路由矩阵测试 |
| FR-002-FR-005 | AdminPage、Overview、ReviewWorkspace | UI 网络请求与审核回归 |

## 阶段与依赖

1. 权限路由和 403。
2. 审核模块提取及等价回归。
3. 管理员页面收敛和响应式完善。
