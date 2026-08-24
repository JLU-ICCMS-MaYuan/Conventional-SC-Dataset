# 实施计划：管理员资格申请与审批

**GitHub Issue**：[#42](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/42)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

以独立申请表保存固定资料快照和状态机，通过数据库唯一保护限制单一 pending；审批事务同时锁定申请与用户，角色降级复用统一治理审计。

## 技术上下文

- **语言与版本**：Go 1.25、React 19、TypeScript 5、Python 3.10。
- **主要依赖**：Gin、GORM、MUI、Vitest、Alembic。
- **数据存储**：MySQL 管理员申请与治理审计。
- **测试体系**：Go sqlmock/Handler，隔离 MySQL 并发约束，Vitest 状态 UI。
- **目标平台**：用户中心提交、超级管理员工作台审批。
- **性能目标**：申请列表分页；审批为单事务常数次查询。
- **约束**：只追加历史、单一 pending、拒绝/降级原因必填。
- **规模范围**：每用户多条历史、最多一条 pending。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| FR-003 | 单一 pending | 生成守卫列 + 唯一约束 | 通过 |
| FR-006 | 角色与状态原子 | 锁申请和用户，同事务更新 | 通过 |
| #38 | 仅 superadmin 审批 | superadmin 路由组 | 通过 |
| #40 | 固定资料快照 | 提交时复制明确字段 | 通过 |

## Feature 文档结构

```text
docs/specs/42-admin-role-applications/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/admin-application-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/admin_applications.go
goserver/models/models.go
backend/models.py
frontend/src/components/account/AdminApplicationSection.tsx
frontend/src/components/superadmin/AdminApplicationsPanel.tsx
```

**结构选择**：申请领域独立于 User，不复用 `is_approved`；超级管理员 UI 只消费 API，不承载状态机规则。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001-FR-004/007 | 本人申请 API、唯一守卫 | 条件、重复、撤回、重提测试 |
| FR-005/006/008/009 | 超级管理员审批 API、治理审计 | 权限、事务、历史测试 |

## 阶段与依赖

1. 申请和治理审计迁移。
2. 本人提交/撤回/历史 API。
3. 超级管理员审批/降级 API。
4. 两端 UI 与并发验收。
