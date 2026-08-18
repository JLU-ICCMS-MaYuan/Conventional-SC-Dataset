# II. 超导数据去中心化维护与验证

## 功能定义

Decentralized Maintenance and Verification 指 SC-Wiki 对用户提交和系统导入的数据进行维护、审核、权限管理、迁移和恢复的能力。这里的 decentralized 表示维护权不只集中在代码作者手里，而是通过普通用户、管理员和超级管理员的角色分工来完成数据治理。

## 当前状态

当前状态是已部分落地。用户注册、邮箱验证、管理员申请、超级管理员审批、论文审核、结构审核、全局文献管理、用户权限管理、图表显示控制、JSON 导入导出、Alembic 迁移和备份建议都已经有代码或文档依据。尚未落地的是复杂工作流引擎、细粒度 RBAC、逐条超导记录的完整编辑体验、审核者排行和社区式争议解决机制。

## Roles

系统当前有四类角色。

匿名访客可以浏览公开页面、元素体系、图表和公开文献，但不能上传和进入后台。

普通注册用户可以注册、邮箱验证、登录，并提交论文、超导记录和结构数据。

管理员可以审核论文、编辑论文基础信息、查看全局文献列表、批量控制图表显示、审核晶体结构。

超级管理员可以审批管理员申请、管理用户权限、删除用户、执行更高风险的维护动作。

角色由 `users.role` 表示，当前主要取值为 `user`、`admin` 和 `superadmin`。前端和部分 API 仍保留兼容字段，如 `is_admin` 和 `is_superadmin`。

## Verification Workflows

论文审核围绕 `papers.review_status` 进行，状态包括 `pending`、`approved`、`rejected` 和 `needs_revision`。审核动作会记录审核人、审核时间和审核意见。

结构审核围绕 `superconductors_structures.review_status` 和 `is_default` 进行。管理员审核通过某个结构后，同一化学式、空间群和压强粒度下的最新通过版本会成为默认结构，旧默认结构保留历史但不再作为默认展示。

图表展示控制不是简单等同于论文审核。首页 Tc-Pressure 和 Tc-Year 图表依赖 `superconductor_records.show_in_chart`，管理员可以批量控制这些记录是否进入图表。Tc-Year 还要求记录有关联论文年份。

## Maintenance and Operations

旧的 X 类能力，也就是数据导入导出、迁移和备份，最适合并入本功能。原因是它们不是面向终端研究者的独立研究功能，而是数据长期可信、可迁移、可恢复的维护基础。

当前维护能力包括：

- Alembic 管理 MySQL 表结构。
- `backend.init_db` 初始化周期表基础元素数据。
- JSON 导入导出覆盖用户、论文、超导记录和晶体结构。
- 导入流程可在缺少可用上传用户时创建本地导入用户。
- 运维文档中给出启动、环境变量、MySQL、备份和服务管理建议。
- 当前 `backend/main.py` 启动事件会调用 `initialize_sqlite_database()`，这说明本地开发仍保留 SQLite 初始化路径。

## Code and API Evidence

主要页面包括 `/admin/register`、`/admin/dashboard`、`/admin/superadmin`、`/admin/papers` 和 `/admin/users`。

主要接口包括：

- `POST /api/auth/register`
- `POST /api/auth/verify-email`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `GET /api/admin/all-users`
- `PUT /api/admin/users/{user_id}/permissions`
- `DELETE /api/admin/users/{user_id}`
- `GET /api/admin/pending-approvals`
- `POST /api/admin/approve-user`
- `POST /api/admin/papers/{paper_id}/review`
- `GET /api/admin/papers/all`
- `PUT /api/admin/papers/{paper_id}`
- `POST /api/admin/papers/batch-review`
- `POST /api/admin/papers/batch-chart-visibility`
- `GET /api/admin/records/all`
- `POST /api/admin/records/batch-chart-visibility`
- `POST /api/structures/{structure_id}/review`

## Boundary

维护与验证不等于社区论坛。当前维护主要由管理员角色执行，没有评论、投票、点赞、弹幕、公开争议讨论或专家共识流程。它也不等于数据上传，上传解决“数据如何进入系统”，维护与验证解决“数据如何变得可信、可恢复、可持续管理”。

## Future Direction

下一步可以补齐逐条 `superconductor_records` 编辑体验、审核者贡献统计、数据变更历史、批量导入的新结构适配、备份自动化和更清晰的公开审核轨迹。
