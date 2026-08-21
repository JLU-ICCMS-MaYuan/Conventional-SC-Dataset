# API 契约：论文权限

- `GET /api/papers`：根据可选身份过滤可见论文。
- `GET /api/papers/{id}`：不存在 404，存在但无权 403。
- `PATCH /api/papers/{id}`：上传者或管理员修改白名单业务字段。
- 管理员审核接口：继续负责 `pending/approved/rejected` 转换和内部备注。

字段过滤必须发生在服务端。匿名和非上传者永远不返回 `review_comment`；非管理员永远不返回 `admin_internal_note`。
