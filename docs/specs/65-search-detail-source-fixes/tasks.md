# 实施任务：修复探索页与社区页三处缺陷

**输入**：[spec.md](spec.md)、[plan.md](plan.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：定位三处根因

- [x] T001 [P] 定位默认选中：`frontend/src/pages/SearchPage.tsx:125` 兜底为 `'La,H'`，
  并经 `initElements.join('')` 把 Formula 框预填为 `LaH`
- [x] T002 [P] 定位总结换行：`SearchPage.tsx:651` 用普通 `Typography`，未设 `whiteSpace`
- [x] T003 [P] 定位物性恒空：`SearchPage.tsx:662` 只判 `key_properties` 长度
- [x] T004 [P] 定位结构恒空：`SearchPage.tsx:328-337` 读 `key_properties[].structure_text`，
  该字段在 Go 侧标记 `gorm:"-"`，`keyPropertiesToDict` 也不输出
- [x] T005 查 MySQL 核实数据完好：`material_states` 1 行、`tc_results` Tc=4.2、
  `structure_models` 816 字节 CIF、`superconductor_properties` 0 行
- [x] T006 `cat -A` 确认库中 summary 含真实 `\n`，排除数据侧丢换行
- [x] T007 实测 `GET /api/papers/9`，确认 API 已完整返回三类数据，问题纯在消费侧
- [x] T008 排查波及范围：`share.tsx:577` 物性表同样只读 `key_properties`；该文件全文
  无 `StructureViewer3D` 引用，即结构预览完全缺失
- [x] T009 确认与 Issue #59 的关系：#59 修了 `PaperEditView` 的同一处错误，但探索页与
  社区页各留一份旧实现，共三处

## 阶段 2：抽取公共提取逻辑（FR-008）

- [x] T010 新建 `frontend/src/lib/paperDetailView.ts`，模块头注释说明四张来源表的分工
- [x] T011 定义 `PaperPropertyRow`、`PaperStructureItem` 两个行类型
- [x] T012 实现 `collectPropertyRows`：按 Tc → 计算参数 → 普通物性顺序汇总（FR-004）
- [x] T013 Tc 数值处理：`tc_value_k` 优先，单臂区间不补造缺失端（`≥ 200 K`）
- [x] T014 Tc 备注：`tc_method_custom` 优先于枚举翻译，未命中枚举时回退原值
- [x] T015 计算参数：λ / ωlog / μ* 各成一行，`== null` 时跳过（FR-005）
- [x] T016 普通物性：按 `material_state_id` 回查所属状态取条件
- [x] T017 实现 `collectStructures`：只遍历 `material_states[].structures[]`（FR-006）
- [x] T018 实现 `viewerFormat`：`poscar` / `vasp` → `vasp`，其余回退 `cif`
- [x] T019 全函数加 `Array.isArray` 守卫与可选链，null / 缺键均不抛错（FR-009）

## 阶段 3：用户故事 1——探索页默认不预选（P1）

- [x] T020 [US1] `SearchPage.tsx:125` 兜底改为 `''`，并注释说明默认选中会静默限定检索
  范围（FR-001、FR-002）

## 阶段 4：用户故事 2——探索页详情读取修正（P1）

- [x] T021 [US2] summary 的 `Typography` 加 `whiteSpace:'pre-wrap'`（FR-003）
- [x] ~~T021b 核心发现与社区页的同类修复~~ **移交
  [Issue #68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)**：本 Issue 只做了
  T021 一处，未先枚举范围，漏了探索页 key_finding 与社区页两处，共四处中的三处。
  完整修复、范围枚举与断言 computed style 的回归测试见
  `docs/specs/68-preserve-multiline-text/`。
- [x] T022 [US2] 结构提取改调 `collectStructures`，删除原 `key_properties` 过滤逻辑
- [x] T023 [US2] 详情渲染前计算 `propertyRows = collectPropertyRows(paperDetail)`
- [x] T024 [US2] 物性表改渲染 `propertyRows`，五列改用归一后的 `row.*` 字段
- [x] T025 [US2] 3Dmol 格式映射改调 `viewerFormat`，消除内联三元

## 阶段 5：用户故事 3——社区页同批修复（P2）

- [x] T026 [US3] `share.tsx` 引入 `collectPropertyRows`、`collectStructures`、
  `viewerFormat` 与 `StructureViewer3D`
- [x] T027 [US3] 计算 `detailPropertyRows` 与 `detailStructures`
- [x] T028 [US3] 物性表改渲染 `detailPropertyRows`，删除内联条件回查与数值分支
- [x] T029 [US3] 新增「结构预览」`details` 区块（此前该页面完全没有结构预览）（FR-007）

## 阶段 6：测试

- [x] T030 `vitest.config.ts` 注册 `tests/03_data_search_and_database_discovery/**/*.test.tsx`
- [x] T031 新建 `tests/03_data_search_and_database_discovery/paper-detail-view-sources.test.tsx`，
  载荷取自 Hg 论文真实 API 响应切片
- [x] T032 用例：`key_properties` 为空但有 Tc 时物性表非空，值为 `4.2 K`（SC-002）
- [x] T033 用例：Tc 备注含判定方法「实验测量」
- [x] T034 用例：λ / ωlog 成行，NULL 的 `μ*` 不成行；ωlog 值为 `1120 K`（SC-003）
- [x] T035 用例：普通物性仍纳入，按 `material_state_id` 回查条件
- [x] T036 用例：标签顺序为 `['Tc', '形成焓']`，Tc 在前（SC-004）
- [x] T037 用例：Tc 单臂区间为 `≥ 200 K`，双端为 `250–260 K`
- [x] T038 用例：论文为空 / null / undefined 时返回空数组不抛错（FR-009）
- [x] T039 用例：结构从 `structures[]` 提取，含空间群符号 `I4/mmm`（SC-005）
- [x] T040 反向用例：伪造 `key_properties[].structure_text` 时须返回空数组——若实现
  回退到读废弃字段，此用例会失败（FR-006）
- [x] T041 用例：空串与纯空白的结构文本被过滤
- [x] T042 用例：`viewerFormat` 五种输入的映射
- [x] T043 新建 `search-page-defaults.test.tsx`，3 个用例覆盖无参、Formula 框、显式传参
  （SC-001）
- [x] ~~T043b `multiline-text-preserved.test.tsx`~~ 随 T021b 一同移交
  [Issue #68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68)

## 阶段 7：验证

- [x] T044 提取逻辑 12 例通过（7ms）
- [x] T045 探索页默认值 3 例通过
- [x] T046 前端全量 104 例中 103 通过；唯一失败为 `tests/08_news/NewsFeed.test.tsx`
  （Issue #63 在建代码，本次改动前即失败）
- [x] T047 `tsc --noEmit` 通过（SC-007）
- [x] T048 重建 dev 前端容器
- [x] T049 产物核对：`SearchPage-CWN2g1gA.js` 中 `La,H` 出现 0 次；
  `paperDetailView-CXqmR4Me.js` 已生成并被引用
- [x] T050 真实 API 复核：Tc 4.2 K、`I4/mmm` CIF 816 字节、summary 含 `\n`（SC-008）

## 阶段 8：文档

- [x] T051 创建 GitHub Issue [#65](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/65)
- [x] T052 编写 `docs/specs/65-search-detail-source-fixes/`（spec、plan、tasks）
- [x] T053 回写 `docs/overview/03_Superconductivity_Data_Search_and_Database_Discovery/paper-and-property-results.md`

## 依赖与执行顺序

- **T001-T009**（定位）：T001-T004 可并行；T005-T008 依赖数据库与容器
- **T010-T019**（公共模块）：依赖 T003-T007 确认字段路径
- **T020**（默认选中）：独立，不依赖公共模块
- **T021-T025**（探索页）：T022-T025 依赖 T010-T019
- **T026-T029**（社区页）：依赖 T010-T019
- **T030-T043**（测试）：依赖 T010-T029
- **T044-T050**（验证）：依赖全部实现与测试
- **T051-T053**（文档）：依赖验证完成

**关键路径**：T004→T007→T010→T012→T017→T024→T031→T040→T046→T049→T050

## 需求覆盖

| 来源 | 任务 | 验证 |
|------|------|------|
| FR-001、FR-002（默认不预选） | T020 | T043（3 例） |
| FR-003（探索页总结换行） | T021 | 库中 `\n` 已确认 + 人工核对；其余三处见 [#68](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/68) |
| FR-004（三类来源汇总） | T012-T016、T024 | T032、T035、T036 |
| FR-005（NULL 不成行） | T015 | T034 |
| FR-006（结构来源） | T017、T022 | T039、T040（反向用例） |
| FR-007（社区页同步） | T026-T029 | tsc + 人工核对 |
| FR-008（逻辑收敛单点） | T010-T019 | 代码审查：两页面共用同一模块 |
| FR-009（异常输入不抛错） | T019 | T038、T041 |
| SC-001 | T043 | 通过 |
| SC-002 | T032 | 通过 |
| SC-003 | T034 | 通过 |
| SC-004 | T036 | 通过 |
| SC-005 | T039、T040 | 通过 |
| SC-006 | T021 | 库中换行已确认 |
| SC-007 | T046、T047 | 通过 |
| SC-008 | T050 | 通过 |

## 遗留事项

- **PaperEditView 未改用公共模块**：详情页在 Issue #59 已修为正确来源，本次不动它以免
  影响 #59 验收判据。它仍保留自己的一份提取实现，后续可统一（属重构非修 bug）。
- **结果表格的 Tc 列**：`SearchPage:282` 处结果列表展开 `key_properties` 取临界温度，
  属搜索结果聚合链路（与详情读取不同路径），本次未触碰，需另行核实其正确性。
- **Tc 方法枚举字典不完整**：`TC_METHOD_LABELS` 只覆盖当前库中取值，未命中回退原值。
  补全需与后端枚举定义逐项对齐。
- **ErrorBoundary 缺失**：见 Issue #64 遗留事项。
