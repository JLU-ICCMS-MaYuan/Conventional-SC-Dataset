# 实施任务：未分配结构候选的分配与确认交互

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认共享组件与候选链路就位，记录基线。

- [x] T001 确认 #76 已落地的 `frontend/src/components/MaterialStatesEditor.tsx` 存在且已暴露 `structureCandidates` / `onStructureCandidatesChange` props（未就位则本 Feature 阻塞）
- [x] T002 确认 `backend/ingest/scientific_drafts.py::_confirmed_candidates_by_state` 契约（`material_states[N]` + confirmed → structure_models），后端零改动前提
- [x] T003 执行 `scripts/run-tests.sh frontend` 记录基线，确认 `tests/07_researcher_community_forum/news-feed.test.tsx` 既有失败不计入回归

## 阶段 2：用户故事 1——上传校对页未分配候选确认（P1，MVP）

**目标**：随任务上传的结构附件可被分配确认并落库。

**独立验收**：带 VASP 附件的任务解析后，校对页出现未分配候选区，分配确认后提交落库。

### 测试

- [x] T004 [P] [US1] 在 `tests/01_decentralized_uploading/material-states-editor.test.tsx` 新增测试：传入含 `unassigned:*` 候选时渲染未分配区（文件名、校验状态可见）（FR-001）
- [x] T005 [P] [US1] 在同一文件新增测试：选择材料状态并「采用」后 `onStructureCandidatesChange` 收到更新候选（`material_state_ref=material_states[0]`、`confirmation/status=confirmed`）（FR-002、FR-006）
- [x] T006 [P] [US1] 在同一文件新增测试：`states` 为空时采用禁用且显示「先创建材料状态」提示（FR-003）
- [x] T007 [P] [US1] 在同一文件新增测试：`blocked` 候选采用禁用且显示校验失败原因（FR-004）
- [x] T008 [US1] 在同一文件新增测试：排除后候选 `confirmation=excluded` 且从未分配区消失（FR-005、R4）
- [x] T009 [US1] 在同一文件新增测试：`readOnly` 下不渲染未分配区（FR-009）
- [x] T010 [P] [US1] 在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 或新增文件新增测试：上传任务草稿含 unassigned 候选时，校对页可见并可分配确认（FR-001、SC-001 前端部分）

### 实施

- [x] T011 [US1] 修改 `frontend/src/components/MaterialStatesEditor.tsx`：新增未分配候选区（`unassignedCandidates` 过滤、文件名/状态展示、目标状态下拉、采用/排除按钮、空材料状态提示、readOnly 隐藏）（FR-001–FR-006、FR-009）
- [x] T012 [US1] 修改 `frontend/src/i18n/{zh,en}/upload.ts`：新增未分配候选区文案键（标题、目标标签、需先创建材料状态、校验失败提示；采用/排除复用既有键或新增）（FR-011）

## 阶段 3：用户故事 2——管理端共用（P2）

**目标**：管理端编辑弹窗出现同一未分配候选区并可确认。

**独立验收**：管理端编辑弹窗可见未分配候选区，分配确认后保存随 C1 提交。

### 测试

- [x] T013 [P] [US2] 在 `tests/02_identity_governance/admin-scientific-data-edit.test.tsx` 新增测试：编辑弹窗传入含 unassigned 候选时可见未分配区，分配确认后保存的 C1 body `structure_candidates` 含该候选（FR-008、SC-003）

### 实施

- [x] T014 [US2] 确认 `frontend/src/pages/AdminPage.tsx` 无需改动（`structureCandidates`/`onStructureCandidatesChange` 已接线，未分配区随共享组件生效）；若接线缺失则补齐（FR-008）

## 阶段 4：存量数据修复（P2）

**目标**：`papers.id=9` 的 Hg 结构恢复，详情页 3D 展示。

**独立验收**：`papers.id=9` 详情页材料状态结构区展示 3D 结构。

- [x] T015 [P] [US3] 用 `build_structure_candidate` 处理磁盘 `Hg-R-3m.vasp`，取 conventional CIF 写 `structure_models`（`paper_id=9, paper_revision=2, material_state_id=51`），核对详情接口 `GET /api/admin/papers/9` 的 `material_states[].structures` 非空（FR-010、SC-004、R3）
- [x] T016 [US3] 一次性修复脚本用后即删，代码库无残留（R3、#74 FR-017 先例）

## 最终阶段：完善与跨故事事项

- [x] T017 执行 `scripts/run-tests.sh frontend`、`go`、`backend`，与 T003 基线比对确认无新增失败（SC-005）
- [x] T018 执行 `cd frontend && npm run build`，确认 `tsc -b` 无类型错误
- [x] T019 按 [quickstart.md](quickstart.md) 场景 1–4 手工走查（上传带结构任务 → 分配确认 → 提交 → 详情 3D；管理端编辑确认；papers.id=9 恢复）
- [x] T020 更新 Issue #77 正文：实现完成结论与验证结果，使 Issue 与 Spec 一致

## 依赖与执行顺序

- **阶段 1** 阻断全部；T001、T002 是硬阻塞（共享组件与候选契约未就位则不得开始）。
- **阶段 2** 依赖阶段 1；T011 阻断 T012（字典键先存在），T004–T010 与 T011 可并行编写（测试先于实现）。
- **阶段 3** 依赖阶段 2 的 T011（共享组件生效）。
- **阶段 4** 独立于阶段 2/3，可并行（数据修复不依赖前端交互）。
- **最终阶段** 依赖全部前置。

**串行触点（同文件任务必须串行）**：

| 文件 | 涉及任务 |
| --- | --- |
| `frontend/src/components/MaterialStatesEditor.tsx` | T011（本 Feature 唯一前端改动面） |
| `frontend/src/i18n/{zh,en}/upload.ts` | T012 |
| `tests/01_decentralized_uploading/material-states-editor.test.tsx` | T004–T009 |
| `tests/02_identity_governance/admin-scientific-data-edit.test.tsx` | T013 |

**并行机会**：阶段 4（数据修复）与阶段 2/3 无依赖，可并行；T004–T010 各测试用例可并行编写。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 / US1 | T004、T010、T011 | 未分配候选区展示 |
| FR-002 / US1 | T005、T011 | 分配与确认交互 |
| FR-003 / US1 | T006、T011 | 空材料状态提示 |
| FR-004 / US1 | T007、T011 | blocked 候选禁用与原因 |
| FR-005 / US1 | T008、T011 | 排除能力 |
| FR-006 / US1 | T005、T011 | 分配后进入对应卡片面板 |
| FR-007 | T002 | 后端契约不变 |
| FR-008 / US2 | T013、T014 | 管理端共用 |
| FR-009 / US1 | T009、T011 | readOnly 不渲染 |
| FR-010 / US3 | T015、T016 | 存量数据恢复 |
| FR-011 | T012、T017 | i18n 与回归 |
| SC-001 | T010、T017 | 落库链路 |
| SC-002 | T015、T019 | 详情 3D 渲染 |
| SC-003 / US2 | T013 | 管理端保存不丢结构 |
| SC-004 / US3 | T015 | Hg 结构恢复 |
| SC-005 | T017 | 上传链路不回退 |

## MVP 与增量策略

1. 完成阶段 1：确认共享组件与契约。
2. 完成阶段 2（P1）：上传校对页未分配候选确认——本 Feature 的最小可用交付。
3. 完成阶段 3（P2）：管理端共用（随共享组件自然获得）。
4. 完成阶段 4（P2）：存量数据恢复。
5. 最终阶段收尾验证，并把 Issue 正文与实现对齐（T020）。
