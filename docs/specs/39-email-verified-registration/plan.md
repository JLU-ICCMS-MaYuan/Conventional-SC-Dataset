# 实施计划：邮箱验证注册

**GitHub Issue**：[#39](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/39)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

在 Go 认证主链路新增 SMTP 发送抽象、Redis 原子挑战存储、验证与重发接口；注册固定创建普通用户，验证成功签发包含会话版本的 JWT。前端沿用现有验证码步骤并补重发与自动登录。

## 技术上下文

- **语言与版本**：Go 1.25、TypeScript 5、React 19、Python 3.10（迁移测试）。
- **主要依赖**：Gin、GORM、go-redis、bcrypt、MUI、Vitest。
- **数据存储**：MySQL 用户验证事实；Redis 验证码摘要、TTL 与额度。
- **测试体系**：Go `testing/httptest/sqlmock/miniredis`、Vitest、Pytest Alembic 契约测试。
- **目标平台**：Docker Compose，Go 服务为 `/api/auth/**` 入口。
- **性能目标**：发送和验证均为常数次 Redis/MySQL 操作；接口超时不得超过外部 SMTP 超时上限。
- **约束**：验证码不得明文持久化或记录；Redis/SMTP 失败关闭。
- **规模范围**：单站点注册流量，按邮箱和 IP 双维度限流。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| AGENTS.md | Alembic 管理迁移，文档简体中文 | 单一迁移 head，三模型同步 | 通过 |
| #31 | 用户名唯一、邮箱登录 | 注册复用现有用户名校验 | 通过 |
| FR-003/005 | 单次消费与原子限流 | Redis Lua/事务封装 | 通过 |
| Overview | 当前 Go 缺少验证端点 | 新接口只在 Go 注册 | 通过 |

## Feature 文档结构

```text
docs/specs/39-email-verified-registration/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/auth-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/auth.go
goserver/services/email.go
goserver/services/verification.go
goserver/middleware/auth.go
goserver/cache/cache.go
goserver/config/config.go
frontend/src/context/AuthContext.tsx
frontend/src/components/AuthDialog.tsx
alembic/versions/<next>_account_identity_foundation.py
docker/compose*.yaml
docker/.env.example
```

**结构选择**：认证 Handler 只编排请求，验证码原子状态和 SMTP 分别封装，避免把外部 IO、限流和用户事务堆在现有 `admin.go`。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/007 | 注册与登录 Handler | 角色注入和未验证登录测试 |
| FR-002/003/006 | 邮件服务、验证挑战、验证接口 | 发送失败、单次消费、自动登录测试 |
| FR-004/005/009/010 | Redis 原子额度服务 | miniredis/Lua 与错误语义测试 |
| FR-008 | AuthDialog | Vitest 注册流程测试 |

## 阶段与依赖

1. 建立账号身份基础迁移、JWT 会话版本和邮件配置。
2. 实现验证码状态、SMTP 和 Go API。
3. 改造前端注册验证状态机。
4. 运行迁移、行为、构建和 Compose 验证。
