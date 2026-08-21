# 契约：上传任务清理与审核快照

## 上传任务读取

`GET /api/upload-tasks` 和 `GET /api/upload-tasks/{task_id}`：

- 数据来自 Redis 公开 DTO。
- duplicate 不触发 Paper 查询。
- 返回 `state_schema_version`。
- 契约版本不支持时返回稳定错误，不静默猜测权限。

## 提交

`POST /api/rag/upload-tasks/{task_id}/submit`：

- 若 MySQL 已存在相同 upload_task_id 且属于当前用户，返回原 paper_id。
- 若属于其他用户，返回 403。
- 新提交事务成功后执行提交清理；清理失败不得创建第二篇 Paper。

## 审核快照读取

`GET /api/rag/papers/{paper_id}/review-artifact`：

- 仅管理员。
- 只返回 paper_id 和 paper_revision 均匹配当前论文的快照。
- revision 不一致返回 409 `review_artifact_revision_mismatch`。

## 审核快照删除

`DELETE /api/rag/papers/{paper_id}/review-artifact`：

- 仅管理员或内部审核代理。
- 论文仍为 pending 时返回 409 `review_artifact_still_pending`。
- approved/rejected 时幂等删除；目标不存在也返回成功并标明 `cleaned=false`。
- 删除失败返回可重试错误，不改变论文审核状态。

## 一次性状态迁移

```text
python -m backend.scripts.migrate_upload_task_states
python -m backend.scripts.migrate_upload_task_states --apply
```

- 默认 dry-run。
- 只处理旧 duplicate 状态。
- apply 查询 MySQL 并原子回填当前契约字段。
- cleanup_at 以旧状态 updated_at 作为进入 duplicate 的保守时间基准，不因迁移重新获得 24 小时。
- 重复执行不修改已是当前版本的状态。

## 部署契约检查

API 与 Worker 镜像必须暴露同一个 `UPLOAD_STATE_SCHEMA_VERSION`。验证至少检查：

- 两个容器镜像 ID 一致或源码契约版本一致；
- Worker `_handle_duplicate` 写入完整字段；
- API 任务读取不依赖数据库 Session；
- 旧状态迁移后 legacy duplicate 数量为 0。
