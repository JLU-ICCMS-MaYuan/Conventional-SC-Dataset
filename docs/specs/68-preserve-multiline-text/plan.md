# 实施计划：修复探索页与社区页多行文本丢失换行

**GitHub Issue**：[#68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

给两个页面的两个字段各加 `whiteSpace: 'pre-wrap'`，共四处样式改动。后端不变，逻辑不变。
真正的工作量在测试：断言 computed style，并反向验证该测试能捕获缺陷。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library
- **部署验证**：dev 栈在仓库外 `~/work/SC-Wiki-docker/dev.yaml`，前端改动需
  `docker compose -f dev.yaml up -d --build frontend`
- **约束**：
  - 不改后端、不改 `PaperEditView`、不改校对页录入控件
  - 不对字段内容做 trim 或改写

## 源代码结构

```text
frontend/src/pages/SearchPage.tsx   [修改] summary（#65 已修）+ key_finding
frontend/src/pages/share.tsx        [修改] summary + key_finding
tests/03_data_search_and_database_discovery/
  multiline-text-preserved.test.tsx [新增] 3 例，断言 computed style
docs/specs/68-preserve-multiline-text/  [新增] 本 Spec
docs/overview/03_.../paper-and-property-results.md  [修改] 回写
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | 四处 `Typography` 的 `sx` 加 `whiteSpace:'pre-wrap'` | 2 个用例断言 computed style；产物核对两 bundle 各含 2 处 |
| FR-002 | 与 `PaperEditView` 相同的 `pre-wrap` 值 | 代码审查：三页面同一字段样式一致 |
| FR-003 | 只加 CSS，不动字段值 | 用例断言 `textContent` 含 `\n` |
| FR-004 | 断言 computed style 而非文本内容 | 反向验证：移除样式后用例失败 |

## 技术决策

### 决策1：断言 computed style，而非断言视觉换行

jsdom 不做布局计算，无法验证「文本在视觉上分了几行」。可选的断言方式有两种：

- 断言 DOM 文本含 `\n` —— 但这在未修复时也成立（React 会把 `\n` 原样写进 DOM，是 CSS
  折叠了它），属恒真断言，抓不到缺陷
- 断言 computed `white-space` 为 `pre-wrap` —— 直接对应修复内容

因此以后者为主，前者作为「前端未改写内容」的补充断言（对应 FR-003）。

### 决策2：反向验证测试有效性

上一条决策指出「断言 DOM 含 `\n`」是恒真的。为确认最终的用例不落入同类陷阱，实施后临时
移除 `pre-wrap` 重跑：2 个用例立即失败，恢复后通过。这一步是必要的 —— 一个不会失败的
测试比没有测试更糟，它给出虚假的安全感。

### 决策3：不引入 Markdown 渲染

保留换行已满足需求。引入 Markdown 会改变内容语义：`1.` 被渲染成有序列表（编号可能被
重排）、下划线与星号被吃掉。用户录入的是纯文本分条，展示侧不该重新解释它。

## 实施步骤

1. `SearchPage.tsx` 的 `key_finding` 加 `pre-wrap`（`summary` 在 Issue #65 已修）
2. `share.tsx` 的 `summary` 与 `key_finding` 各加 `pre-wrap`
3. 排查同类字段：确认 `PaperEditView` 四处已有、表格 `row.note` 为单行不需要
4. 新建 `multiline-text-preserved.test.tsx`，3 个用例
5. 反向验证：临时移除 `pre-wrap`，确认用例失败
6. `tsc --noEmit`、全量测试、重建容器、产物核对

## 验证结果

| 项目 | 结果 |
|------|------|
| 多行文本用例 | 3 例通过 |
| 反向验证 | 移除 `pre-wrap` 后 2 例失败，确认非恒真 |
| 前端全量 | 107 例中 106 通过 |
| `tsc --noEmit` | 通过 |
| 产物核对 | `SearchPage-CPpRNREo.js` 与 `share-*.js` 各含 2 处 `pre-wrap` |
| 数据侧复核 | 库中 `cat -A` 见 `\n`；API 返回真实换行（`chr(10)` 命中，`'\\n'` 字面未命中） |

**关于 NewsFeed 失败**：`tests/08_news/NewsFeed.test.tsx` 属 Issue #63 每日新闻在建代码，
本次改动前即失败，与本 Issue 无关。

## 实施细节

**Testing Library 的空白归一化。** `getByText` 默认对目标文本做空白归一化，多行字符串
因此永远匹配不到。须传 `normalizer: value => value` 关掉归一化才能按原文查找：

```ts
const findExact = (text: string) =>
  waitFor(() => screen.getByText(text, { normalizer: value => value }))
```

## 事故记录

**同一缺陷分四处，第一轮只修了一处。** Issue #65 修 `summary` 时只改了探索页那一处，
漏掉同区块的 `key_finding` 与社区页的两处，#65 关闭后用户复测才发现核心发现仍然合并成段。

这是同类遗漏第二次出现。Issue #59 修结构预览读取来源时也只修了三个页面中的一个（详情页），
探索页与社区页留到 #65 才补。两次的共同点是「同一缺陷在多页面各存一份，逐处修必然漏」。

对策不是下次更小心，而是改变动手顺序：先枚举「哪些字段属于这一类、在哪些页面渲染」，
再一次改完，最后用一条断言样式的测试锁住 —— 任何页面遗漏都会被拦住。本次即按此执行，
并额外做了反向验证确认测试真的有效。
