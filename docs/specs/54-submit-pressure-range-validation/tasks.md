# 实施任务：提交审核压强区间校验与草稿保存语义修复

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、
[data-model.md](data-model.md)、[contracts/](contracts/draft-and-api.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

**说明**：本 Spec 为已实现修复（commit 16298c9）的补档，T001–T006 的勾选证据为对应测试与迁移验证记录。

## 阶段 1：后端修复

- [x] T001 新建迁移 `alembic/versions/20260826_0016_relax_pressure_range.py`（单臂合法、双臂 min≤max）并同步 `backend/models.py` 约束文本；dev MySQL 8.4 验证 upgrade/downgrade 可逆，临时表实测 (200,NULL)/(NULL,200)/(100,200) 可插入、(300,200) 被拒 [US1]
- [x] T002 改 `backend/api/rag.py`：`_validate_draft` 新增压强校验（min>max → 400 `invalid_pressure_range`，:283-287）与 `partial` 参数（:220-228）；PUT 路径传 partial=True（:799），submit 两处保持严格 [US1][US2]；grep 确认 `backend/` 无 min/max 成对假设计算
- [x] T003 在 `backend/tests/test_upload_workflow.py:313-388` 追加 5 用例：单臂通过、倒置 400、PUT 半成品落盘、同一半成品 submit 400 [US1][US2]

## 阶段 2：前端修复

- [x] T004 改 `frontend/src/components/UploadTaskEditor.tsx`（:118-134 新增 `backendErrorReason`/`failureMessage`，:606/:676 两处 catch 接入）：保存/提交失败横幅展示后端 detail.message（附 code）并区分动作，无 detail 回退通用文案 [US3]
- [x] T005 在 `tests/01_decentralized_uploading/upload-task-editor-layout.test.tsx` 追加 2 用例（400 带 detail 显示具体原因、500 无 detail 回退）[US3]；`upload-task-editor-classification.test.tsx` 重度用例加 `{ timeout: 15000 }` 修复并行偶红 flake

## 最终阶段

- [x] T006 全量回归：后端 pytest 99 过（test_concurrency.py 环境脚本除外）、前端 vitest 6 文件 45 用例全过、`npx tsc --noEmit` 通过
- [x] T007 重建 dev 镜像（`cd docker && docker compose build python frontend && docker compose up -d`）后按 quickstart 场景 1–4 验收：原任务 `6b5bf07c…` 重新提交成功，`papers` id=4 / DOI 10.1073/pnas.1704505114 / `review_status=pending` 已入库，该材料状态 `pressure_value_gpa=250`、`pressure_min_gpa=200`、`pressure_max_gpa=NULL`、`pressure_raw="above 200 GPa"` 完整保留；dev MySQL `alembic_version=20260826_0016`，`ck_material_states_pressure_range` 实际定义为「任一侧为 NULL 合法，双侧要求 min≤max」
- [x] T008 `gh issue comment 54` 回写修复记录；按 AGENTS.md 规范 git commit（16298c9，仅暂存本修复文件）

## 依赖与执行顺序

- T001→T002→T003 串行（同一后端链路）；T004、T005 串行（同一前端文件）；前后端两线并行。
- T007 依赖镜像重建（运维前置），为关闭 Issue #54 的最后条件。

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001 / US1 | T001 | 约束放宽与迁移验证 |
| FR-002 / US1 | T002、T003 | 校验补缺与用例 |
| FR-003 / US2 | T002、T003 | 两级校验分离与用例 |
| FR-004 / US3 | T004、T005 | 错误可见与用例 |
| SC-002 | T007 | 原任务重提验收（待镜像重建） |
