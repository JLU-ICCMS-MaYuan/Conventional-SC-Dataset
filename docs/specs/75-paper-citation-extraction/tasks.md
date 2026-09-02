# 实施任务：材料状态「材料」字段改名为「化学式」

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：确认依赖就位与基线，避免在 i18n 基建缺失时写出需要返工的中文硬编码。

- [x] T001 确认 Issue #74 的 i18n 基建已就位：`frontend/src/context/LanguageContext.tsx` 存在，且 `frontend/src/i18n/{zh,en}/upload.ts` 与 `admin.ts` 已建立（依据 [research.md](research.md) R5；未就位则本 Feature 阻塞）
- [x] T002 确认 #74 的 T018（`UploadTaskEditor.tsx` 文案替换）与 T019（`AdminPage.tsx` 文案替换）已完成，避免同文件冲突（[plan.md](plan.md) 串行触点）
- [x] T003 执行 `scripts/run-tests.sh frontend` 与 `scripts/run-tests.sh backend` 记录基线，确认 `tests/07_researcher_community_forum/news-feed.test.tsx` 的既有失败用例不计入本 Feature 回归

## 阶段 2：用户故事 1——上传校对页化学式标签（P1，MVP）

**目标**：上传者在校对页明确知道首个输入框该填化学式。

**独立验收**：校对页材料状态卡片首个输入框标签为「化学式」，英文为 `Chemical formula`；留空提交时提示指明化学式且定位到出错卡片。

### 测试

- [x] T004 [P] [US1] 在 `tests/01_decentralized_uploading/chemical-formula-label.test.tsx` 新增测试：校对页首个输入框标签在中文下为「化学式」、英文下为 `Chemical formula`（FR-001、FR-003、SC-001）
- [x] T005 [P] [US1] 在 `tests/01_decentralized_uploading/chemical-formula-label.test.tsx` 新增测试：填入化学式并提交后，请求体字段名仍为 `material`（FR-004、SC-002）
- [x] T006 [US1] 修改 `tests/01_decentralized_uploading/submit-validation-feedback.test.tsx`：3 处文案断言由「缺少材料」改为「缺少化学式」，序号前缀断言保留不动（[research.md](research.md) R4、FR-007）
- [x] T007 [P] [US1] 在 `tests/01_decentralized_uploading/submit-validation-feedback.test.tsx` 新增测试：后端返回「第 N 个材料状态缺少化学式」时仍能解析序号并定位到对应卡片（FR-007、SC-003）
- [x] T008 [P] [US1] 在 `backend/tests/test_submit_error_contract.py` 新增或更新断言：化学式缺失时 `detail.code` 为 `state_material_required` 且 `message` 匹配 `第 \d+ 个材料状态缺少化学式`（FR-006、FR-007）

### 实施

- [x] T009 [US1] 修改 `frontend/src/i18n/zh/upload.ts` 与 `frontend/src/i18n/en/upload.ts`：新增化学式标签条目，值分别为「化学式」与 `Chemical formula`（FR-003）
- [x] T010 [US1] 修改 `frontend/src/components/UploadTaskEditor.tsx` 第 1061 行附近：`label` 改用 T009 的字典键（FR-001）
- [x] T011 [US1] 修改 `backend/api/rag.py` 第 254 行：文案由「第 {n} 个材料状态缺少材料」改为「第 {n} 个材料状态缺少化学式」，前缀保持不变；第 262 行「缺少材料家族」不动（FR-006、FR-007、FR-008）

## 阶段 3：用户故事 2——管理员编辑页化学式标签（P2）

**目标**：管理员编辑物性时标签与上传页一致。

**独立验收**：管理员编辑弹窗物性行的输入框标签为「化学式 (material)」，英文为 `Chemical formula (material)`。

### 测试

- [x] T012 [P] [US2] 在 `tests/02_identity_governance/admin-edit-review.test.tsx` 新增测试：物性行输入框标签在中文下为「化学式 (material)」、英文下为 `Chemical formula (material)`（FR-002、FR-003、SC-001）

### 实施

- [x] T013 [US2] 修改 `frontend/src/i18n/zh/admin.ts` 与 `frontend/src/i18n/en/admin.ts`：新增条目，值分别为「化学式 (material)」与 `Chemical formula (material)`（FR-003）
- [x] T014 [US2] 修改 `frontend/src/pages/AdminPage.tsx` 第 1099 行附近：`label` 改用 T013 的字典键（FR-002）

## 最终阶段：完善与跨故事事项

- [x] T015 [P] 新增测试确认不改动项：`frontend/src/components/ChartGroupEditor.tsx` 的「材料名」标签未变、「材料家族」与「材料维度」标签未变（FR-008、[research.md](research.md) R2）
- [x] T016 执行 `scripts/run-tests.sh frontend`、`scripts/run-tests.sh backend`、`python -m pytest tests -q`，与 T003 基线比对确认无新增失败（SC-004）
- [x] T017 执行 `cd frontend && npm run build`，确认 `tsc -b` 无类型错误（字典缺键会在此暴露）
- [x] T018 按 [quickstart.md](quickstart.md) 场景 1–4 手工走查，含场景 4 的不改动项确认
- [x] T019 更新 Issue #75 正文：删除对图表组合编辑器「材料名」的改名要求，改为记录该处为范围外及其理由，使 Issue 与 Spec 一致（[checklists/requirements.md](checklists/requirements.md) CHK017 备注）

## 依赖与执行顺序

- **阶段 1** 阻断全部后续；其中 T001、T002 是硬阻塞——#74 未就位时不得开始，否则违反 R5 并产生返工。
- **阶段 2、3** 在阶段 1 完成后可并行：两者改动不同的字典文件与不同组件。
- T009 阻断 T010（字典键须先存在）；T013 阻断 T014，同理。
- T006 与 T007 同文件，必须串行。
- **最终阶段** 依赖阶段 2、3 全部完成。

**串行触点（同文件任务必须串行）**：

| 文件 | 涉及任务 |
| --- | --- |
| `tests/01_decentralized_uploading/submit-validation-feedback.test.tsx` | T006、T007 |
| `frontend/src/components/UploadTaskEditor.tsx` | T010（另与 #74 的 T018 冲突，须排在其后） |
| `frontend/src/pages/AdminPage.tsx` | T014（另与 #74 的 T019 冲突，须排在其后） |

**并行机会**：T004、T005、T008 分属不同文件可并行；阶段 2 与阶段 3 的实施任务可并行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 / US1 | T004、T009、T010 | 上传校对页标签改名与验证 |
| FR-002 / US2 | T012、T013、T014 | 管理员编辑页标签改名与验证 |
| FR-003 | T004、T009、T012、T013 | 中英双语文案 |
| FR-004 | T005 | 请求体字段名不变 |
| FR-005 | T018（场景 4 步骤 3、4） | 列名不变、无新增迁移 |
| FR-006 | T008、T011 | 校验文案指明化学式 |
| FR-007 | T006、T007、T008、T011 | 序号前缀保留且定位仍生效 |
| FR-008 | T011、T015 | 语义正确的标签不被误改 |
| SC-001 | T004、T012 | 两处标签双语无遗漏 |
| SC-002 | T005 | 请求体逐键一致 |
| SC-003 | T007、T018 | 出错卡片被定位 |
| SC-004 | T016 | 三套测试与基线比对无回归 |

## MVP 与增量策略

1. 完成阶段 1：确认 #74 依赖就位。
2. 完成阶段 2（P1）：上传校对页标签与校验文案改名——这是本 Feature 的最小可用交付，覆盖错填的主要发生位置。
3. 完成阶段 3（P2）：管理员编辑页标签一致化。
4. 最终阶段收尾验证，并把 Issue 正文与 Spec 的差异对齐（T019）。

阶段 2 交付后即可独立验收；阶段 3 缺失时管理员页标签仍是旧文案，不影响上传链路的正确性。
