# 用户中心 API

## `GET /api/auth/me`

需要登录。返回当前 `user`、角色、邮箱验证状态、账号状态和用户中心展示所需字段；不得返回密码哈希。

## `GET /api/account/profile`

需要登录。返回本人头像 URL、用户名、更名资格、邮箱、真实姓名、机构、ORCID、研究方向和角色。

## `PATCH /api/account/profile`

输入可包含 `real_name`、`affiliation`、`orcid`、`research_interests`。部分更新；姓名/机构变化与审计同事务。

错误：`400` 字段校验，`409` ORCID 冲突，`401` 会话失效。

## `POST /api/account/avatar`

`multipart/form-data`，字段 `avatar`；最大 2 MiB，接受 JPEG/PNG/WebP。成功返回新头像 URL。

## `DELETE /api/account/avatar`

删除当前头像键并恢复默认首字符头像；重复删除幂等。

## `POST /api/account/change-password`

输入 `current_password`、`new_password`。成功更新密码、递增会话版本并返回 `204`；客户端必须清理本地会话。

错误：`400` 新密码不足 10 位，`403` 当前密码错误。
