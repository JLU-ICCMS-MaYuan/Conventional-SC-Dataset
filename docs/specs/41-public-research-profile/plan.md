# 实施计划：公开科研身份页

**GitHub Issue**：[#41](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/41)

**日期**：2026-08-24

**Spec**：[spec.md](spec.md)

## 摘要

新增独立匿名白名单 API 和 React 公开资料页；贡献榜只把现有 username 渲染为链接，不扩张排行榜响应。审核记录补充稳定 username 字段以生成链接。

## 技术上下文

- **语言与版本**：Go 1.25、React 19、TypeScript 5。
- **主要依赖**：Gin、GORM、React Router、MUI、Vitest。
- **数据存储**：读取 users 与账号状态，不新增实体。
- **测试体系**：Go DTO/Handler 测试、Vitest 匿名页面与链接测试。
- **目标平台**：公开响应式页面。
- **性能目标**：用户名唯一索引单次查询；公开头像使用缓存头。
- **约束**：严格字段白名单、noindex、不改变排行榜缓存。
- **规模范围**：单用户资料页。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| #31 | 排行 DTO 与用户名规则稳定 | 只增加前端链接 | 通过 |
| FR-002/003 | 白名单且无邮箱 | 独立 DTO，不序列化 ORM | 通过 |
| FR-006 | 匿名但 noindex | 页面级 meta 生命周期 | 通过 |
| FR-009 | 封禁/注销差异 | DTO 状态映射 | 通过 |

## Feature 文档结构

```text
docs/specs/41-public-research-profile/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── contracts/public-profile-api.md
├── tasks.md
└── checklists/requirements.md
```

## 源代码结构

```text
goserver/handlers/public_profile.go
frontend/src/pages/PublicUserPage.tsx
frontend/src/pages/share.tsx
frontend/src/components/ReviewWorkspace.tsx
frontend/src/LazyRoutes.tsx
```

**结构选择**：公开 API、本人资料 API 和排行榜 API 三者保持独立，避免缓存或权限边界互相污染。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001-FR-006/008/009 | 公开 DTO、Handler、PublicUserPage | 匿名白名单和页面测试 |
| FR-007/010 | 排行榜/审核/用户中心链接 | 回归测试排行榜 DTO 与入口 |

## 阶段与依赖

1. 冻结公开 DTO 和状态映射。
2. 实现匿名 API 与页面。
3. 接入三个入口并验证 #31 不回归。
