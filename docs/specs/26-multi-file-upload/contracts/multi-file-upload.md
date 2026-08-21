# API 契约：多文件上传

- `POST /api/upload-tasks` 请求含 `files[{client_id,role,filename,size,media_type}]`，返回服务器 `file_id`。
- `PUT /api/upload-tasks/{task_id}/files/{file_id}` 流式上传一个文件。
- `POST /api/upload-tasks/{task_id}/finalize` 幂等校验全部文件并锁定；自动路径也调用同一服务。
- `GET /api/upload-tasks/{task_id}/consistency` 返回 `ok/unknown/warning` 及字段级差异。
- `POST /api/upload-tasks/{task_id}/submit` 在存在 warning 时要求 `consistency_acknowledged=true`。

稳定错误码：`INVALID_MANIFEST`、`UNSUPPORTED_FILE_TYPE`、`FILE_TOO_LARGE`、`DUPLICATE_TASK_FILE`、`MANIFEST_LOCKED`、`UPLOAD_INCOMPLETE`、`CONSISTENCY_ACK_REQUIRED`。
