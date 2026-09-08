# 状态模型：上传 Worker 版本漂移恢复

## 上传任务

本修复不新增持久实体或字段，只明确既有 Redis 上传任务在队列级失败时的取值。

| 字段 | 队列级失败值 | 约束 |
|------|--------------|------|
| `task_id` | 保持不变 | 必须为 32 位小写十六进制 |
| `status` | `failed` | 仅允许从既有运行态转换 |
| `processing_status` | `failed` | 与 `status` 同步 |
| `error_code` | `upload_worker_execution_failed` | 稳定机器码 |
| `processing_error` | 固定安全摘要 | 不包含异常堆栈、文件路径或凭据 |
| `failed_stage` | 失败前的 `stage` | 通常为 `queued` |
| `partial_draft` | `null` | 不展示不完整草稿 |
| `terminal_at` / `cleanup_at` | 由既有状态机生成 | 沿用 24 小时终态生命周期 |

## 状态转换

```text
queued / extracting / reading / summarizing
                │
                │ RQ 入口或执行边界异常，且业务函数未完成终态写入
                ▼
              failed
                │
                │ 既有 POST /api/upload-tasks/{task_id}/retry
                ▼
              queued ──► extracting ──► reading ──► summarizing ──► ready
```

## 不变量

1. 队列级回调只收敛运行态，不覆盖 `failed`、`ready`、`duplicate`、`cancelled` 或 `submitted`。
2. 非法或缺失 task ID 不产生 Redis 状态。
3. RQ job 的失败记录继续由 RQ 管理；上传任务状态不替代 FailedJobRegistry。
4. 历史任务恢复必须生成新 job ID，旧失败 job 仅作为诊断证据保留到既有 TTL。
5. 原始上传文件、已完成 Markdown 和分段缓存不因队列级失败被立即删除。
