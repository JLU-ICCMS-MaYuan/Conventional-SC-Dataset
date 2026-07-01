# 认证、审批与审核

## 1. 这是什么业务

这一模块负责系统身份管理与内容可信度控制，包括用户注册登录、邮箱验证码、管理员申请、超级管理员审批、文献审核、全局文献管理和用户权限调整。

## 2. 角色与权限

| 角色 | 主要能力 |
|---|---|
| 匿名访客 | 浏览公开页面 |
| 普通用户 | 注册、登录、上传文献、批量上传 |
| 管理员 | 审核文献、编辑文献、查看全局文献 |
| 超级管理员 | 审批管理员、管理用户权限、删除用户 |

角色在数据库中由 `users.role` 表示，取值为 `user`、`admin`、`superadmin`。前端响应仍返回兼容用的 `is_admin` 和 `is_superadmin` 布尔值。

## 3. 用户注册与登录

### 3.1 注册流程
1. 用户提交邮箱、密码、真实姓名、是否申请管理员
2. 系统发送 6 位邮箱验证码
3. 用户调用验证接口完成邮箱验证
4. 普通用户直接激活
5. 管理员申请者进入待审批状态

### 3.2 登录约束
- 邮箱必须已验证
- 普通用户可直接登录
- 管理员必须已通过超级管理员审批

### 3.3 认证接口
- `POST /api/auth/register`
- `POST /api/auth/verify-email`
- `POST /api/auth/login`
- `GET /api/auth/me`

## 4. 管理员申请与超级管理员审批

### 4.1 管理员申请
- 管理员通过专用注册入口提交注册
- 邮箱验证成功后并不会立即拥有后台权限

### 4.2 超级管理员审批
- 超级管理员查看待审批管理员列表
- 可批准或拒绝申请
- 批准后记录审批时间与审批人
- 拒绝时会删除申请用户并发送通知

### 4.3 用户权限管理
- 超级管理员可以查看全部用户
- 可以修改 `role` 与 `is_approved`
- 可以删除其他用户，但不能删除自己

## 5. 文献审核业务

### 5.1 审核状态
- `pending`
- `approved`
- `rejected`
- `needs_revision`

### 5.2 审核动作
- 管理员可更新文献审核状态
- 更新审核状态时记录审核人、审核时间和审核备注

### 5.3 管理员可见后台能力
- 查看未审核文献
- 查看自己审核过的文献
- 查看全局文献列表
- 编辑文献信息
- 批量控制文献下属 `superconductor_records.show_in_chart`

## 6. 后台页面与接口

### 6.1 页面
- `/admin/dashboard`
- `/admin/superadmin`
- `/admin/papers`

### 6.2 主要接口
- `/api/admin/pending-approvals`
- `/api/admin/approve-user`
- `/api/admin/all-users`
- `/api/admin/users/{user_id}/permissions`
- `/api/admin/papers/{paper_id}/review`
- `/api/admin/papers/unreviewed`
- `/api/admin/my-reviews`
- `/api/admin/papers/all`

## 7. 邮件通知

- 注册验证码依赖邮件服务发送
- 管理员审批结果也可通过邮件通知
- 如果邮件服务未配置，实际可用性取决于部署环境和日志输出方式

## 8. 边界与限制

- 当前权限体系比较直接，没有细粒度 RBAC
- 审核流程围绕单篇文献，不支持复杂工作流引擎
- 用户提交文献数量统计依赖 `papers.uploaded_by_user_id`
- 邮件功能属于部署依赖项，不是纯前端能力
