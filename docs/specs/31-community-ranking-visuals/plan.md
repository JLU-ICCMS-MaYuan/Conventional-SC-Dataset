# 实施计划：唯一公开用户名与贡献榜身份

**GitHub Issue**：[#31](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/31)

**日期**：2026-08-21

**Spec**：[spec.md](spec.md)

## 摘要

通过 Alembic 为用户增加大小写敏感唯一用户名和更名资格，为超级管理员更名增加只追加审计表；Go 服务实现权威验证、注册、可用性、自助更名、管理员更名与缓存失效；前端统一使用用户名并提供注册检查、历史更名和审计管理界面；Python共享模型与认证契约同步更新。

## 技术上下文

- **语言与版本**：Go 1.25、Python 3.10+、TypeScript 5.6、React 19
- **主要依赖**：Gin、GORM、FastAPI、SQLAlchemy、Alembic、MUI 7
- **数据存储**：MySQL 8.4、Redis 7
- **测试体系**：Go `testing`/sqlmock/miniredis、Pytest、TypeScript、Vite
- **目标平台**：Docker Compose 与现有 Web 客户端
- **性能目标**：可用性查询使用唯一索引；Top 20 渲染保持线性复杂度
- **约束**：用户名大小写敏感；不增加前端或后端第三方依赖；保留邮箱登录
- **规模范围**：全量历史用户一次迁移，两个 Top 20 榜单，单用户更名事务

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|----------|----------|--------------|------|
| AGENTS.md | KISS、DRY、精确范围、中文文档 | 集中用户名策略函数和明确接口边界 | 通过 |
| Spec FR-001–FR-007 | 大小写敏感唯一、迁移、注册和可用性 | `ascii_bin` 唯一索引、迁移回填、双层校验 | 通过 |
| Spec FR-008–FR-014 | 隐私、更名、审计和榜单身份 | 客户端 DTO 排除实名、事务审计、缓存失效 | 通过 |
| Issue #29 | 统计与刷新口径不变 | 只替换身份字段，不改聚合条件和排序 | 通过 |
| 工作区并行改动 | 不混入 Issue #32/#33 | 只编辑列出的认证、用户和榜单文件 | 通过 |

## Feature 文档结构

```text
docs/specs/31-community-ranking-visuals/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── username-api.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
alembic/versions/20260821_0006_add_public_usernames.py
backend/models.py
backend/api/auth_routes.py
backend/email_service.py
backend/username_policy.py
backend/scripts/create_superadmin.py
backend/scripts/import_data.py
backend/scripts/export_data.py
goserver/models/models.go
goserver/handlers/username.go
goserver/handlers/admin.go
goserver/handlers/stats.go
goserver/middleware/auth.go
goserver/main.go
frontend/src/context/AuthContext.tsx
frontend/src/lib/username.ts
frontend/src/components/UsernameField.tsx
frontend/src/components/AuthDialog.tsx
frontend/src/components/AppShell.tsx
frontend/src/pages/AdminPage.tsx
frontend/src/pages/share.tsx
tests/07_researcher_community_forum/
```

**结构选择**：用户名策略在每种后端语言中集中实现；Go 负责当前生产写路径，Python保持共享模型和备用路由一致。前端提取用户名字段以复用注册、自助和管理员更名的校验与可用性反馈。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|------|---------------|----------|
| FR-001–FR-004 | Alembic、双后端用户模型 | 迁移与模型测试 |
| FR-005–FR-008 | 注册、登录和可用性接口 | Go/Python契约测试、前端测试 |
| FR-009 | 自助更名事务 | sqlmock 并发资格测试 |
| FR-010–FR-011 | 超管更名与审计接口 | 权限、事务、审计测试 |
| FR-012–FR-014 | 缓存和榜单 DTO | miniredis、聚合测试 |
| FR-015–FR-016 | 社区页面共享榜单渲染 | Pytest、构建、桌面与窄屏浏览器验收 |
| FR-017 | 原有排行回归套件 | Go 全量、社区 Pytest |
| FR-018 | 审核事件写入与请求幂等 | Go 审核事件测试、贡献聚合测试 |

## 阶段与依赖

1. 先建立迁移、策略和接口契约测试。
2. 实现数据模型及后端用户名服务。
3. 实现注册、账号菜单、管理员更名审计和榜单身份。
4. 更新脚本与双后端兼容面。
5. 执行全量验证并回写 Overview 和 Issue。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
|------------|------------|--------------------------|
| 大小写敏感数据库排序规则 | 默认 MySQL 排序规则通常不区分大小写 | 仅应用层检查无法阻止并发重复 |
| 独立审计实体与事务 | 超管可多次更名且必须可追责 | 普通日志不能保证字段完整和持久查询 |
| 双后端策略同步 | Python共享用户模型且可能承接回退路由 | 只改 Go 会留下未来隐私和约束漂移 |
