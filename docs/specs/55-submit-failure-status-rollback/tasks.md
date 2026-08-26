# 实施任务：提交失败后任务状态回滚修复

**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)

**格式**：`- [ ] T### [P?] [US#?] 动作描述，包含准确文件路径`

## 阶段 1：修复与测试

- [x] T001 [US1] 改 `backend/api/rag.py:1312-1317`：异常路径 `update_state` 补 `status="ready"`（保留 `submission_status="failed"` 与 best-effort try/except）
- [x] T002 [US1] 在 `backend/tests/test_upload_workflow.py` 追加用例：mock `_create_pending_paper` 抛错 → submit 抛错后 state 为 `status="ready"`、`submission_status="failed"`、草稿保留可重试

## 最终阶段

- [x] T003 运行后端 pytest 与前端 `npm run test:upload-ui` 回归全过
- [x] T004 按 quickstart 场景 1–2 人工验收（含 #54 的原任务重提）
- [x] T005 `gh issue edit 55` 回写 Spec 链接；按 AGENTS.md 规范 git commit

## 需求覆盖

| 来源 | 任务 | 说明 |
|------|------|------|
| FR-001~003 / US1 | T001、T002 | 回滚修复与回归用例 |
| SC-001 | T004 | 人工验收 |
