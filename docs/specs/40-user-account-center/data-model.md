# 数据模型：用户中心与账户安全

## users 扩展

- `affiliation VARCHAR(255) NULL`：同步到 Go 模型。
- `avatar_key VARCHAR(500) NULL`：仅保存受控对象键，不保存外部 URL。
- `orcid VARCHAR(19) NULL`：规范化格式，唯一索引允许多个 NULL。
- `research_interests JSON NULL`：字符串数组，最多 10 项。
- `session_version BIGINT NOT NULL DEFAULT 0`：由 #39 建立，本 Feature 修改密码时递增。

## profile_change_audit_events

- `id`：主键。
- `target_user_id`、`changed_by_user_id`：均指向保留的用户行，删除受限。
- `field_name`：仅允许 `real_name` 或 `affiliation`。
- `old_value`、`new_value`：可空，保存当时值。
- `created_at`：不可修改时间。

资料更新只在值实际变化时追加事件，与用户更新同一事务。

## 头像生命周期

1. 上传到临时文件并限制读取大小。
2. 解码、验证像素量、居中裁剪并输出统一正方形文件。
3. 原子移动到随机对象键。
4. 更新 `avatar_key`；事务提交后清理旧文件。
5. 失败时保留旧头像，孤儿新文件由安全清理任务回收。
