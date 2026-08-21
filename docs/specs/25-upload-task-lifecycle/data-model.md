# 数据模型：#25

## Redis UploadTask

- `task_id`、`owner_id`、`status`、`stage`、`revision`
- `created_at`、`updated_at`、`last_progress_at`、`last_user_activity_at`
- `terminal_at`、`cleanup_at`、`cancel_requested_at`
- `progress`、`error_code`、`error_message`
- 内部字段：`job_id`、文件路径、缓存路径，仅仓库内部可见

## Redis 索引

`upload:user:{user_id}:tasks`：member 为 task_id，score 为最近可见排序时间。创建、提交、删除和失效清理必须与任务状态保持一致。

## MySQL

`papers.upload_task_id`：nullable、unique、indexed。它是永久认领标识；Redis 是否存在不影响其保护作用。

## 状态转换

`uploading → queued → extracting → reading → summarizing → ready → submitting → submitted`

异常分支：`* → failed`、`* → cancelling → cancelled`、重复检测进入 `duplicate`。禁止从终态回到运行态；重试通过 revision 创建新的允许转换。
