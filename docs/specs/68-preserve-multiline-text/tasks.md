# 实施任务：修复探索页与社区页多行文本丢失换行

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：区分数据侧与渲染侧

**目的**：先确认换行是在存储、传输还是渲染环节丢失，避免修错层。

- [x] T001 `cat -A` 查库中 `papers.key_finding`（id=9），确认含真实 `\n`
- [x] T002 实测 `GET /api/papers/9`，用 `chr(10) in kf` 与 `'\\n' in kf` 区分「真实换行」
  与「`\n` 字面量」——确认是真实换行，数据与传输均无问题
- [x] T003 定位渲染缺陷：`frontend/src/pages/SearchPage.tsx` 核心发现的 `Typography`
  未设 `whiteSpace`，HTML 默认折叠连续空白符

## 阶段 2：枚举同类字段的全部渲染点

**目的**：#65 与 #59 两次遗漏都源于「逐处修」，本阶段先把范围列全再动手。

- [x] T004 `rg 'key_finding'` 全仓，列出所有渲染点（排除测试与录入控件）
- [x] T005 排查两个检索页的全部多行字段：`summary`、`key_finding`、`abstract`、
  `rationale`、`review_comment`、`row.note`
- [x] T006 得出待修清单共四处：探索页 `summary`（#65 已修）/ `key_finding`，
  社区页 `summary` / `key_finding`
- [x] T007 确认无需改动的部分：`PaperEditView` 的 abstract / summary / key_finding /
  rationale 四处一直有 `pre-wrap`；两页面表格 `row.note` 为单行短文本；`abstract` 与
  `rationale` 当前不在检索页渲染

## 阶段 3：用户故事 1——保留换行（P1）

- [x] T008 [US1] `SearchPage.tsx` 核心发现的 `Typography` 加 `whiteSpace:'pre-wrap'`
  （FR-001）
- [x] T009 [US1] `share.tsx` 论文总结的 `Typography` 加 `whiteSpace:'pre-wrap'`
- [x] T010 [US1] `share.tsx` 核心发现的 `Typography` 加 `whiteSpace:'pre-wrap'`，
  并确认其 `JSON.parse` 兜底分支不影响换行
- [x] T011 [US1] 四处均只加 CSS，不对字段值做 trim 或替换（FR-003）

## 阶段 4：测试

- [x] T012 新建 `tests/03_data_search_and_database_discovery/multiline-text-preserved.test.tsx`，
  载荷取自 Hg 论文真实字段形态
- [x] T013 用例：探索页论文总结的 computed `white-space` 为 `pre-wrap`（SC-002）
- [x] T014 用例：探索页核心发现的 computed `white-space` 为 `pre-wrap`（SC-001）
- [x] T015 用例：DOM 文本含 `\n`，且不含「突变 2.」这类换行被替换为空格的痕迹（FR-003）
- [x] T016 解决 Testing Library 的空白归一化：`getByText` 默认归一化空白符导致多行文本
  匹配不到，传 `normalizer: value => value` 关掉
- [x] T017 反向验证：临时移除 `pre-wrap` 重跑，确认 2 个用例失败而非恒真通过；随后恢复
  （SC-004）

## 阶段 5：验证

- [x] T018 多行文本用例 3 例通过
- [x] T019 `tsc --noEmit` 通过（SC-005）
- [x] T020 前端全量 107 例中 106 通过；唯一失败为 `tests/08_news/NewsFeed.test.tsx`
  （Issue #63 在建代码，本次改动前即失败）
- [x] T021 重建 dev 前端容器
- [x] T022 产物核对：`SearchPage-CPpRNREo.js` 与 `share-*.js` 两个 bundle 各含 2 处
  `pre-wrap`（summary + key_finding）（SC-003）

## 阶段 6：文档

- [x] T023 创建 GitHub Issue [#68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)，
  记录现象、根因、四处波及范围，以及与 #65 / #59 的遗漏关系
- [x] T024 编写 `docs/specs/68-preserve-multiline-text/`（spec、plan、tasks）
- [x] T025 回写 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`

## 依赖与执行顺序

- **T001-T003**（分层定位）：必须最先做，否则可能修错层
- **T004-T007**（枚举范围）：依赖 T003；必须在动手前完成，这是本次流程的关键改进
- **T008-T011**（实施）：依赖 T006 的清单
- **T012-T017**（测试）：依赖 T008-T011；T017 依赖 T013-T016
- **T018-T022**（验证）：依赖全部实现与测试
- **T023-T025**（文档）：依赖验证完成

**关键路径**：T001→T002→T003→T004→T006→T008→T013→T017→T020→T022

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001（四处 pre-wrap） | T008-T010 | T013、T014 + T022 产物核对 |
| FR-002（与详情页一致） | T007 | 代码审查 |
| FR-003（不改写内容） | T011 | T015 |
| FR-004（测试可捕获缺陷） | T012-T016 | T017 反向验证 |
| SC-001 | T014 | 通过 |
| SC-002 | T013 | 通过 |
| SC-003 | T022 | 两 bundle 各 2 处 |
| SC-004 | T017 | 移除后 2 例失败 |
| SC-005 | T019、T020 | 通过 |
| SC-006 | T001、T002 | 库与 API 均含真实换行 |

## 遗留事项

- **abstract 与 rationale 未在检索页展示**：当前无从丢失换行；若日后新增展示，须一并设
  `pre-wrap`。已在 Spec 范围外事项留档。
- **不做 Markdown 渲染**：保留换行已满足可读性；Markdown 会改变内容语义（`1.` 被重排为
  有序列表、特殊字符被吃掉），属独立议题。
- **同类遗漏的流程改进未固化**：本次通过「先枚举范围再动手 + 断言样式的测试」避免了逐处
  修，但这只是本 Issue 的做法，未形成对其他多页面重复代码的普遍约束。
