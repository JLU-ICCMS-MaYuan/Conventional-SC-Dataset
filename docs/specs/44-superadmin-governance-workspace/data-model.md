# 数据模型：超级管理员治理

## users.account_status

- `active`：允许按角色登录和操作。
- `banned`：禁止登录和全部写操作；公开资料保留。
- `deactivated`：永久不可登录；公开资料与头像键清空，历史关系保留。

每次封禁、解封、注销或敏感角色变化递增 `session_version`。

## user_governance_audit_events

- `id`：主键。
- `actor_user_id`、`target_user_id`：RESTRICT 外键。
- `event_type`：`role_promoted/role_demoted/banned/unbanned/deactivated`。
- `old_role`、`new_role`、`old_status`、`new_status`。
- `reason`：必填，最多 1000 字符。
- `created_at`：不可修改。

## 状态转换

```text
active -> banned -> active
active -> deactivated
banned -> deactivated
```

`deactivated` 为终态。注销清空 `avatar_key/real_name/affiliation/orcid/research_interests`，但保留 email 与 username 唯一占位及所有外键。

## 并发约束

- 自操作在领域服务中直接拒绝。
- 涉及 superadmin 角色或状态的变更必须锁定 active superadmin 集合并保证更新后数量至少 1。
- 用户更新与治理审计在同一事务；头像文件在事务提交后清理。
