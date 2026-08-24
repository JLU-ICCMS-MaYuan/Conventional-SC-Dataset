# 超级管理员治理 API

所有接口均要求 active superadmin。

## 用户列表

`GET /api/superadmin/users`：分页返回治理所需字段，不返回密码哈希。支持角色、账号状态、邮箱验证和关键词筛选。

## 治理动作

- `POST /api/superadmin/users/:id/ban`
- `POST /api/superadmin/users/:id/unban`
- `POST /api/superadmin/users/:id/deactivate`
- `POST /api/superadmin/users/:id/demote`（由 #42 定义）

请求统一包含 `reason`，不得包含任意目标状态或角色。成功返回更新后的治理摘要。

错误：`400` 原因或状态非法，`403` 非超管/自操作/最后超管保护，`404` 用户不存在，`409` 并发状态已变化。

## 审计读取

- `GET /api/superadmin/audits/profile-changes`
- `GET /api/superadmin/audits/username-changes`
- `GET /api/superadmin/audits/governance`

均支持分页、目标用户和时间范围；只读，不提供修改或删除端点。

## 内容管理

图表组合和快讯公开读取路径保持不变；创建、更新、删除和公开切换仅在 superadmin 权限下执行。可保留兼容 URL，但必须叠加 `AuthRequired + SuperAdminRequired`。
