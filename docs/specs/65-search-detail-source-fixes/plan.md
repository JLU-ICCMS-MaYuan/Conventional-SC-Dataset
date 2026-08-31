# 实施计划：修复探索页与社区页三处缺陷

**GitHub Issue**：[#65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)

**日期**：2026-08-31

**Spec**：[spec.md](spec.md)

## 摘要

新增一个纯数据提取模块 `lib/paperDetailView.ts`，把「跨三张来源表汇总物性」与「从材料
状态取结构」两件事收敛为公共函数；探索页与社区页改用它。另外两处是单行修复：移除
`'La,H'` 兜底、给论文总结加 `pre-wrap`。后端不变。

## 技术上下文

- **语言与版本**：TypeScript 5.6 + React 19 + Material-UI 7
- **测试体系**：Vitest + React Testing Library，`./node_modules/.bin/vitest run --config ../vitest.config.ts`
- **构建验证**：`tsc --noEmit`
- **部署验证**：dev 栈在仓库外 `~/work/SC-Wiki-docker/dev.yaml`，前端改动需
  `docker compose -f dev.yaml up -d --build frontend`
- **约束**：
  - 不改后端 API 字段结构
  - 不动 `PaperEditView`（Issue #59 已修正，避免影响其验收判据）
  - 两个页面各自保留现有表格样式，只统一数据来源

## 源代码结构

```text
frontend/src/lib/paperDetailView.ts          [新增] 公共提取逻辑
frontend/src/pages/SearchPage.tsx            [修改] 三处缺陷全部涉及
frontend/src/pages/share.tsx                 [修改] 物性表来源 + 新增结构预览区块
vitest.config.ts                             [修改] 注册 tests/03 目录
tests/03_data_search_and_database_discovery/
  paper-detail-view-sources.test.tsx         [新增] 提取逻辑 12 例
  search-page-defaults.test.tsx              [新增] 默认选中 3 例
docs/specs/65-search-detail-source-fixes/    [新增] 本 Spec
docs/overview/03_.../paper-and-property-results.md  [修改] 回写
```

## 需求到设计的映射

| 来源 | 设计 | 验证方式 |
|------|------|----------|
| FR-001 | `searchParams.get('elements') \|\| ''`，移除 `'La,H'` 兜底 | Vitest 断言「未选择」可见 |
| FR-002 | 读参逻辑本身不变，只改兜底值 | Vitest 用 `?elements=Nb,Ti` 断言仍预选 |
| FR-003 | summary 的 `Typography` 加 `whiteSpace:'pre-wrap'` | 库中 `cat -A` 确认有 `\n`；人工核对 |
| FR-004 | `collectPropertyRows` 依次遍历 `tc_results`、`calculation_contexts`、`key_properties` | 用例断言 Tc 值与标签顺序 |
| FR-005 | 参数值 `== null` 时 `continue`，不 push 行 | 用例断言 `μ*` 不在标签列表 |
| FR-006 | `collectStructures` 只遍历 `material_states[].structures[]` | 反向用例：伪造 `key_properties[].structure_text` 应返回空 |
| FR-007 | `share.tsx` 引入同两个函数，新增结构预览 `details` 区块 | `tsc` + 人工核对 |
| FR-008 | 单一模块导出两个纯函数，两页面共用 | 代码审查：无重复解析分支 |
| FR-009 | 每层 `Array.isArray` 守卫 + 可选链 | 用例覆盖 null / 缺键 / 空数组 |

## 技术决策

### 决策1：抽取纯数据函数，而非复用 PaperEditView 组件

用户曾询问是否直接复用详情页组件。若那样做，探索页的表格样式、「返回结果表格」布局、
侧栏结构预览的位置都会跟着变 —— 改动面从「修三个 bug」扩大为「重做两个页面的详情视图」。

改为抽取纯数据函数：来源统一了（消除 FR-008 关心的重复），但两个页面各自保留现有样式。
这也让提取逻辑可以脱离 DOM 单元测试，12 个用例总耗时 7ms。

### 决策2：Tc 排在普通物性之前

超导论文的核心结论是 Tc。按表结构顺序（普通物性在 `key_properties` 里、Tc 在材料状态
下）排列是实现细节泄漏到界面，读者关心的顺序与存储顺序无关。

### 决策3：NULL 值的计算参数不产生表格行

后端 `calculationContextsToDict` 明确注释了「读取侧不筛选也不合并，避免擅自判定哪一条
才算有效」，所以数值全为 NULL 的记录也会返回。这个决定在 API 层是对的 —— 消费方可能
需要知道「这条记录存在但没填数值」。但在表格里渲染三个空行对读者没有信息量，因此在
展示侧过滤。两者不矛盾：API 保真，展示层做取舍。

### 决策4：Tc 判定方法只做部分翻译

`TC_METHOD_LABELS` 覆盖当前库中出现的取值，未命中时回退显示原始枚举值而非空白或
「未知」。补全字典需与后端枚举定义逐项对齐，属独立事项；回退原值保证信息不丢失。

### 决策5：不动 PaperEditView

它在 Issue #59 已改为正确来源，本次不碰以免影响 #59 的验收判据。代价是详情页仍有一份
自己的提取实现 —— 后续可让它也改用本模块，但那属于重构而非修 bug。

## 实施步骤

1. 新建 `lib/paperDetailView.ts`，导出 `collectPropertyRows`、`collectStructures`、
   `viewerFormat` 与两个行类型
2. `SearchPage.tsx`：移除 `'La,H'` 兜底
3. `SearchPage.tsx`：summary 加 `pre-wrap`
4. `SearchPage.tsx`：结构提取改调 `collectStructures`，物性表改渲染 `propertyRows`
5. `SearchPage.tsx`：3Dmol 格式映射改调 `viewerFormat`，消除内联三元
6. `share.tsx`：物性表改渲染 `detailPropertyRows`，新增结构预览区块
7. `vitest.config.ts` 注册 `tests/03_data_search_and_database_discovery`
8. 编写两个测试文件
9. 验证：`vitest run`、`tsc --noEmit`、重建容器、真实 API 实测

## 验证结果

| 项目 | 结果 |
|------|------|
| 提取逻辑用例 | 12 例通过（7ms，纯函数无需 DOM） |
| 探索页默认值用例 | 3 例通过 |
| 前端全量 | 104 例中 103 通过 |
| `tsc --noEmit` | 通过 |
| 产物核对 | `SearchPage-CWN2g1gA.js` 中 `La,H` 出现 0 次；`paperDetailView-CXqmR4Me.js` 已生成并被引用 |
| 真实 API | `GET /api/papers/9`：`tc_value_k: 4.2`、`I4/mmm` CIF 816 字节、summary 含 `\n`、`key_properties: []` |

**关于 NewsFeed 失败**：`tests/08_news/NewsFeed.test.tsx` 属 Issue #63 每日新闻在建代码，
本次改动前即失败，与探索页无关。

## 事故记录

**误判产物核对结果。** 首次核对 bundle 时用了 `grep -o 'La,H' ... | head -3 && echo "!! 仍存在"`，
管道让 `head` 的退出码掩盖了 `grep` 的，得到「仍存在」的错误结论。改用 `grep -c` 直接
取计数后确认为 0 次。教训：验证命令本身也要能被信任，管道中的 `&&` 判断的是最后一个
命令的退出码。

**JSX 注释位置错误。** 把 `{/* ... */}` 写进了 `{cond && (...)}` 的括号内，esbuild 报
`Expected ")" but found "sx"`。JSX 表达式容器内只能有一个表达式，注释须移到条件之外。
