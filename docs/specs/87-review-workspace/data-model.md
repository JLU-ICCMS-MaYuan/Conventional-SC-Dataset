# 数据模型：文献处理历史

**Feature**：[spec.md](spec.md)

## 演进目标

现有 `paper_review_events` 仅能表示审核。迁移后它的唯一继任者为
`paper_history_events`，作为论文上传、修改和审核的唯一追加式事实来源。不会并行保留两个
持续写入的事件表。

## `paper_history_events`

| 字段 | 约束 | 说明 |
| --- | --- | --- |
| `id` | 主键 | 事件标识。 |
| `paper_id` | 非空，外键 `papers.id` | 事件所属论文。 |
| `paper_revision` | 非空，`>= 1` | 发生动作时的论文版本。 |
| `event_type` | 非空，`uploaded` / `modified` / `reviewed` | 处理动作类型。 |
| `actor_user_id` | 可空，外键 `users.id` | 操作者；历史导入的未知上传者为 `NULL`。 |
| `actor_username_snapshot` | 可空 | 动作发生时的公开用户名；旧数据由迁移时的当前用户名回填。 |
| `review_status` | 仅审核事件可非空，`approved` / `rejected` / `pending` | 审核结果。 |
| `review_comment` | 可空 | 审核意见；上传和修改必须为 `NULL`。 |
| `occurred_at` | 非空 | 动作完成时间。 |
| `operation_id` | 可空且唯一 | 上传任务、编辑保存或审核请求的幂等标识。 |
| `classification_snapshot` | 兼容保留，不对历史 API 输出 | 已有审核事件的历史字段；新事件不写入。 |

索引：`(paper_id, occurred_at, id)` 支持时间线；`(actor_user_id, occurred_at, id)` 支持审核
贡献统计；`operation_id` 保证重试和两段保存去重。

## 生命周期

```text
创建待审 Paper
  -> uploaded

一次实际保存修改
  -> modified

每次实际审核
  -> reviewed

物理删除 Paper
  -> 先删除全部 paper_history_events，再删除 Paper
```

事件不可修改、不可单独删除。论文的 `review_status`、`review_comment`、`reviewed_by_user_id`
和 `reviewed_at` 继续表示当前最终状态；它们不是历史事件的替代品。

## 迁移与回填

1. 重命名现有表并将列语义从审核专用字段演进为通用事件字段。
2. 现有审核行标记为 `reviewed`，保留审核结果、审核意见、时间、版本和操作标识。
3. 为每篇 `papers` 行插入一条 `uploaded` 事件，时间使用 `created_at`，版本为 `1`；
   上传者和用户名快照由 `uploaded_by_user_id` 与 `users` 回填，缺失时保留空操作者。
4. 不从 `updated_at` 推导修改事件，因为没有可靠操作者和操作时间。
5. 新约束确保 `uploaded` 和 `modified` 没有审核结果或意见，`reviewed` 必有审核结果。

迁移必须先验证所有旧审核事件的行数、审核意见和时间保持一致，再切换贡献统计与删除链路。
