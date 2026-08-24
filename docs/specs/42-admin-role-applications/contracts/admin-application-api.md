# 管理员申请 API

## `POST /api/account/admin-applications`

需要 active user。无请求正文；服务端从当前资料生成快照。成功 `201` 返回申请。

错误：`400` 姓名/机构缺失，`409` 已有 pending 或角色不为 user。

## `GET /api/account/admin-applications`

返回本人全部申请历史，按提交时间倒序。

## `POST /api/account/admin-applications/:id/withdraw`

仅本人且仅 pending 可撤回。成功 `200`；终态返回 `409`。

## `GET /api/superadmin/admin-applications`

仅 superadmin，支持状态、分页和时间筛选。

## `POST /api/superadmin/admin-applications/:id/approve`

仅 superadmin；请求无目标角色字段。事务内把 pending 置 approved 并将 user 改为 admin。

## `POST /api/superadmin/admin-applications/:id/reject`

输入 `reason`，非空且最多 1000 字符。事务内置 rejected。

## `POST /api/superadmin/users/:id/demote`

输入 `reason`。仅目标为 admin 时允许；不得操作自己。事务内改为 user 并追加治理审计。
