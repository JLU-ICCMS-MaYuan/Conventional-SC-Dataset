# API 契约：公开用户名与更名

## 用户名可用性

`GET /api/auth/username-availability?username=<value>`

- 匿名可访问。
- `200`：`{"available": true}` 或 `{"available": false, "reason": "..."}`。
- 只返回可用状态与规则原因，不返回账号资料。
- 该结果不预留名称，最终提交仍可能因并发返回冲突。

## 注册

`POST /api/auth/register`

```json
{
  "email": "person@example.org",
  "password": "secret",
  "username": "Researcher_01",
  "real_name": "可省略",
  "is_admin": false
}
```

- `username` 必填，`real_name` 可选。
- `409`：邮箱或用户名已占用。
- `400`：用户名格式、保留名称或 `sc_` 前缀不合法。
- 新账号 `username_change_allowed=false`。
- 响应不得返回 `real_name`。

## 登录

`POST /api/auth/login`

- 请求仍只接受 `email` 和 `password`。
- 用户响应增加 `username` 和 `username_change_allowed`，不返回 `real_name`。

## 历史账号自助更名

`PATCH /api/auth/username`

```json
{"username": "ChosenName"}
```

- 需要有效登录。
- 仅 `username_change_allowed=true` 的账号可调用。
- `200` 返回更新后的客户端用户 DTO。
- `403`：没有自助更名资格。
- `409`：名称已占用；资格保持不变。
- `400`：名称不合法；资格保持不变。

## 超级管理员更名

`PUT /api/admin/users/{id}/username`

```json
{"username": "CorrectedName", "reason": "修正注册时的拼写错误"}
```

- 仅超级管理员可调用，原因去除首尾空白后必须为 1–500 字符。
- 用户名更新和审计写入必须同事务完成。
- 不改变目标账号 `username_change_allowed`。

## 更名审计列表

`GET /api/admin/username-audit-events`

- 仅超级管理员可访问。
- 返回事件 ID、目标用户 ID、操作者用户 ID、操作者用户名、旧用户名、新用户名、原因和时间。
- 不返回实名。

## 社区贡献榜兼容扩展

`GET /api/community/contributions`

每个排名项：

```json
{
  "rank": 1,
  "user_id": 7,
  "username": "Researcher_01",
  "display_name": "Researcher_01",
  "avatar_text": "R",
  "contribution_count": 18
}
```

- `username` 是权威公开身份。
- `display_name` 是兼容别名，必须与 `username` 完全相同。
- 不返回邮箱、实名、角色或审批字段。
