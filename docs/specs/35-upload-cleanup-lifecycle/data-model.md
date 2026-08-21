# 数据模型：上传任务清理生命周期

## Redis UploadTaskState

新增公开字段：

| 字段 | 含义 | 规则 |
|------|------|------|
| `state_schema_version` | 上传状态契约版本 | 创建时写入，Worker 更新时保留 |

duplicate 状态必须同时包含：

- `status=duplicate`
- `existing_paper_id`
- `existing_paper_status`
- `allowed_actions`
- `duplicate_reason`
- `terminal_at`
- `cleanup_at`

## CleanupContext

清理任务参数中的最小快照：

| 字段 | 必填 | 用途 |
|------|------|------|
| `task_id` | 是 | 计算全部受管键和目录 |
| `user_id` | 否 | Redis 用户索引移除 |
| `processing_job_id` | 否 | 删除 RQ 处理 Job |
| `existing_paper_id` | 否 | 定位 duplicate 候选目录 |
| `expected_updated_at` | 是 | 防止旧清理 Job 删除已续期任务 |
| `state_schema_version` | 是 | 检测调度方和执行方契约 |

上下文不得保存或接受调用者提供的绝对文件路径。

## ReviewSnapshot

`review_artifacts/{task_id}/result.json` 在提交后收敛为：

| 字段 | 规则 |
|------|------|
| `task_id` | 必须等于目录 task_id |
| `paper_id` | 必须等于请求论文 |
| `paper_revision` | 必须等于论文当前 content_revision |
| `ai_values` | AI 原始建议的安全结构化值 |
| `user_values` | 用户最终提交的安全结构化值 |
| `evidence` | 管理员审核所需证据 |

不保存系统提示词、密钥、异常堆栈或完整模型原始响应。

## 生命周期

```text
运行中
  -> Redis + RQ + processing artifacts + upload files + markdown

ready
  -> 上述数据，主动用户操作滑动保留 24h

submitted
  -> MySQL 正式数据 + upload files + markdown + review snapshot
  -> Redis/RQ/processing artifacts 已删除

approved/rejected
  -> MySQL 正式数据 + upload files + markdown
  -> review snapshot 已删除或等待幂等重试

failed/duplicate/cancelled 到期
  -> 所有该任务临时数据和未认领文件删除
```

## 清理组合

| 场景 | transient | unsubmitted files | duplicate candidate | review snapshot |
|------|-----------|-------------------|---------------------|-----------------|
| 提交成功 | 删除 | 保留 | 不适用 | 保留 |
| 未提交到期/主动清理 | 删除 | 删除 | duplicate 时删除 | 删除 |
| approved/rejected | 已删除 | 保留 | 不适用 | 删除 |
| pending 审核 | 已删除 | 保留 | 不适用 | 保留 |
