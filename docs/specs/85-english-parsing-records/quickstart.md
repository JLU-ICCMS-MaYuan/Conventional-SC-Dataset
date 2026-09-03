# 验证路径：上传解析英文值与无建议审核表单

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

1. 在中文和英文界面分别上传受控论文，确认 Upload parsing records、只读草稿和最终表单中的生成字段均为英文，且不会显示 `AI 建议` / `AI suggestion`。
2. 上传含中文标题、摘要和引文的论文，确认这些原文以及 `quote` 保持中文；AI 方法、总结、分类和结论保持英文。
3. 向旧草稿注入 `ai_original`，确认页面忽略它；保存和提交后读取 Redis 与 `result.json`，确认不存在建议字段。
4. 提交含中文生成 `methodology` 的 canonical 草稿，确认返回带字段路径的 400，Redis/MySQL 没有违规写入。
5. 检查 Pb 活动任务，确认正式字段为英文、证据未改写、建议字段已删除。
