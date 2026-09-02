# 实施计划：未分配结构候选的分配与确认交互

**GitHub Issue**：[#77](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/77)

**日期**：2026-09-02

**Spec**：[spec.md](spec.md)　**决策依据**：[research.md](research.md)

## 目标结构与改动面

```text
frontend/src/components/MaterialStatesEditor.tsx   ← 唯一代码改动面（前端）
  ├─ 未分配候选区（新增渲染块，位于材料状态列表下方）
  │    ├─ unassignedCandidates = structureCandidates.filter(c => c.material_state_ref 以 "unassigned:" 开头)
  │    ├─ 每个候选：文件名 / 校验状态（valid|blocked）/ 目标材料状态下拉 / 采用 / 排除
  │    └─ 采用 → onStructureCandidatesChange 更新候选：
  │         material_state_ref = `material_states[${index}]`
  │         confirmation = 'confirmed', status = 'confirmed'
  ├─ 排除 → confirmation = 'excluded', status = 'excluded'
  └─ readOnly：不渲染该区；states 为空：提示先创建材料状态、采用禁用
后端：零改动（_confirmed_candidates_by_state 契约已支持）
数据修复：一次性恢复 papers.id=9 的 Hg 结构（不保留脚本）
```

## 实施步骤

### 步骤 1：未分配候选区（MaterialStatesEditor）

- 在 `MaterialStatesEditor.tsx` 的 `states.map(...)` 列表之后、`states.length === 0` 空态 Alert 之前（或之后）新增 `<Box data-testid="unassigned-candidates">` 区域，仅当 `!readOnly && unassignedCandidates.length > 0` 时渲染标题与候选列表。
- 每个候选渲染：
  - 文件名：`candidate.sources?.[0]?.filename || candidate.candidate_id`。
  - 校验状态 Chip：valid → 正常色；blocked → warning 色 + `t('upload.structureStatusBlocked')` 与 `candidate.validation?.message`。
  - 目标材料状态下拉：`states.map((s, i) => ({ value: i, label: t('upload.materialStateNumber', { index: i + 1 }) + (s.material ? ` · ${s.material}` : '') }))`；`states.length === 0` 时禁用并显示 `t('upload.unassignedNeedState')`。
  - 「采用」按钮：`disabled={states.length === 0 || targetIndex == null || candidate.status !== 'valid'}`。
  - 「排除」按钮：`disabled={candidate.confirmation === 'excluded'}`。
- 交互回调统一走 `onStructureCandidatesChange`（受控），不引入组件内部状态副本（除 `targetIndex` 这类纯 UI 态）。

### 步骤 2：管理端共用

- 管理端编辑弹窗已消费 `MaterialStatesEditor` 并传入 `structureCandidates`/`onStructureCandidatesChange`（#76 已接线），未分配候选区自动生效；管理端数据修复后同样可确认。无需改 `AdminPage.tsx`。

### 步骤 3：i18n 文案

- `frontend/src/i18n/{zh,en}/upload.ts` 新增键（键集一致）：未分配候选区标题、分配目标标签、采用/排除按钮（可复用 `upload.adoptStructure`/`upload.excludeStructure`，若无则新增）、需先创建材料状态提示、校验失败提示。

### 步骤 4：测试

- `tests/01_decentralized_uploading/material-states-editor.test.tsx` 新增用例：
  1. 传入含 `unassigned:*` 候选时渲染未分配区（文件名、状态可见）。
  2. 选择材料状态并「采用」后 `onStructureCandidatesChange` 收到更新后的候选（`material_state_ref=material_states[0]`、confirmed）。
  3. `states` 为空时采用禁用且显示提示。
  4. `blocked` 候选采用禁用且显示失败原因。
  5. 「排除」后候选 confirmation=excluded。
  6. `readOnly` 不渲染未分配区。
- `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 或新用例：上传任务带结构附件的草稿，校对页可见未分配候选并可分配（mock 草稿含 unassigned 候选）。
- 管理端：`tests/02_identity_governance/admin-scientific-data-edit.test.tsx` 补充：detail/草稿含 unassigned 候选时编辑弹窗可见并可在保存时随 C1 提交。

### 步骤 5：存量数据修复（papers.id=9）

- 用 `backend/services/structure_candidates.build_structure_candidate` 处理磁盘上的 `Hg-R-3m.vasp`，取 `representations.conventional.cif.text` 为规范表示，写 `structure_models` 行：
  - `paper_id=9, paper_revision=2, material_state_id=51, structure_format='cif', structure_text=<conventional CIF>, structure_hash=sha256(text)`，其余列按既有写入逻辑（`scientific_drafts.py:305-330` 的字段集）。
- 一次性执行，不保留脚本；执行后核对详情接口 `GET /api/admin/papers/9` 的 `material_states[].structures` 非空。

### 步骤 6：验证

- `cd frontend && npx vitest run --config ../vitest.config.ts tests/01_decentralized_uploading/ tests/02_identity_governance/` 全绿。
- `cd frontend && npm run build`（tsc -b）无类型错误。
- `scripts/run-tests.sh go`、`scripts/run-tests.sh backend` 无回归（后端零改动，仅确认）。
- 浏览器走查：上传带 VASP 任务 → 校对页分配确认 → 提交 → 详情页 3D 结构可见；`papers.id=9` 详情页 3D 结构可见。

## 关键约束

- **后端零改动**：`_confirmed_candidates_by_state`、`build_structure_candidate`、上传端点均不动。
- **受控组件**：候选状态由父级持有（`structureCandidates`/`onStructureCandidatesChange`），组件内只加纯 UI 态（`targetIndex`）。
- **不破坏既有测试**：`material-states-editor.test.tsx`、`admin-scientific-data-edit.test.tsx` 等既有用例必须通过。
