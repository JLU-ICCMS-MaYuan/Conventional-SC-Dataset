# 数据模型：管理员资格申请

## admin_applications

- `id`：主键。
- `user_id`：申请人，RESTRICT 删除。
- `real_name_snapshot`、`affiliation_snapshot`：提交时必填快照。
- `orcid_snapshot`、`research_interests_snapshot`：可选快照。
- `status`：`pending/withdrawn/approved/rejected`。
- `pending_guard`：仅 pending 时为 1，否则 NULL；与 `user_id` 组成唯一约束。
- `reviewed_by_user_id`、`rejection_reason`、`submitted_at`、`withdrawn_at`、`reviewed_at`。

状态转换：

```text
pending -> withdrawn
pending -> approved
pending -> rejected
```

终态不可再次转换；重新申请创建新行。

## user_governance_audit_events

- `event_type`：本 Feature 使用 `role_demoted`，#44 扩展封禁、解封和注销。
- `actor_user_id`、`target_user_id`。
- `old_role`、`new_role`、`old_status`、`new_status`。
- `reason`、`created_at`。

事件只追加，角色变更与事件同事务。
