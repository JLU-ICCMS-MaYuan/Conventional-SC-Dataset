# 实施计划：超级管理员工作台与账号治理

**GitHub Issue**：[#44](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/44)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

新增独立 superadmin 路由组和工作台，复用审核、图表与快讯组件；账号治理使用明确动作端点、行锁和只追加审计，统一递增 session_version 撤销会话。

## 技术上下文

- **语言与版本**：Go 1.25、React 19、TypeScript 5、Python 3.10。
- **主要依赖**：Gin、GORM、MUI、Vitest、Alembic。
- **数据存储**：users 账号状态、治理审计、现有资料/用户名审计。
- **测试体系**：Go 权限/事务/并发、隔离 MySQL、Vitest 工作台交互。
- **目标平台**：高权限生产力工作台，桌面优先并支持窄屏。
- **性能目标**：列表分页；工作台按当前 tab 懒加载，不一次请求全部治理数据。
- **约束**：禁止自操作、至少一名 active superadmin、禁止物理删除。
- **规模范围**：现有用户、论文、图表和快讯管理规模。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| #38 | 后端权限是安全边界 | 独立 `/api/superadmin` 组 | 通过 |
| FR-002 | 不复制审核 | 复用 ReviewWorkspace | 通过 |
| FR-008/009 | 审计与最后超管保护 | 事务行锁、条件更新 | 通过 |
| FR-007 | 历史链条不破坏 | 保留 User 行、状态化注销 | 通过 |

## Feature 文档结构

```text
docs/specs/44-superadmin-governance-workspace/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/superadmin-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/superadmin_users.go
goserver/main.go
frontend/src/pages/SuperAdminPage.tsx
frontend/src/components/superadmin/*
frontend/src/components/workspace/*
```

**结构选择**：治理动作使用独立 POST 端点而不是通用 `PUT User`，使权限、必填原因、状态转换和审计均可精确测试。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001-FR-004/011/012 | superadmin 路由与页面模块 | 权限矩阵、懒加载、面板测试 |
| FR-005-FR-010 | 治理动作服务、SensitiveActionDialog | 事务、会话、并发和交互测试 |

## 阶段与依赖

1. 后端路由分组和治理状态机。
2. 工作台薄组合和共享审核接入。
3. 内容管理、申请、用户和审计面板。
4. 并发、响应式和 Overview 验收。
