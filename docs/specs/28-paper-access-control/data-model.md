# 数据模型：#28

## Paper 扩展

- `review_comment`：已有字段，上传者和管理员可见。
- `admin_internal_note`：nullable text，仅管理员可见。

## PaperPublicDTO

仅包含公开论文业务字段和状态允许的信息；不含源路径、reviewer id、内部备注。

## DuplicateResolution

`existing_paper_id/status/allowed_actions[]/reason`。动作取值为 `view`、`edit` 或 `none`，由服务端权限策略生成，前端不得自行猜测。
