# 实施任务：上传校对页布局重构与材料状态卡片完善

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/draft-and-api.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：显式声明新依赖。

- [x] T001 在 `requirements.txt` 与 `docker/requirements.txt` 各加一行 `spglib>=2.5`（与 pymatgen 兼容的版本下限），并用 `pip install spglib` 验证当前环境可导入

## 阶段 2：基础能力（后端与契约）

**目的**：全部用户故事共用的后端能力，阻断前端故事任务。

- [x] T002 [P] 新建 `backend/services/space_groups.py`：遍历 spglib hall 1–530 生成 230 条符号↔群号只读映射，提供 `all_space_groups()` 与 `lookup_number(symbol)`（忽略空白）；新建 `backend/tests/test_space_groups.py` 抽查 Fm-3m→225、I4/mmm→139、P6_3/mmc→194、Fd-3m→227 且总数 230
- [x] T003 [P] 新建 `backend/db_helpers.py` 内函数 `extract_formula_elements_loose()`（剔除括号内容/单位后缀后扫描合法元素符号，见 research D3），在 `backend/tests/test_classification_catalog.py` 追加 `LaHx (x = 1–12) 150 GPa`→2、`LaHx`→2 用例
- [x] T004 新建迁移 `alembic/versions/20260826_0014_superconductor_kind_tc_method.py`（仿照 `20260825_0012` 裸 op 模式）：material_states 加 `superconductor_kind` 列+CHECK；tc_results 重建 `ck_tc_results_method`（+scdft/other）并加 `tc_method_custom` 列；同步改 `backend/models.py`（MaterialState、TcResult）；执行 `alembic upgrade head` 验证
- [x] T005 改 `backend/ingest/upload_jobs.py`：① element_count 锁定语义（D2）+宽松解析回退（T003）；② `SPACE_GROUP_NUMBERS` 硬编码替换为 T002 全表查询；③ `superconductor_kind` 白名单规范化；④ `tc_results[].calculation_context` 数值化；⑤ `tc_method` 合法集扩展与 `tc_method_custom` 保留规则；⑥ SUMMARY prompt 增加 superconductor_kind、tc_method 新枚举、energy above hull（thermodynamically stable→0）说明；在 `backend/tests/test_upload_jobs.py` 追加对应用例
- [x] T006 改 `backend/ingest/scientific_drafts.py`：element_count 草稿值优先（:204）；常规 Tc 逐条创建 CalculationContext（:315-385，无专属参数时回退共享）；`tc_method_custom` 入库；在 `backend/tests/test_scientific_drafts.py` 追加两条 Tc 独立 context 的集成用例
- [x] T007 改 `backend/api/rag.py`：`_create_pending_paper` 前汇总 research_materials（:974-996）；`_validate_draft` 放宽（:208-308，汇总值可满足）；新增 `GET /api/rag/space-groups`；在 `backend/tests/test_upload_workflow.py` 追加校验放宽与接口用例
- [x] T008 [P] 改 `goserver/models/models.go`（MaterialState.SuperconductorKind、TcResult.TcMethodCustom）与 `goserver/handlers/papers.go`（materialStatesToDict 与 tc_results 字典输出新字段及条目级 λ/ωlog/μ\*）；`go build ./...` 通过
- [x] T009 改 `frontend/src/lib/paperProcessing.ts`：DraftMaterialState 加 `superconductor_kind`、`element_count_locked`；DraftTcResult 加 `calculation_context`、`tc_method_custom`

## 阶段 3：用户故事 1——对称布局与材料状态折叠（P1，MVP）

**目标**：校对页无研究材料输入框，关键词/研究方法并排等高，卡片可折叠。

**独立验收**：quickstart 场景 1 全部步骤通过。

- [x] T010 [US1] 改 `frontend/src/components/UploadTaskEditor.tsx`（:592-609）：删除「研究材料」TextField 及其 AI 建议块；「关键词」「研究方法」改为 `md: 1fr 1fr` 两列且统一 `minRows` 等高
- [x] T011 [US1] 同文件（:656-843）：新增会话级 `collapsed` state、卡片头点击折叠（MUI Collapse）、「材料状态与计算条件」标题行右侧「全部折叠/全部展开」按钮；默认规则 ≤2 张全展开、否则仅首张展开
- [x] T012 [US1] 新建 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx`：无研究材料输入框、关键词/研究方法并排、折叠按钮与单卡折叠行为

## 阶段 4：用户故事 2——元素种类数可编辑（P1，MVP）

**目标**：输入框可编辑、手动锁定、非法值即时提示。

**独立验收**：quickstart 场景 2。

- [x] T013 [US2] 改 `frontend/src/components/UploadTaskEditor.tsx`（:690-695）：去除 readOnly；onChange 校验整数 1–118 并置 `element_count_locked=true`；helperText 改为「自动计算，可手动修改」
- [x] T014 [US2] 更新 `tests/01_decentralized_uploading/upload-task-editor-classification.test.tsx`：编辑元素数→保存 payload 含锁定标志与新值

## 阶段 5：用户故事 3——超导类型与条件化 Tc（P1，MVP）

**目标**：超导类型选择驱动 Tc 条目字段组。

**独立验收**：quickstart 场景 3。

- [x] T015 [US3] 改 `frontend/src/components/UploadTaskEditor.tsx`：材料状态新增超导类型 Select（常规 (BCS)/非常规/未知，默认未知）；「添加 Tc」按类型生成字段组（常规：λ、ωlog、μ\*、Tc 值、方法下拉 5+其他与自定义文本框，旧状态级值预填一次；非常规/未知：仅 Tc 值）；移除状态级 λ/ωlog 输入框（:758-763）；Tc 行移除「原始值」输入（:799）
- [x] T016 [US3] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：三种超导类型下添加 Tc 的字段差异、方法「其他」自定义文本、切换类型数据保留

## 阶段 6：用户故事 4——空间群标准表（P2）

**目标**：230 条可搜索下拉 + 符号自动带群号。

**独立验收**：quickstart 场景 4。

- [x] T017 [US4] 改 `frontend/src/components/UploadTaskEditor.tsx`（:753-757）：空间群符号改为 MUI Autocomplete freeSolo（选项来自 `GET /api/rag/space-groups`，选中自动填群号，自由输入不阻断）
- [x] T018 [US4] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：选中 Fm-3m 带出 225；自由输入可保存

## 阶段 7：用户故事 5——文案、结构家族说明与模块顺序（P2）

**目标**：压强文案、主结构家族说明、附件置底。

**独立验收**：quickstart 场景 5。

- [x] T019 [US5] 改 `frontend/src/components/UploadTaskEditor.tsx`：「压力 (GPa)」→「压强 (GPa)」（:751）；主结构家族 Select 加说明 helperText（:735-750）；结构附件块（:771-781）移至 Tc 与普通物性之后
- [x] T020 [US5] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：压强文案与结构附件渲染顺序断言

## 阶段 8：用户故事 6——energy above hull 预置（P2）

**目标**：一键添加预置物性，不重复。

**独立验收**：quickstart 场景 6 步骤 2。

- [x] T021 [US6] 改 `frontend/src/components/UploadTaskEditor.tsx`（:814-839 附近）：「添加普通物性」旁加「＋ energy above hull」按钮（name=energy above hull、unit=eV/atom、值为空；已存在同名条目时禁用）
- [x] T022 [US6] 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加：点击生成预置条目、重复点击被禁用

## 最终阶段：完善与跨故事事项

- [x] T023 运行 `python -m pytest backend/tests/ -q`、`cd frontend && npm run test:upload-ui`、`npx tsc --noEmit` 与 `cd goserver && go build ./... && go test ./...`，全部通过；修复波及的既有测试
- [ ] T024 按 quickstart.md 场景 1–7 手工验证并记录结果（含 alembic upgrade head 后 fresh 启动）
- [ ] T025 用 `gh issue edit 52 --body` 回写 Spec 链接（docs/specs/52-upload-review-material-state/）；按 AGENTS.md 提交规范 git commit（仅暂存本 Feature 文件）

## 依赖与执行顺序

- T001 先行；T002/T003/T008 互不依赖可并行；T004 独立（models.py 与迁移）。
- T005 依赖 T002、T003；T006、T007 依赖 T005 的草稿契约；T009 依赖 data-model，独立于后端代码。
- 前端故事任务（T010–T022）全部改同一文件 `UploadTaskEditor.tsx`，必须串行；测试任务紧随其后。
- T023–T025 串行收尾。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001/002 / US1 | T007、T010、T012 | 后端汇总+前端布局 |
| FR-003 / US1 | T011、T012 | 折叠交互 |
| FR-004/005 / US2 | T003、T005、T006、T013、T014 | 锁定语义+宽松解析+可编辑 |
| FR-006 / US5 | T019、T020 | 压强文案 |
| FR-007/008 / US4 | T001、T002、T005、T007、T017、T018 | spglib 全表+下拉 |
| FR-009~012 / US3 | T004、T005、T006、T008、T015、T016 | 超导类型+条件化 Tc |
| FR-013/014 / US5 | T019、T020 | 附件置底+主家族说明 |
| FR-015 / US6 | T005（prompt）、T021、T022 | AI 提取+快捷添加 |
| SC-006 | T023、T024 | 全量回归 |

## MVP 与增量策略

1. 完成 T001–T009 基础能力。
2. 实施 US1（T010–T012）、US2（T013–T014）、US3（T015–T016）即达 MVP：布局、元素数、超导类型 Tc。
3. 依次叠加 US4、US5、US6；每个故事测试通过后保持可提交状态。
