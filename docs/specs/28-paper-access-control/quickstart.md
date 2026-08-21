# 验收指南：#28

1. 分别以匿名、普通登录用户、上传者和管理员请求 approved/pending/rejected 详情。
2. 确认其他用户可看 pending、不可看 rejected；上传者可见自己 rejected 的审核意见。
3. 检查普通响应不含 `admin_internal_note`、路径和审核人内部字段。
4. 尝试 PATCH 状态、路径和上传者，应被拒绝；修改白名单业务字段按权限成功。
5. 触发他人论文重复，确认使用统一详情或显示无权原因，不访问 my-uploads 详情。
