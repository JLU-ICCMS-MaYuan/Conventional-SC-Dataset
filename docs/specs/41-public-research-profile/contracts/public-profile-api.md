# 公开科研身份 API

## `GET /api/users/:username`

匿名可访问。

成功 `200`：

```json
{
  "username": "alice",
  "avatar_url": "/api/users/alice/avatar",
  "real_name": "Alice Zhang",
  "affiliation": "Jilin University",
  "orcid": "0000-0002-1825-0097",
  "research_interests": ["高压超导"],
  "role_badge": "管理员",
  "is_banned": false
}
```

字段为空时可省略或返回 null，但不得出现邮箱、用户 ID、验证、权限和审计字段。普通用户的 `role_badge` 必须为空。

注销账号和不存在用户名均返回 `404`；历史贡献的匿名化由贡献查询负责。

## `GET /api/users/:username/avatar`

仅解析受控头像键。不存在或已注销时返回 `404`，前端使用用户名首字符回退。响应提供内容类型、ETag 或等价缓存头，不接受任意路径参数。
