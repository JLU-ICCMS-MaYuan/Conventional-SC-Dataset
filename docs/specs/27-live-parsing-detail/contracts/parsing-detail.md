# API 契约：解析详情

- `GET /api/upload-tasks/{task_id}/parsing`：文件、分段和汇总状态快照；纯只读，不续期。
- `GET /api/upload-tasks/{task_id}/chunks`：分页返回安全分段结果。
- `POST /api/upload-tasks/{task_id}/retry`：默认只重试失败/缺失段，幂等返回 revision。

响应带 `server_time`、`revision` 和 `next_poll_ms`。活跃阶段建议 `2000`，稳定阶段为 `null`。客户端不得用计时器伪造处理进度。
