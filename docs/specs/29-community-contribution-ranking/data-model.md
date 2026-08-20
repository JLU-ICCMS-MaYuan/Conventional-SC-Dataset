# 数据模型：社区贡献排行榜

## `paper_review_events` 审核历史

一行表示一篇论文的一次有效审核动作。事件创建后不可通过业务 API 修改或删除。

| 字段 | 类型/可空 | 约束与含义 |
| --- | --- | --- |
| `id` | bigint / 否 | 主键 |
| `paper_id` | bigint / 否 | 审核发生时的论文 ID；保留快照，不设级联删除 |
| `reviewer_user_id` | bigint / 否 | 审核人，外键到 `users.id`，限制删除 |
| `status` | varchar(50) / 否 | `approved`、`rejected` 或 `pending` |
| `review_comment` | text / 是 | 本次提交的审核意见快照 |
| `reviewed_at` | datetime / 否 | 有效审核发生时间 |
| `request_id` | varchar(64) / 是 | 客户端幂等键；非空时全局唯一 |
| `source` | varchar(20) / 否 | `single`、`batch` 或 `backfill` |

索引与约束：

- `UNIQUE(request_id)`：阻止同一审核请求重试重复计数；批量请求为每篇论文派生稳定子键。
- `(reviewer_user_id, reviewed_at, id)`：审核榜聚合与同分排序。
- `(paper_id, reviewed_at)`：论文审核历史追踪。
- `status` 仅接受约定的三种审核结论。

## 派生模型

### 贡献排行项

| 字段 | 含义 |
| --- | --- |
| `rank` | 从 1 开始的顺序名次；排序完全相同时仍按用户 ID 确定唯一顺序 |
| `user_id` | 仅用于客户端稳定 key，不作为敏感认证信息 |
| `display_name` | `users.real_name`；空值使用“匿名贡献者” |
| `avatar_text` | 展示名称首字符 |
| `contribution_count` | 对应榜单贡献数 |
| `reached_at` | 达到当前累计数的时间，仅用于服务端排序，不向公开响应暴露 |

### 贡献榜单快照

- `participant_count`：上传贡献者集合与审核贡献者集合的并集大小。
- `upload_leaderboard`：上传排行前 20。
- `review_leaderboard`：审核排行前 20。
- `current_user`：仅有效登录请求存在，含上传和审核本人项。
- `generated_at`：本次数据库聚合完成时间。

## 生命周期与状态转换

1. 管理员提交审核请求。
2. 服务校验状态、权限、不可自审与幂等键。
3. 若请求是重复或无业务变化，返回当前论文但不写事件。
4. 否则在同一事务内更新 `papers` 当前审核字段并插入 `paper_review_events`。
5. 事务成功后清除贡献榜缓存；失败时两者一起回滚。
6. 排行查询从当前 `papers` 计算上传贡献，从不可变事件计算审核贡献。

## 迁移与回滚

- 升级迁移创建表、约束和索引，并为 `reviewed_by_user_id`、`reviewed_at` 均非空的现有论文各插入一条 `source = backfill` 事件。
- 回填请求键采用确定性 `backfill-paper-<paper_id>`，保证迁移逻辑可识别且不会重复。
- 降级迁移删除审核历史表；降级会丢失新记录的历史审核事实，执行前必须备份。
