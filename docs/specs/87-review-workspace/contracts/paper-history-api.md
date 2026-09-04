# 接口契约：管理端文献处理历史

**Feature**：[spec.md](../spec.md)

## 管理端列表与详情

`GET /api/admin/papers/all` 保持现有管理员鉴权，并在每条列表项上返回：

```json
{
  "uploader_name": "author"
}
```

- `uploader_name`：上传者的公开用户名；没有归属时为 `null`，供论文列表每行操作区域展示。
- `GET /api/admin/papers/{paper_id}` 不重复返回 `uploader_name`，也不返回 `record_count`；物性数据仍由现有物性编辑区按原契约读取和保存。

列表交互约定：有用户名时，操作区域中的用户名链接到 `/users/{username}` 公开页；没有用户名时显示
稳定占位 `-`。历史入口使用历史图标按钮，文字“历史”仅作为 Tooltip 和无障碍名称，不在按钮视觉上显示。

## 读取处理历史

`GET /api/admin/papers/{paper_id}/history`

**权限**：active `admin` 或 active `superadmin`。

**成功响应**：

```json
{
  "paper_id": 87,
  "events": [
    {
      "id": 1,
      "event_type": "uploaded",
      "paper_revision": 1,
      "actor": { "username": "author", "unknown": false },
      "occurred_at": "2026-09-03T10:00:00Z",
      "review": null
    },
    {
      "id": 2,
      "event_type": "reviewed",
      "paper_revision": 1,
      "actor": { "username": "reviewer", "unknown": false },
      "occurred_at": "2026-09-03T11:00:00Z",
      "review": { "status": "approved", "comment": "证据充分" }
    }
  ]
}
```

- 事件按 `occurred_at`、`id` 升序排列。
- `uploaded` 与 `modified` 的 `review` 为 `null`。
- 历史导入但没有上传者时，`actor.username` 为 `null`、`actor.unknown` 为 `true`；前端显示
  “历史导入，上传者未知”。
- 论文不存在返回 `404`；无管理员权限返回 `403`。

## 写入操作标识

管理员编辑页每次点击“保存修改”生成一个 UUID，并以 `history_operation_id` 同时传给：

- `PUT /api/admin/papers/{paper_id}`
- `PUT /api/rag/papers/{paper_id}/scientific-draft`

两个端点仅在对应数据实际变化时尝试写入 `modified` 事件。`history_operation_id` 唯一约束
保证同一次界面操作最多产生一条历史。新上传使用 `upload_task_id`，审核继续使用
`review_request_id` 作为操作标识。
