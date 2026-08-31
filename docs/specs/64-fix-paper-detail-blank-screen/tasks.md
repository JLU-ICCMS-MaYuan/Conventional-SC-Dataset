# 实施任务：修复论文详情页整页白屏

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：定位根因

**目的**：区分白屏是权限、路由还是渲染问题，取到真实载荷。

- [x] T001 [P] 读 `frontend/src/App.tsx`、`LazyRoutes.tsx`，确认 `/papers/:id` 路由存在且
  有 `NotFoundPage` 兜底 —— 排除路由未匹配
- [x] T002 [P] `curl` 实测 `/papers/9` 返回 200 + `index.html`，静态资源 200 —— 排除 nginx
  与 SPA 回退问题
- [x] T003 [P] 读 `frontend/src/pages/PaperDetailPage.tsx`，确认已有 403/404/400 四路分流，
  推断异常在下游展示组件
- [x] T004 [P] 全仓 `rg "ErrorBoundary|componentDidCatch"` —— 无结果，确认叶子异常会拖垮整树，
  解释「连顶栏侧栏都消失」
- [x] T005 查 MySQL 确认 `papers` id=9 存在（`pending`、`uploaded_by_user_id=2`），
  排除数据缺失
- [x] T006 查 `papers` 表 `keywords_tags` / `methodology` / `authors` 实际存储形态 ——
  确认是 JSON 文本
- [x] T007 用真实载荷写一次性复现测试，取得确切异常：
  `TypeError: paper.keywords_tags.map is not a function` @ `PaperEditView.tsx:389`
- [x] T008 用 id=2 的合法 token 实测 `GET /api/papers/9`，确认三字段类型均为 `str`

## 阶段 2：修复渲染崩溃（P1）

**目标**：三个 JSON 文本列字段在数组与字符串两种形态下都能正常渲染。

**独立验收**：`keywords_tags` 为 JSON 字符串的论文，详情页完整渲染不白屏。

- [x] T009 [US1] 在 `frontend/src/components/PaperEditView.tsx` 新增组件级
  `toTextList(value: unknown): string[]`，覆盖数组 / JSON 字符串 / null / 非法 JSON /
  非数组 JSON 五种输入（FR-004、FR-005）
- [x] T010 [US1] `methodologyList` 改走 `toTextList` —— 原实现 `if (Array.isArray(raw))`
  之外直接 `return []`，遇字符串静默丢数据（FR-002）
- [x] T011 [US1] 新增 `keywordList = toTextList(paper?.keywords_tags)`，侧栏关键词区改用
  该变量，移除 `PaperEditView.tsx:389` 的 `paper.keywords_tags.map` 直接调用（FR-001）
- [x] T012 [US1] `setEditAuthors` 改为 `toTextList(data.authors).join('、')`，替换原
  `JSON.stringify(data.authors || [])`（FR-003）

## 阶段 3：回归测试

**目的**：把后端真实载荷形态固化进用例，防止同类回归。

- [x] T013 [US1] 在 `tests/01_decentralized_uploading/paper-detail-route.test.tsx` 新增
  describe「详情页对 JSON 文本列字段的容错」，构造 `jsonStringPaper` fixture，三字段
  全用 JSON 字符串（FR-006）
- [x] T014 [US1] 用例「keywords_tags 为 JSON 字符串时正常渲染详情而非白屏」：断言
  「论文详情」标题与「超导」「汞」「液氦」三标签同时可见（SC-001）
- [x] T015 [US1] 用例「methodology 为 JSON 字符串时逐项可读展示」：断言 `• 电阻测量`、
  `• 低温实验` 可见（SC-002）
- [x] T016 [US1] 用例「authors 为 JSON 字符串时展示人名而非 JSON 原文」：断言人名可见，
  且 `document.body.textContent` 不含 `["` 与 `"]`（SC-003）
- [x] T017 删除阶段 1 的一次性复现测试文件，不留临时产物

## 阶段 4：验证

- [x] T018 详情页专项：`paper-detail-route.test.tsx` + `paper-detail-form-parity.test.tsx`
  共 26 例通过，证明数组形态行为未回退（SC-004）
- [x] T019 前端全量：89 例中 88 通过。唯一失败为 `tests/08_news/NewsFeed.test.tsx`，
  属 Issue #63 在建代码，grep 确认不引用 `PaperEditView` 与 `papers/`，与本次无关
- [x] T020 `tsc --noEmit` 通过（SC-006）
- [x] T021 重建 dev 前端容器 `docker compose -f dev.yaml up -d --build frontend`，
  确认新 bundle `index-BYNGd8N8.js` 生效
- [x] T022 真实环境实测：`/papers/9` 返回 200、匿名 `GET /api/papers/9` 仍正确返回 403
  （权限逻辑未受影响）、带 token 返回 200（SC-005）
- [x] T023 清理临时文件（`/tmp/p9.json`、`/tmp/repro.test.tsx`）

## 阶段 5：文档

- [x] T024 创建 GitHub Issue [#64](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/64)，
  记录现象、根因链路、白屏放大机制与测试盲区
- [x] T025 编写 `docs/specs/64-fix-paper-detail-blank-screen/`（spec、plan、tasks）
- [x] T026 回写 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-ingestion.md`：
  详情页对 JSON 文本列字段的容错行为 + 变更记录条目

## 依赖与执行顺序

- **T001-T008**（定位）：T001-T004 可并行；T005-T008 依赖数据库与容器可用
- **T009**（归一函数）：依赖 T006-T008 确认字段形态
- **T010-T012**（三字段改造）：依赖 T009
- **T013-T017**（测试）：依赖 T009-T012
- **T018-T023**（验证）：依赖 T010-T017
- **T024-T026**（文档）：依赖验证完成

**关键路径**：T006→T007→T009→T011→T014→T018→T021→T022

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001（keywords_tags 容错） | T009、T011 | T014 用例 |
| FR-002（methodology 容错） | T009、T010 | T015 用例 |
| FR-003（authors 容错与可读展示） | T009、T012 | T016 用例 |
| FR-004（归一逻辑单点） | T009 | 代码审查：三处共用一个函数 |
| FR-005（异常输入不抛错） | T009 | T018 中既有「非数组不抛错」用例 |
| FR-006（fixture 用真实形态） | T013 | 用例本身 |
| SC-001 | T014 | 通过 |
| SC-002 | T015 | 通过 |
| SC-003 | T016 | 通过 |
| SC-004 | T018 | 26 例通过 |
| SC-005 | T022 | API 200 + 页面 200 |
| SC-006 | T020 | tsc 通过 |

## 遗留事项

- **ErrorBoundary 缺失**：全仓无 `componentDidCatch`，任何页面的渲染异常都会导致整站
  白屏，排查成本极高。本次不处理（见 Spec 范围外事项），建议单独立项。
- **其他页面的解析重复**：`SearchPage.tsx:707`、`share.tsx:632` 各有一份内联
  `try/JSON.parse/catch` 处理 `methodology`。当前不崩溃，但形态上与 `toTextList` 重复。
  若出现第四处，应抽取到 `frontend/src/lib/`。
- **字段形态治理**：`keywords_tags` / `methodology` / `authors` 在后端为 JSON 文本列而非
  结构化数组，属历史设计。统一为结构化类型需跨 Go 模型、Python 写入侧与全部消费方，
  值得单独立项。
