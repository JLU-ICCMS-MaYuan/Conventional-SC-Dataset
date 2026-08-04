# 角色与管理员审批

## 功能说明

管理 `user`、`admin` 和 `superadmin` 三类角色，以及管理员申请的批准状态和角色调整。

## 当前行为

- 安全层将 admin 和 superadmin 视为管理员，并要求管理员身份已批准。
- 超级管理员可以查看待审批管理员、批准申请、修改用户角色和管理其他管理员。
- 兼容逻辑仍可把旧 `is_admin`、`is_superadmin` 字段映射为角色。
- 防护逻辑限制超级管理员降低自身权限等危险操作。

## 工作流程

用户注册时申请管理员；账户进入待审批状态；超级管理员查看申请并批准；后续请求由角色依赖决定可访问的管理端点。

## 约束

- 角色值限制为 `user`、`admin`、`superadmin`。
- 用户管理和管理员审批中的部分操作只允许 superadmin。
- 旧布尔角色字段仍在兼容路径中，不能假设迁移已完全结束。

## 代码与测试

- `backend/api/admin.py`
- `backend/api/auth_routes.py`
- `backend/security.py`
- `backend/models.py`
- `frontend/src/pages/AdminPages.tsx`

## 相关变更记录

当前未发现可链接的已完成 Feature 或 Debug 记录。

## 已知问题

- 角色兼容字段的最终移除计划不属于当前事实。
