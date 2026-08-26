# Feature 规格：提交失败后任务状态回滚修复

**GitHub Issue**：[#55](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/55)（type:bug）

**创建日期**：2026-08-26

**状态**：已确认

## 背景与目标

`_submit_upload_draft_locked` 在 `_create_pending_paper` 抛错时只写 `submission_status="failed"`，不回滚 `status="submitting"`。前端仅 `status === 'ready'` 渲染可编辑表单，卡死任务显示空白只读预览；且 submitting 状态不按创建时间过期，任务永久无法恢复（本次由 #54 的 500 触发，运维已手动修复受影响任务）。

目标：submit 失败时任务自动回到可校对状态，用户可修正后重新提交。

## 用户场景与验收

### 用户故事 1：提交失败后可继续校对（优先级：P1）

贡献者提交审核因任何后端错误失败后，上传记录恢复「等待校对」状态，打开详情仍是可编辑表单，草稿内容不变；修正问题后可再次提交成功。

**独立验收**：模拟 `_create_pending_paper` 抛错 → submit 返回错误后，Redis state 的 `status="ready"`、`submission_status="failed"`，草稿 key 仍存在且内容不变。

**验收场景**：

1. **假如** 任务处于 ready 且提交过程中 `_create_pending_paper` 抛出异常，**当** submit 返回 5xx，**那么** `status` 回滚为 `ready`，`submission_status` 为 `failed`。
2. **假如** 状态已回滚，**当** 用户重新打开详情页，**那么** 渲染可编辑表单（非只读预览），草稿字段完整。
3. **假如** 状态回滚时 `update_state` 自身失败，**当** 异常向外抛出，**那么** 不掩盖原始的提交异常（best-effort 回滚）。

## 边界与异常场景

- 回滚操作本身失败（Redis 抖动）不得掩盖原始异常——沿用现有 try/except pass 的 best-effort 写法。
- 重复提交防护（`submission_in_progress` 锁、`_submitted_paper_for_task` 幂等）不受影响。
- 成功路径的 `_record_submitted_upload` / `cleanup_transient_data` 失败不重滚状态（已有独立 best-effort 处理）。

## 需求

### 功能需求

- **FR-001**：`_create_pending_paper` 抛错时，`status` 必须回滚为 `ready`、`submission_status` 写为 `failed`；原始异常继续向上抛出。
- **FR-002**：回滚失败不得掩盖原始提交异常。
- **FR-003**：回归测试覆盖：失败后 status=ready、submission_status=failed、草稿保留、可重试。

## 成功标准

- **SC-001**：人为制造 submit 失败后任务自动回到 ready，详情页可编辑，重新提交成功。
- **SC-002**：相关测试通过，不回归 #54。

## 范围外事项

- 提交成功后的清理重试语义。
- 其他终态的状态机梳理。

## 澄清记录

### 2026-08-26

- 受影响任务 `6b5bf07cac944ed6acbaa6422bdbeee7` 已通过一次性数据修复恢复（Redis state `status`: submitting→ready，草稿 69 KB 完好），本 Feature 只修代码根因。
