# 实施任务：实验 Tc 的条件字段与计算上下文一致性

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/tc-draft.md](contracts/tc-draft.md)

## 阶段 1：基础契约与测试

- [x] T001 [US3] 在 `backend/tests/test_upload_workflow.py` 增加实验 `tc_method` 携带计算上下文的草稿保存、提交拒绝测试。
- [x] T002 [P] [US3] 在 `backend/tests/test_scientific_draft_rewrite.py` 增加管理员科学数据重写的同类拒绝与事务回滚测试。
- [x] T003 [P] [US3] 在 `backend/tests/test_scientific_drafts.py` 增加按 `tc_method` 创建实验/理论上下文的持久化测试。

## 阶段 2：方法驱动的写入不变量

- [x] T004 [US3] 修改 `backend/api/rag.py` 的 `_validate_draft`，校验 `tc_method`、`result_kind`、上下文关系并返回定位错误。
- [x] T005 [US3] 修改 `backend/ingest/scientific_drafts.py`，按 `tc_method` 而不是仅按 `result_kind` 创建和关联上下文。
- [x] T006 [US3] 修改 `backend/models.py` 与迁移执行链，替换 `ck_tc_results_context_kind` 为方法驱动不变量并清理历史关联。
- [x] T007 [US3] 在真实隔离 MySQL 测试中验证迁移清理、共享引用保留和约束拒绝。

## 阶段 3：用户故事 1 与 2——共享编辑体验

- [x] T008 [US1] 在 `tests/01_decentralized_uploading/` 为 `MaterialStatesEditor` 增加“先选方法、实验字段集、切换清理、中文选项标签”Vitest 测试。
- [x] T009 [US1] 修改 `frontend/src/components/MaterialStatesEditor.tsx`，以每条 `tc_method` 选择和渲染字段，删除上层类型推断；补全 `frontend/src/i18n/zh/enums.ts` 的中文方法标签。
- [x] T010 [US2] 在 `tests/02_identity_governance/` 或现有管理员编辑测试中验证管理员和超级管理员复用同一实验 Tc 字段集。

## 最终阶段：收敛与文档

- [ ] T011 运行相关 Vitest、pytest、隔离 MySQL 测试，并执行上传和管理员手工 quickstart。前端 38 项、上传/持久化 pytest 以及 #84 隔离 MySQL 迁移测试已通过；管理员真实事务测试暂被未完成的 #87 `paper_history_events` 迁移阻断，不能标记完成。
- [x] T012 使用 `big-project-overview-maintainer` 更新 `docs/overview/01_Decentralized_Uploading_of_Superconductivity_Data/upload-review-and-default-selection.md` 与 `docs/overview/02_Decentralized_Maintenance_and_Verification/domain-model-and-schema.md`。

## 依赖与执行顺序

- T001 至 T003 先于 T004 至 T006。
- T006 与 T007 在共享数据库结构上串行。
- T008 可与后端测试准备并行；T009 依赖 T008。
- T011 依赖所有实现任务，T012 在行为落地后执行。

## 需求覆盖

| 来源 | 任务 | 说明 |
| --- | --- | --- |
| FR-001 至 FR-003、FR-008 | T008–T010 | 三个编辑入口的统一字段集与按语言显示的方法标签 |
| FR-004 | T001、T002、T004 | 两类 API 的可定位拒绝 |
| FR-005 | T003、T005 | 持久化语义 |
| FR-006 至 FR-007 | T006、T007 | 历史清理与数据库兜底 |
