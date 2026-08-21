# 实施计划：社区 Tc 双图个人配置与品质因子

**GitHub Issue**：[#30](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/30)

**日期**：2026-08-20

**Spec**：[spec.md](spec.md)

## 摘要

后端以白名单 `tc_field` 从 `superconductor_records` 生成公共图表点并按字段隔离缓存；前端新增带校验的个人偏好模块，改造社区页为响应式双列，并扩展 Recharts 组件绘制 Pickard S 等值线和温度参考线。

## 技术上下文

- **语言与版本**：Go 1.25、TypeScript 5.6、React 19
- **主要依赖**：Gin、GORM、MUI 7、Recharts 2.15
- **数据存储**：公共记录 MySQL；个人偏好浏览器 localStorage；公共响应 Redis 缓存
- **测试体系**：Go `testing`；前端 `tsc -b && vite build`；浏览器人工验收
- **目标平台**：桌面和移动 Web
- **性能目标**：每次只请求当前字段；公共结果按字段复用缓存
- **约束**：不改 schema、不建个人配置 API、不引入前端测试依赖
- **规模范围**：2 个 API、1 个页面、1 个图表组件、1 个偏好模块

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| AGENTS.md | KISS、DRY、YAGNI | 单一白名单与单一偏好模块，无新服务 | 通过 |
| Overview | 公共数据必须经审核 | 联接 Approved 论文并要求 `show_in_chart` | 通过 |
| Spec FR-012 | 不持久化个人科研数据 | localStorage 只保存两个枚举 | 通过 |
| Issue #30 | 五字段与 S 图 | API 契约和图表覆盖层完整映射 | 通过 |

## Feature 文档结构

```text
docs/specs/30-community-tc-chart-preferences/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/chart-stats-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/stats.go
goserver/handlers/stats_test.go
frontend/src/lib/chartPreferences.ts
frontend/src/pages/share.tsx
frontend/src/components/ChartScatter.tsx
docs/overview/05-visualization-and-metrics/tc-history-and-pressure-charts.md
```

**结构选择**：API 参数解析留在 stats handler；本地配置解析为独立纯函数；页面负责编排状态，图表组件只负责绘制。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001 / US1 | `share.tsx` MUI Grid | 1440/390 px 浏览器验收 |
| FR-002–FR-009 / US2 | API 契约、`chartPreferences.ts` | Go 单测、构建、账号切换验收 |
| FR-010–FR-011 / US3 | `ChartScatter` 覆盖层 | 公式抽样与视觉验收 |
| FR-012–FR-013 | 页面编排与无服务端偏好 API | 网络/数据库检查与回归 |

## 阶段与依赖

1. 建立字段白名单、API 契约与单测。
2. 建立本地偏好模型并接入双图请求和响应式布局。
3. 增加品质因子覆盖层、状态和可访问图例。
4. 构建、测试、浏览器验收并更新 Overview。

## 复杂度说明

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 后端动态列白名单 | 五个列共享端点且必须防 SQL 注入 | 客户端字段直接拼 SQL 不安全 |
| 曲线采样 | S 等值线需随坐标域响应 | 静态背景图会失真 |
