# 技术决策记录：提交失败后任务状态回滚修复

**Feature**：[spec.md](spec.md) ／ **日期**：2026-08-26

## D1：回滚到 ready 并保留 submission_status=failed

- **决策**：异常路径 `update_state(task_id, status="ready", submission_status="failed")`。
- **理由**：`status="ready"` 是前端可编辑表单的唯一门（UploadParsingDetail.tsx:152）；`submission_status="failed"` 如实保留失败事实，不影响任何现有读取（前端不消费该字段做门控）。
- **备选**：删除 submission_status（丢失失败事实，拒绝）；回滚到其他状态（语义不符，拒绝）。

## D2：沿用 best-effort 回滚

- **决策**：回滚 update_state 仍包在 try/except pass 内，原始异常继续抛出。
- **理由**：与现有写法一致；Redis 抖动不得把 500 变成别的错误。
