# 契约：英文规范值与来源证据

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

## 服务端语言验证器

分段结果、汇总草稿、浏览器草稿保存和提交前复用同一字段策略。只检测必须英文的生成字段是否含中日韩 Unicode 字符；原文事实字段不参与检测。

- 输入：结构化候选或草稿、作用域（`chunk` / `draft` / `submit`）。
- 输出：通过的值，或包含 JSON 路径、规则名和可展示消息的错误列表。
- 失败：草稿保存和提交返回 400；后台分段或汇总进入已有失败/重试状态，不能写入违规内容。

## 数据边界

`POST /api/upload-tasks` 只接收文件声明，不再接收语言快照。Worker 不得生成建议副本；Redis 草稿与 `result.json` 只保留 canonical `ai_values`、用户值和证据。提交快照必须过滤遗留 `ai_original`。

前端不得读取、传递或显示建议字段。`EvidenceNotes` 仅为非空 `quote` 显示默认折叠的“论文片段 / Source excerpt”；它保留来源位置与文本，但不得称为绝对准确的“原文”。
