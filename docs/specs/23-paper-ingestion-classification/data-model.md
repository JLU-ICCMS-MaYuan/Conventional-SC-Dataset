# 数据模型：论文全文解析与 LLM 自动分类

## 论文分类结果

- `paper_type`：`theoretical`、`experimental`、`review`、必要时 `unknown`。
- `theoretical_subtype`：`calculation`、`method`、`theory`，作为唯一新增的正式业务列。
- 分类理由、AI 原值和证据在审核期间保存在临时产物，审核完成后不进入正式数据库。

## 材料类型

类型名称是可扩展字符串。现有常用类型作为建议项；用户或 LLM 可提交自由文本，管理员在论文审核时确认最终文本。本 Feature 不建设全局类型表。

## 物性数据

`KeyProperty.article_type` 继续独立表示该条物性来自实验还是理论（现有 `e/t` 兼容）；不得由 `Paper.paper_type` 自动覆盖。

## 状态转换

Redis 处理状态为 `saving_file → extracting → reading → summarizing → ready`，任一步可进入 `failed`。MySQL 新审核状态只使用 `pending/approved/rejected`；历史 `needs_revision` 只兼容读取。处理状态不写 MySQL。

未提交任务以最后活动时间为基准保留 24 小时。`pending` 保留 AI 临时产物供审核，`approved` 或 `rejected` 后删除；已提交论文的 PDF 与 Markdown 保留但不公开。
