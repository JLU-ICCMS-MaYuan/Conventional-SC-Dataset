# 实施计划：用户中心与账户安全

**GitHub Issue**：[#40](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/40)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

扩展用户模型和本人资料 API，使用独立头像服务及只追加资料审计；在 React 中新增用户中心并让 AuthContext 以服务端身份为准。密码修改复用 #39 的会话版本撤销机制。

## 技术上下文

- **语言与版本**：Go 1.25、React 19、TypeScript 5、Python 3.10。
- **主要依赖**：Gin、GORM、bcrypt、MUI、Vitest；WebP 解码使用 `golang.org/x/image/webp`。
- **数据存储**：MySQL 用户资料与审计；文件系统持久卷存头像。
- **测试体系**：Go Handler/事务测试、Vitest/Testing Library、Alembic Pytest。
- **目标平台**：桌面优先、窄屏单列的 MUI App Shell。
- **性能目标**：资料读取一次数据库查询；头像响应可缓存且不暴露磁盘路径。
- **约束**：头像 2 MiB；隐私字段使用专用 DTO；修改密码撤销旧会话。
- **规模范围**：每用户一张当前头像、10 个研究方向标签。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| #31 | 用户名一次性规则 | 复用 UsernameField 与现有 API | 通过 |
| FR-009 | 审计与资料同事务 | 独立只追加审计表 | 通过 |
| FR-010 | 旧 Token 全失效 | session_version 统一校验 | 通过 |
| 设计系统 | MUI、一致、响应式 | 三个职责区块，不做巨型表单 | 通过 |

## Feature 文档结构

```text
docs/specs/40-user-account-center/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/account-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/account.go
goserver/services/avatar.go
goserver/models/models.go
backend/models.py
frontend/src/pages/AccountPage.tsx
frontend/src/components/account/*
frontend/src/context/AuthContext.tsx
frontend/src/components/AppShell.tsx
```

**结构选择**：头像、资料和密码分别提交，避免一个外部文件失败阻断全部文字资料；页面组件按个人资料、账户安全、工作入口拆分。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001-FR-005/011/012 | AccountPage、AppShell、AuthContext | 三角色路由与菜单测试 |
| FR-006-FR-009 | 资料/头像 API 与服务 | 校验、唯一性、事务审计测试 |
| FR-010 | 改密 API + session_version | 旧 JWT 回归测试 |

## 阶段与依赖

1. 用户资料迁移和 API 契约。
2. 本人资料、头像、审计与改密后端。
3. AuthContext、Shell 和用户中心 UI。
4. 响应式、无障碍、部署和文档验证。
