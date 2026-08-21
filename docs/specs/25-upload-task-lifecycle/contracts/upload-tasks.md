# API 契约：任务生命周期

- `POST /api/upload-tasks`：创建任务，达到 100 返回 `409 ACTIVE_TASK_LIMIT_REACHED`。
- `GET /api/upload-tasks`：返回当前用户任务摘要数组。
- `GET /api/upload-tasks/{task_id}`：返回公开详情；显式 `touch=true` 只允许主动详情操作续期。
- `POST /api/upload-tasks/{task_id}/activity`：记录允许续期的用户动作。
- `POST /api/upload-tasks/{task_id}/cancel`：幂等请求取消。
- `DELETE /api/upload-tasks/{task_id}`：只清理可清理终态。
- `POST /api/upload-tasks/cleanup`：批量清理并返回 `deleted/skipped/deferred`。

公开 DTO 包含 `task_id/status/stage/progress/created_at/updated_at/cleanup_at/error/files`；严禁返回绝对路径、job id、内部 Redis key 和原始异常堆栈。
