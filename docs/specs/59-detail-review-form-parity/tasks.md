# 实施任务：只读详情页与校对表单一致

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[contracts/detail-view-fields.md](contracts/detail-view-fields.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认修复前基线，使「修复后全绿」有对照意义。

- [ ] T001 记录前端基线：`cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit`（预期 8 文件 65 用例全过、`tsc` 无输出）

## 阶段 2：用户故事 1——详情页字段集与校对页一致（P1，MVP）

**目标**：材料状态展示的字段与校对页卡片逐项对应，无缺项、无多余项。

**独立验收**：paper 4 详情页显示晶系 `cubic`、空间群 `Fm-3m`/225、压强 250 GPa 与原文 `above 200 GPa`、Tc 274 K、λ=2.56、μ*=0.1、物性名 `thermodynamic stability` 与解析值 200，且无「最小值」「最大值」空字段。

### 测试

- [ ] T002 [US1] `tests/01_decentralized_uploading/paper-detail-form-parity.test.tsx`（新建）：构造含完整材料状态的论文对象渲染 `PaperEditView`，以 [contracts/detail-view-fields.md](contracts/detail-view-fields.md) 分类区清单断言 9 项均渲染（FR-001、FR-005）
- [ ] T003 [US1] 同文件：断言单臂区间只显示存在的一侧——`pressure_min_gpa=200`、`pressure_max_gpa=null` 时显示下限与原文 `above 200 GPa`，不出现上限、不把 null 渲染为 0（FR-002）
- [ ] T004 [US1] 同文件：断言 Tc 数值/方法与 λ/ωlog/μ* 可见；**关键用例**——注入 2 条计算上下文（首条全 NULL、次条含 λ=2.56/μ*=0.1），断言 λ 可见，防止实现取首条（FR-003）
- [ ] T005 [US1] 同文件：断言物性显示名称、原始值、解析值、单位，且页面**不含**「最小值」「最大值」文本（FR-004）

### 实施

- [ ] T006 [US1] `frontend/src/components/PaperEditView.tsx`：重写材料状态区为按 [contracts/detail-view-fields.md](contracts/detail-view-fields.md) 组织的只读展示——分类区 9 项、压强区（值/原文/下限/上限，单臂不补造）、Tc 区（`tc_results[]` + 材料状态级 `calculation_contexts[]` 全部条目）、普通物性区（名称/原始值/解析值/单位/条件说明，移除 min/max 两框）

## 阶段 3：用户故事 2——字段名称与内容语义对应（P1）

**目标**：标签与内容来源一致；研究方法可读展示。

**独立验收**：详情页含「分类理由」、不含标为「研究理由」的内容；研究方法逐项可读，无 JSON 原文。

### 测试

- [ ] T007 [US2] 同测试文件：断言页面含「分类理由」且不含「研究理由」（FR-006、FR-007）
- [ ] T008 [US2] 同测试文件：断言研究方法逐项独立可见，且页面文本不含 `["` 片段；覆盖 `methodology` 为空与非数组两个边界（FR-008）

### 实施

- [ ] T009 [US2] `frontend/src/components/PaperEditView.tsx`：`rationale` 标签由「研究理由 (rationale)」改为「分类理由」；`methodology` 由 `JSON.stringify` 改为逐项列表展示（与校对页「每行一项」形态一致）；关键词同样按列表展示（与 T006 同文件，串行）

## 阶段 4：用户故事 3——结构预览同源与只读化（P2）

**目标**：结构预览取自材料状态下的 `structures`；组件成为纯只读，无死代码。

**独立验收**：无结构数据时显示空态不报错；组件内无可编辑控件与增删改函数。

### 测试

- [ ] T010 [US3] 同测试文件：覆盖有结构数据（注入 `material_states[].structures[]`）与无结构数据两个分支，后者断言空态文案存在且不抛错（FR-009）
- [ ] T011 [US3] 同测试文件：断言页面不存在可编辑输入框（无非只读 `input`/`textarea`），无「添加物性」「删除」按钮（FR-010）
- [ ] T012 [US3] 同测试文件：覆盖无材料状态的空态分支，断言不渲染空白卡片骨架（边界场景）

### 实施

- [ ] T013 [US3] `frontend/src/components/PaperEditView.tsx`：删除 `editKps` 状态、`updateKp`/`addKp`/`deleteKp` 三个函数、全部 `onChange`、「添加物性」与删除按钮，以及 `fieldset disabled` 整体禁用包裹（改为本就只读的展示形态，不留「移除 disabled 即可编辑但存不下」的陷阱）；结构预览确认取自 `material_states[].structures[]`（与 T006、T009 同文件，串行）

## 最终阶段：完善与跨故事事项

- [ ] T014 前端全量回归：`cd /home/mayuan/code/SC-Wiki/frontend && npm run test:upload-ui && npx tsc --noEmit`（SC-006）
- [ ] T015 重建并部署前端镜像：`cd /home/mayuan/work/SC-Wiki-docker && docker compose -f dev.yaml build frontend && docker compose -f dev.yaml up -d frontend`；核对运行制品含本次改动
- [ ] T016 按 [quickstart.md](quickstart.md) 场景 1、2、3、4 人工验收：分类字段、压强单臂区间、Tc 与计算上下文、物性无空 min/max（SC-001、SC-002、SC-003）
- [ ] T017 按 [quickstart.md](quickstart.md) 场景 5 人工验收：分类理由标签正确、无「研究理由」、研究方法可读列表（SC-003、SC-004）
- [ ] T018 按 [quickstart.md](quickstart.md) 场景 6、7 人工验收：结构空态、只读性、返回入口与匿名权限无回归（SC-005、SC-006）
- [ ] T019 使用 `big-project-overview-maintainer` 将「详情页与校对表单的字段集一致」「分类理由与研究理由的字段语义」回写 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/pdf-ingestion.md`，并在相关变更记录追加 Issue #59 链接
- [ ] T020 交由 `big-project-issue-manager` 回写 Spec 链接并在全部门槛满足后关闭 Issue #59

## 依赖与执行顺序

- T001 无依赖。
- **三个用户故事都改同一个文件 `PaperEditView.tsx`，实施任务 T006 → T009 → T013 必须串行**。故事 3 的死代码清理不能独立于故事 1：移除编辑控件与重写字段展示是同一处代码的同一次改写，拆开会产生中间不可编译状态。
- 测试任务 T002–T005、T007、T008、T010–T012 同在一个新建测试文件，可连续编写，但只能在对应实施任务完成后才通过。
- T014 依赖全部实施任务；T015 依赖 T014；T016–T018 依赖 T015；T019 依赖 T016–T018 全部通过；T020 依赖 T019。
- 无 `[P]` 并行任务：本 Feature 改动集中在单文件。

## 需求覆盖

| 来源 | 任务 | 说明 |
|---|---|---|
| FR-001 / US1 | T002、T006、T016 | 分类区 9 项 |
| FR-002 / US1 | T003、T006、T016 | 压强单臂区间不补造 |
| FR-003 / US1 | T004、T006、T016 | Tc 与全部计算上下文 |
| FR-004 / US1 | T005、T006、T016 | 物性字段集，移除空 min/max |
| FR-005 / US1 | T002、T005、T006 | 字段集无多余项 |
| FR-006 / US2 | T007、T009、T017 | 分类理由标签 |
| FR-007 / US2 | T007、T009、T017 | 无「研究理由」错配 |
| FR-008 / US2 | T008、T009、T017 | 研究方法可读列表 |
| FR-009 / US3 | T010、T013、T018 | 结构预览同源与空态 |
| FR-010 / US3 | T011、T013、T018 | 只读化与死代码清理 |
| FR-011 / 全部 | T014、T018 | 入口与权限无回归 |
| SC-001 | T002、T005、T016 | 字段集逐项一致 |
| SC-002 | T003、T004、T016 | paper 4 的 8 项实测值可见 |
| SC-003 | T005、T007、T016、T017 | 无空 min/max、无「研究理由」 |
| SC-004 | T008、T017 | 无 JSON 原文片段 |
| SC-005 | T010、T011、T018 | 空态与只读性 |
| SC-006 | T014 | 前端全量 + `tsc` |
| 边界：无材料状态 | T012 | 空态不渲染骨架 |
| 边界：多条计算上下文 | T004 | 含全 NULL 记录一并展示 |
| 边界：研究方法为空/非数组 | T008 | 不抛错、不渲染空容器 |

## MVP 与增量策略

1. 完成 T001 基线记录。
2. 连续完成 T006 → T009 → T013 三次同文件改写至可编译，再运行测试验证。
3. 三个故事在验收层面独立：US1 由材料状态字段证明，US2 由标签与形态证明，US3 由空态与只读性证明，可分别验收。
