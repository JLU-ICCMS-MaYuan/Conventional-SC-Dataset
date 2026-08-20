# API 契约：社区贡献排行榜

## 获取贡献排行榜

`GET /api/community/contributions?refresh=<boolean>`

### 权限

- 匿名可访问公共榜单。
- 携带有效 Bearer Token 时附加 `current_user`。
- 携带无效或过期 Token 返回 `401`，不静默降级为匿名响应。
- `refresh=true` 对匿名和登录用户均可用；服务端应限制并发重建，防止缓存击穿。

### 查询参数

| 参数 | 必填 | 默认值 | 含义 |
| --- | --- | --- | --- |
| `refresh` | 否 | `false` | `true` 时绕过缓存并基于数据库重建榜单 |

### `200 OK`

```json
{
  "participant_count": 42,
  "upload_leaderboard": [
    {
      "rank": 1,
      "user_id": 7,
      "display_name": "张三",
      "avatar_text": "张",
      "contribution_count": 18
    }
  ],
  "review_leaderboard": [],
  "current_user": {
    "upload": {
      "rank": 31,
      "user_id": 99,
      "display_name": "李四",
      "avatar_text": "李",
      "contribution_count": 1
    },
    "review": null
  },
  "generated_at": "2026-08-20T16:00:00+08:00"
}
```

匿名响应省略 `current_user`。登录用户零贡献的榜项为 `null`，界面显示 0 次和“暂无排名”。数组为空而不是 `null`。

### 错误

| 状态 | 条件 | 响应要求 |
| --- | --- | --- |
| `400` | `refresh` 不是合法布尔值 | 返回可读参数错误 |
| `401` | Bearer Token 无效或过期 | 返回认证错误 |
| `500` | 数据库聚合失败 | 不返回不完整榜单 |

## 审核写入契约扩展

以下已有接口的请求体新增可选字段 `review_request_id`：

- `POST /api/admin/papers/:id/review`
- `POST /api/admin/papers/batch-review`

约束：

- 新前端必须发送长度不超过 64 的唯一值。
- 单篇审核直接使用该值；批量审核为每个 paper ID 派生 `<request_id>:<paper_id>`。
- 相同请求键的重试返回成功但不重复更新或计数。
- 兼容旧客户端省略该字段；后端仍通过“状态不变且无新增审核意见”规则阻止明显重复计数。
