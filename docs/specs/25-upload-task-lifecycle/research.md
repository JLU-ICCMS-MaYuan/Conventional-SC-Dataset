# 调研记录：#25

- 现有 Redis 只有 `upload:{task}:state|draft|lock`，没有用户索引，无法恢复任务或原子限制 100 个。
- 现有 `GET → 修改 → SETEX` 会让并行文件上传、Worker 和草稿保存互相覆盖。
- 现有清理在 `state=None` 时直接删目录；必须先用永久 `upload_task_id` 查询 MySQL。
- RQ Worker 不持有覆盖整个处理周期的生命周期锁，因此取消依赖状态检查点和确定性 job/revision。
- `ready` 滑动续期必须与只读轮询分离，避免页面常开导致永不过期。

**决定**：用户索引使用有序集合；任务数据由仓库封装原子 patch；清理采用数据库认领检查和可清理状态白名单。
