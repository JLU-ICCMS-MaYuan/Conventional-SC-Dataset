# 实施计划：全网超导文献、科研新闻与产业资讯定时发现

**GitHub Issue**：[＃88](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/88)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

在 #63 的资讯缓存、去重和页面基础上，扩展公开联网来源与来源溯源字段，增加 OpenAlex 和可配置出版社适配器，修复 Worker 长连接恢复，并把论文语义、科研报道、社会产业资讯与展示栏位分离。

## 技术上下文

- **语言与版本**：Python 3、Go、React/TypeScript；以仓库现有运行时为准。
- **主要依赖**：SQLAlchemy/Alembic、httpx/feedparser、RQ/Redis、GORM、MUI/Vitest。
- **数据存储**：MySQL 资讯表新增字段；不写正式 `papers` 等业务表。
- **测试体系**：pytest、Go test、Vitest；外部来源使用固定响应样本，保留隔离 MySQL/Redis 集成测试。
- **目标平台**：Docker Compose 与本地 `scripts/dev.sh`。
- **性能目标**：来源限速、单请求有限重试，单次任务不因一个来源失败而中断其他来源。
- **约束**：不抓取受限全文，不泄露凭证，不把聚合来源伪装成出版社官方来源。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
|---|---|---|---|
| #88 Spec FR-001/002 | 固定主题、指定来源联网发现 | 来源注册表和定时任务 | 通过 |
| #88 Spec FR-003/008 | 发现来源与原文来源分离 | 资讯字段和链接契约 | 通过 |
| #88 Spec FR-006 | Phys.org 栏位与语义分离 | `content_type`/`display_kind` | 通过 |
| #88 Spec FR-009 | Redis 超时自动恢复 | 长连接配置与 Worker 循环 | 通过 |
| AGENTS.md | 文档中文、变更后验证并提交 | 本目录产物与定向测试 | 通过 |

## 源代码结构

```text
backend/news/{domain.py,sources.py,service.py,scheduler.py,__main__.py,models.py}
alembic/versions/<new_news_discovery>.py
goserver/{models/news_feed.go,handlers/news_feed.go}
frontend/src/components/NewsFeed.tsx
frontend/src/i18n/{zh,en}/news.ts
tests/07_researcher_community_forum/*news*
```

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
|---|---|---|
| FR-001/002/003 | `Sources` 来源注册与 OpenAlex/出版社适配器 | Python 固定响应测试 |
| FR-004/005/006 | 内容类型、展示栏位、相关性依据字段；OpenAlex 滚动回看 30 天，仅接收已发表期刊 article，摘要命中需学术上下文 | 固定响应 pytest、真实 DOI 只读采集、ORM/API/Vitest 契约 |
| FR-007/008 | `upsert` 身份键与来源链接 | 去重回归测试 |
| FR-009 | Redis 连接与 Worker 入口 | 隔离 Redis 集成测试 |
| FR-010/011 | Transport 限制和跨层测试 | pytest/Go/Vitest |

## 阶段与依赖

1. 数据字段、来源注册表和 Worker 恢复等基础能力。
2. OpenAlex/Crossref/出版社聚合发现与去重。
3. API/UI 类型和栏位展示。
4. 社会资讯可配置适配器、测试、文档和运行验证。

## 复杂度说明

来源适配、数据溯源和展示栏位分离是需求要求的必要复杂度；已拒绝直接让前端逐站抓取和把所有内容塞入单一 `kind` 字段，因为会造成凭证/CORS 风险和语义错误。
