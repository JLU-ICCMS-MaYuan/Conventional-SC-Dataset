# 角色与管理员审批

## 功能说明

管理 `user`、`admin` 和 `superadmin` 三类角色、公开研究身份、管理员资格申请和可审计的账号治理。

## 当前行为

- 所有已登录角色都进入 `/account`“用户中心”；左侧末项按角色显示“用户 / 管理员 / 超级管理员”，顶部头像菜单只保留退出登录。
- 用户中心可维护头像、一次性用户名、真实姓名、所属机构、ORCID 和研究方向，并修改密码。除邮箱外，已填写资料通过匿名 `/users/:username` 公开；公开页设置 `noindex`。
- 普通用户在邮箱已验证且真实姓名、所属机构齐全时可无理由提交管理员申请；同一时间只允许一个待审申请，可撤回、被拒后再次申请，申请保存资料快照。
- 超级管理员批准申请会把角色从 `user` 改为 `admin`；拒绝或管理员降级必须记录原因。申请、角色、封禁、解封、注销、实名/机构和用户名变更均保留审计。
- `/admin` 只允许 active admin；`/superadmin` 只允许 active superadmin。普通用户或管理员越权访问返回 403，superadmin 访问 `/admin` 时前端重定向 `/superadmin`。
- 超级管理员可以为任意账号带原因修改用户名；用户名更新和只追加审计事件在同一事务完成，管理员给自己更名后前端立即同步当前会话身份。
- 用户记录保存 `username`、`role`、`is_approved`、`is_email_verified`、`approved_at` 等字段；实名不是公开身份字段。

## 工作流程

普通用户注册并验证邮箱后即可使用；需要承担审核职责时从用户中心提交管理员资格申请；超级管理员在独立工作台审批。账号治理使用明确动作端点，要求原因、二次确认并在同一事务写用户状态与审计。

## 约束

- 角色值限制为 `user`、`admin`、`superadmin`。
- 图表组合、快讯、管理员申请、角色、用户状态和审计接口在后端强制 `SuperAdminRequired`，前端隐藏不作为安全边界。
- 封禁禁止登录和所有写操作，但保留公开资料与历史贡献并标注状态；注销保留用户与全部历史关系，移除公开资料和头像，历史贡献显示“已注销用户”。
- 超级管理员不能封禁、注销或降级自己；系统始终至少保留一名 active superadmin。
- 超级管理员更名必须提供 1–500 字符原因；更名不恢复或消耗历史账号的自助更名资格。

## 代码与测试

- `goserver/handlers/admin.go`
- `goserver/middleware/auth.go`
- `goserver/models/models.go`
- `backend/security.py`
- `backend/models.py`
- `frontend/src/pages/AdminPage.tsx`
- `frontend/src/pages/AccountPage.tsx`
- `frontend/src/pages/PublicUserPage.tsx`
- `frontend/src/pages/SuperAdminPage.tsx`
- `goserver/handlers/admin_applications.go`
- `goserver/handlers/governance.go`
- `goserver/handlers/username_test.go`

## 相关变更记录

- [Feature #31：唯一公开用户名与贡献榜身份](../../specs/31-community-ranking-visuals/spec.md)

## 已知问题

- `is_approved` 仍为兼容字段，不再表示注册审批或管理员资格状态。
