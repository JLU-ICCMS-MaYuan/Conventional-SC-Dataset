# 上传 Worker 失败边界契约

## 输入

RQ 调用异常回调时提供：

- `job`：必须能从位置参数读取唯一的上传 `task_id`；
- `exc_type`、`exc_value`、`traceback`：仅用于服务端诊断，不直接进入公开状态。

## 处理条件

同时满足以下条件才允许修改上传任务：

1. job 第一个位置参数是符合 `^[0-9a-f]{32}$` 的字符串；
2. Redis 中存在该任务；
3. 当前 `status` 属于既有 `RUNNING_STATUSES`。

不满足条件时回调返回并保留 RQ 默认失败处理。

## 输出状态

```json
{
  "status": "failed",
  "processing_status": "failed",
  "error_code": "upload_worker_execution_failed",
  "processing_error": "后台解析任务未能启动，请重新解析",
  "failed_stage": "queued",
  "partial_draft": null
}
```

`failed_stage` 使用失败前实际阶段，不强制固定为 `queued`。

## RQ 回调语义

- 回调返回 `true`，允许 RQ 继续执行默认异常处理并把 job 放入 FailedJobRegistry。
- 回调自身的 Redis 或状态错误只写服务端日志，不得替代原始 job 异常。
- 业务函数已经记录 `paper_processing_failed` 时，回调不得改写为
  `upload_worker_execution_failed`。

## 重试兼容

成功写入上述状态后，既有 `POST /api/upload-tasks/{task_id}/retry` 继续作为唯一用户恢复接口：

- 权限：沿用任务所有者或管理员权限；
- 前置状态：`failed`；
- 成功响应：HTTP 202；
- 后续状态：`queued / processing`，并产生新 RQ job ID。
