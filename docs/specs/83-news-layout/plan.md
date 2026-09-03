# 实施计划：News 页面品牌信息与三列独立资讯流

**GitHub Issue**：[ #83](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/83)

**日期**：2026-09-03

**Spec**：[spec.md](spec.md)

## 摘要

替换 News 页双语品牌文案，删除重复的 Hero/功能卡入口。将当前单列 `NewsFeed` 拆为页面级来源状态和固定类型的可复用资讯列；每个列组件独立请求 `GET /api/news/feed?kind=<类型>&page=<页码>&page_size=5`，并维持自己的页码、加载、失败和重试状态。桌面端采用三列紧凑布局，窄屏依次纵向排列。

## 技术上下文

- **语言与版本**：TypeScript 5.6、React 19。
- **主要依赖**：React Router 6、MUI 7、Vitest、Testing Library。
- **数据存储**：不适用；仅读取既有自动资讯与人工快讯接口。
- **测试体系**：Vitest 配置为 `vitest.config.ts`；前端生产构建使用 `npm --prefix frontend run build`。
- **目标平台**：现代桌面和移动浏览器。
- **性能目标**：初次加载固定为三条、每条最多五项的轻量 GET 请求；单栏翻页只发起一条请求。
- **兼容约束**：保持 `/api/news/feed`、`/api/news`、详情抽屉和安全外链的现有契约；不修改后端。
- **规模范围**：仅 `/news` 页面及其专用双语文案、自动化测试。

## 质量门

| 约束来源 | 强制要求 | 设计如何满足 | 状态 |
| --- | --- | --- | --- |
| `AGENTS.md` | Issue 为协作权威，Spec 与 Issue 双向链接 | #83 与本目录互链 | 通过 |
| `docs/overview/news.md` | 自动资讯不等于论文入库，保留来源、状态和详情语义 | 只变前端展示，继续读取相同 API 数据 | 通过 |
| Issue #83 / FR-005 | 三栏各 5 条且独立分页 | 固定类型列拥有独立状态和请求 | 通过 |
| Issue #83 / FR-006 | 1440×900 首屏可见分页，窄屏可读 | 响应式三列网格与紧凑条目布局；浏览器验收 | 待实施验证 |
| 项目文档语言 | `docs/` Markdown 使用简体中文 | 全部 Feature 文档使用简体中文 | 通过 |

## Feature 文档结构

```text
docs/specs/83-news-layout/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── tasks.md
└── checklists/
    └── requirements.md
```

## 源代码结构

```text
frontend/src/pages/NewsPage.tsx                         # Hero、保留模块及页面编排
frontend/src/components/NewsFeed.tsx                    # 自动资讯列、详情抽屉、来源状态
frontend/src/i18n/zh/news.ts                            # 中文页面文案
frontend/src/i18n/en/news.ts                            # 英文页面文案
tests/03_data_search_and_database_discovery/news-page-layout.test.tsx
                                                        # 三列独立分页和品牌交互测试
```

**结构选择**：将单个资讯列做成按固定 `kind` 参数工作的组件。它负责自身数据请求和分页；页面组件只排列三个列并保留来源状态和全局详情抽屉。这样同一套加载、失败、空状态和条目渲染逻辑只有一个实现，同时确保状态没有跨栏耦合。

## 需求到设计的映射

| 来源 | 设计组件/接口 | 验证方式 |
| --- | --- | --- |
| FR-001–FR-003 / US1 | `NewsPage.tsx`、`zh/news.ts`、`en/news.ts` | 双语 UI 与路由测试 |
| FR-004–FR-005 / US2 | `NewsFeed.tsx` 固定类型列；既有 `/api/news/feed` 查询参数 | Vitest 断言请求、每栏条目与独立页码 |
| FR-006 / US2 | `NewsPage.tsx` 响应式网格、`NewsFeed.tsx` 紧凑条目布局 | 1440×900 与窄屏浏览器验收 |
| FR-007 / US3 | 可复用列保留状态渲染；页面级详情抽屉和来源状态 | 空/失败/详情/外链 Vitest |

## 阶段与依赖

1. 补充 News 页面布局与交互的测试数据和测试用例。
2. 更新中英文 Hero 文案，移除指定入口。
3. 重组自动资讯组件，使三栏独立加载和分页，同时复用详情抽屉及来源状态。
4. 调整响应式布局，执行单元测试、构建和浏览器首屏验收。

## 必要复杂度

| 必要复杂度 | 为什么需要 | 已拒绝的简单方案及原因 |
| --- | --- | --- |
| 固定类型的可复用资讯列 | 每栏必须隔离页码、加载、错误和重试状态，同时避免复制三段 UI | 单个全局筛选状态不能同时表示三栏；复制三份 JSX 会造成维护漂移 |
