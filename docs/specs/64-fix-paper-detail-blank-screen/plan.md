# 实施计划：修复论文详情页整页白屏

**GitHub Issue**：[#64](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/64)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

只改前端一个组件：在 `PaperEditView` 内加一个字段归一函数，把 `keywords_tags`、
`methodology`、`authors` 三个 JSON 文本列字段统一收敛为 `string[]` 再消费。
后端不变，测试 fixture 校正为后端真实返回形态。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library，`./node_modules/.bin/vitest run --config ../vitest.config.ts`
- **构建验证**：`tsc --noEmit`
- **部署验证**：dev 栈在仓库外 `~/work/SC-Wiki-docker/dev.yaml`，前端改动需
  `docker compose -f dev.yaml up -d --build frontend` 才会进入 bundle
- **约束**：
  - 不改后端字段类型与序列化（NFR-001）
  - 不改详情页权限分流逻辑（仍由后端 `canViewPaper` 单点裁决）
  - 数组形态行为必须不变，Issue #56/#57/#59 的既有验收判据不得回退

## 源代码结构

```text
frontend/src/components/PaperEditView.tsx   [修改] 新增 toTextList，三字段改走归一
tests/01_decentralized_uploading/
  paper-detail-route.test.tsx               [修改] 补 3 个真实载荷用例
docs/specs/64-fix-paper-detail-blank-screen/  [新增] 本 Spec
docs/overview/01_.../pdf-ingestion.md       [修改] 回写行为与变更记录
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | `keywordList = toTextList(paper?.keywords_tags)`，渲染改用该变量 | Vitest 断言三个关键词标签可见 |
| FR-002 | `methodologyList = toTextList(paper?.methodology)`，替换原「仅接受数组」实现 | Vitest 断言 `• 电阻测量` 可见 |
| FR-003 | `setEditAuthors(toTextList(data.authors).join('、'))` | Vitest 断言人名可见且无 `["` / `"]` |
| FR-004 | 单个 `toTextList` 供三处复用，组件级常量 | 代码审查：无重复解析分支 |
| FR-005 | 归一函数内 `try/catch` 包裹 `JSON.parse`，并二次校验解析结果是否为数组 | 既有「非数组不抛错」用例 + 新增用例 |
| FR-006 | 新增 `jsonStringPaper` fixture，字段全用 JSON 字符串 | 用例本身即验证 |

## 技术决策

### 决策1：在消费侧归一，不改后端类型

`papers.keywords_tags` 是 `text` 列，Python 侧 `json.dumps` 写入，Go 侧 `*string`
透传。把它改成结构化数组需同时改动 Go 模型、`paperToDict`、Python 写入侧，以及
`SearchPage`、`share` 两个已按字符串消费的页面 —— 影响面远超一个白屏修复，且每个
消费方都要重新验收。本轮在详情页消费侧容错，成本最低且不引入新的回归面。

字段形态的统一治理值得单独立项，但不应把它和「页面打不开」的紧急修复捆在一起。

### 决策2：归一函数放在组件文件内，暂不抽到 lib

`SearchPage.tsx:707` 与 `share.tsx:632` 也各有一份内联 `try/JSON.parse/catch`，形态上
与本函数重复。但那两处当前不崩溃，把三处一起抽到 `lib/` 需连带回归两个页面，属于
跨页面重构。按 YAGNI 先在详情页收敛；若第四处出现同类需求，届时再抽取。

### 决策3：不新增 ErrorBoundary

白屏之所以是「整页白」而非「局部报错」，是因为全仓没有 `componentDidCatch`。这是
全站性缺口，但它是放大器不是根因。混进本次修复会让验收边界模糊 —— ErrorBoundary
的验收需要覆盖所有路由，而本次只需验证详情页。已在 Spec 的范围外事项留档。

### 决策4：`authors` 用 `、` 连接而非保留数组渲染

作者是单行展示字段（`whiteSpace: 'pre-wrap'` 的 `Typography`），不像关键词有标签容器。
原实现 `JSON.stringify` 会印出 JSON 原文，违反 Issue #59 的既定要求。中文顿号符合
中文排版习惯，与页面其余中文文案一致。

## 实施步骤

1. 在 `PaperEditView.tsx` 增加组件级 `toTextList(value: unknown): string[]`，处理
   数组 / JSON 字符串 / null / 非法 JSON / 非数组 JSON 五种输入
2. `methodologyList` 改走 `toTextList`（原实现遇字符串直接返回空数组，静默丢数据）
3. 新增 `keywordList`，侧栏关键词区改用它，移除 `paper.keywords_tags.map` 直接调用
4. `setEditAuthors` 改为 `toTextList(data.authors).join('、')`
5. 在 `paper-detail-route.test.tsx` 新增「详情页对 JSON 文本列字段的容错」describe，
   用 JSON 字符串 fixture 覆盖三个字段
6. 验证：`vitest run`（详情页 26 例 + 全量）、`tsc --noEmit`
7. 重建 dev 前端容器，实测 `/papers/9` 与 `GET /api/papers/9`
8. 回写 Overview

## 验证结果

| 项目 | 结果 |
|------|------|
| 详情页专项用例 | 26 例通过（`paper-detail-route` 16 + `paper-detail-form-parity` 10） |
| 前端全量用例 | 89 例中 88 通过；1 例失败在 `tests/07_researcher_community_forum/news-feed.test.tsx` |
| `tsc --noEmit` | 通过 |
| 真实 API | 用 id=2 合法 token 请求 `GET /api/papers/9` 返回 200，三字段确认为 `str` |
| 真实页面 | 重建容器后 `/papers/9` 返回 200，新 bundle `index-BYNGd8N8.js` 生效 |

**关于 NewsFeed 失败**：该文件属未提交的每日新闻功能（Issue #63）在建代码，不涉及
详情页任何模块（grep 确认无 `PaperEditView` / `papers/` 引用），与本次改动无关。

## 事故与教训

**测试全绿却漏掉 100% 故障率的缺陷。** 详情页有 16 个用例、覆盖了路由分流、失败提示、
导航跳转，但 `makePaper` fixture 写的是 `authors: ['Hanyu Liu']` —— 数组形态。后端真实
返回的是字符串。fixture 一旦偏离契约，用例数量与覆盖率都会给出虚假的安全感。

教训：构造 fixture 时应从真实 API 响应取样，而不是按字段的「理想类型」手写。本次已把
真实载荷固化进用例，后续同类字段回归会被立即拦住。
