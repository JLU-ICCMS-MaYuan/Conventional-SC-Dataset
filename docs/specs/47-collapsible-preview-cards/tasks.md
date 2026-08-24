# 实施任务：AI 临时表单字段卡片渐进展开

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[quickstart.md](quickstart.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：准备

**目的**：建立完整 Feature 文档、确认公开 UI 测试边界并通过实施前质量门。

- [x] T001 完成 `docs/specs/47-collapsible-preview-cards/plan.md`、`research.md`、`quickstart.md` 和 `tasks.md`，并核验 Requirements Checklist。

## 阶段 2：用户故事 1——快速扫描临时表单（P1，MVP）

**目标**：短字段完整显示且没有无效控制，超长字段默认收起并保留标题、状态和入口。

**独立验收**：通过公开 `UploadParsingDetail` UI 同时渲染短字段和至少 20 行的长字段，验证按钮和默认状态。

### 测试

- [x] T002 [US1] 先在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加短字段与长字段的失败测试，覆盖 FR-001～FR-004、FR-014 和 SC-001。

### 实施

- [x] T003 [US1] 在 `frontend/src/components/UploadParsingDetail.tsx` 实现统一收起高度、真实溢出判断、短字段直显和 Grid 顶部对齐。

## 阶段 3：用户故事 2——独立核对完整候选与证据（P1）

**目标**：多张长卡片可独立展开和再次收起，正文选择不误触，全部证据保持完整。

**独立验收**：连续展开三张卡片并收起中间一张，确认其他状态和完整候选来源不变。

### 测试

- [x] T004 [US2] 先在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加独立展开、再次收起和正文点击不切换的失败测试，覆盖 FR-005～FR-008、FR-015、SC-002 和 SC-005。

### 实施

- [x] T005 [US2] 在 `frontend/src/components/UploadParsingDetail.tsx` 增加字段级展开状态、文字按钮、完整内容呈现和正文非交互边界。

## 阶段 4：用户故事 3——动态解析与多设备可用（P2）

**目标**：轮询追加、任务切换、键盘和辅助技术操作时保持正确状态。

**独立验收**：模拟连续解析响应和任务切换，并用键盘完成展开/收起，验证语义状态。

### 测试

- [x] T006 [US3] 先在 `tests/01_decentralized_uploading/upload-task-workspace.test.tsx` 增加动态追加、任务隔离和键盘/ARIA 失败测试，覆盖 FR-006、FR-009～FR-013、SC-003 和 SC-004。

### 实施

- [x] T007 [US3] 在 `frontend/src/components/UploadParsingDetail.tsx` 增加尺寸变化监听、任务身份隔离、ARIA 关系和减少动效分支。

## 阶段 5：完善与跨故事事项

- [x] T008 运行 `frontend` 上传工作区完整测试与生产构建，并在 `docs/specs/47-collapsible-preview-cards/quickstart.md` 记录可重复验收路径。
- [x] T009 使用 `big-project-overview-maintainer` 更新 `docs/overview/06-rag-literature-assistant/pdf-ingestion.md`，只记录已经验证的字段卡片折叠行为。
- [ ] T010 对照 FR、SC、Plan 和测试执行 converge；Spec 与任务文档已收敛，Issue #47 状态等待提交完成后同步。

## 依赖与执行顺序

- T001 无依赖并阻断代码实施。
- 每个用户故事严格按失败测试在前、最小实现在后的顺序执行：T002 → T003 → T004 → T005 → T006 → T007。
- T008 依赖 T003、T005、T007；T009 仅在 T008 验证通过后执行；T010 最后执行。
- 测试和实现修改同一组文件，保持串行，不标记并行任务。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| US1、FR-001～FR-004、FR-014、SC-001、SC-003 | T002、T003、T008 | 覆盖长短内容、稳定布局、安全换行和构建 |
| US2、FR-005～FR-008、FR-015、SC-002、SC-005 | T004、T005、T008 | 覆盖独立状态、完整证据和现有行为回归 |
| US3、FR-006、FR-009～FR-013、SC-003、SC-004 | T006、T007、T008 | 覆盖动态测量、任务隔离、键盘、ARIA 和减少动效 |
| Documentation Impact | T009、T010 | 更新当前功能事实并同步 Feature 状态 |

## MVP 与增量策略

1. T001 通过文档门。
2. T002～T003 交付可独立验收的长卡片默认收起 MVP。
3. T004～T005 增加多卡片独立核对能力。
4. T006～T007 补齐动态和无障碍边界。
5. T008～T010 完成回归、Overview 和收敛。
