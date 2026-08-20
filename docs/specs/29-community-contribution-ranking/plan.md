# 实施计划：社区贡献排行榜

**GitHub Issue**：[#29](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/29)

**日期**：2026-08-20

**Spec**：[spec.md](spec.md)

## 摘要

通过 Alembic 新增不可变论文审核事件，重构单篇与批量审核为事务化写入；Go 服务新增可选认证的社区贡献聚合 API，并用 Redis 缓存公共排行榜一小时；React 社区页增加贡献概览、双 Top 20、本人排名和自动/手动刷新状态。

## 技术上下文

- **语言与版本**：Go 1.25、TypeScript 5.6、Python/Alembic 迁移
- **主要依赖**：Gin 1.12、GORM 1.31、React 19、MUI 7、Redis 客户端
- **数据存储**：MySQL 主业务库、Redis 一小时共享缓存
- **测试体系**：Go `go test ./...`、前端 `npm run build`、仓库 Python `pytest` 回归按影响范围执行
- **目标平台**：Docker 部署的 Nginx + React、Go API、MySQL、Redis
- **性能目标**：同一小时普通访问命中共享缓存；聚合使用常数次 SQL，不产生逐用户查询
- **约束**：公开响应不得泄露敏感用户字段；历史事件与论文当前状态事务一致；兼容未发送幂等键的旧客户端
- **规模范围**：公开 Top 20，个人排名覆盖全部贡献者；当前用户和论文规模下使用数据库聚合与排序

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | 简体中文文档、KISS、DRY、先验证后收敛 | 复用现有 Gin/GORM/Redis/MUI，不引入新依赖 | 通过 |
| Overview | Go 为主要公开 API，MySQL 为事实源，社区页为 `/share` | 新能力落在现有 Go 路由和社区页面 | 通过 |
| Spec FR-005–FR-006 | 每次有效审核计数且防重 | 审核事件表、事务、请求唯一键和业务无变化判断 | 通过 |
| Spec FR-007–FR-009 | 匿名公开、登录附加本人排名、字段最小化 | 专用 DTO 与可选认证，不复用管理员用户序列化 | 通过 |
| Spec FR-010–FR-013 | 一小时缓存、立即刷新、失败保留 | Redis TTL、`refresh=true`、前端定时器和陈旧数据保留 | 通过 |

## Feature 文档结构

```text
docs/specs/29-community-contribution-ranking/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── community-contributions-api.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
alembic/versions/<revision>_add_paper_review_events.py
backend/models.py
goserver/models/models.go
goserver/middleware/auth.go
goserver/handlers/admin.go
goserver/handlers/stats.go
goserver/handlers/stats_test.go
goserver/main.go
frontend/src/pages/share.tsx
frontend/src/pages/AdminPage.tsx
docs/overview/05-visualization-and-metrics/
```

**结构选择**：审核事件属于现有论文审核域，写入逻辑保留在审核 handlers；排名属于现有统计域，读取逻辑放在 `stats.go`。前端直接扩展现有社区页，不创建新的路由或状态框架。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001–FR-004 / US1 | 社区聚合查询与稳定排序 | Go 表驱动数据库测试、Quickstart 场景 1 |
| FR-005–FR-006、FR-014 / US1 | `paper_review_events`、迁移、事务审核写入 | 迁移检查与单篇/批量/重试测试 |
| FR-007–FR-009 / US2 | 专用响应 DTO、可选认证、本人排名 | 匿名/登录/Top 20 外/敏感字段测试 |
| FR-010–FR-013 / US3 | Redis TTL、强制刷新、前端计时器与状态 | 缓存测试、前端构建、Quickstart 场景 2–3 |
| SC-001–SC-005 | 全链路实现与验证 | `go test ./...`、`npm run build`、Quickstart |

## 阶段与依赖

1. 建立审核事件模型与迁移，完成回填规则。
2. 先写后端失败测试，再实现事务化审核写入、统计查询、可选认证与缓存。
3. 扩展社区页面和审核请求幂等键，完成自动/手动刷新与个人排名。
4. 运行测试与构建，执行 Quickstart，回写 Overview 并检查任务收敛。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 新增审核事件表 | 当前论文行只能保存最终审核人，无法统计每轮劳动 | 聚合 `papers.reviewed_by_user_id` 会丢失历史贡献 |
| 可选认证 | 一个公开响应需按登录状态附加个人排名 | 拆成两个端点会重复聚合与前端请求 |
| 请求幂等键 | 网络重试不可增加审核次数 | 仅比较状态无法区分真实重复审核轮次 |
