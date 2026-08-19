# 数据模型：论文全文解析与 LLM 自动分类

## 论文分类结果

- `paper_type`：`theoretical`、`experimental`、`review`、必要时 `unknown`。
- `theoretical_subtype`：`calculation`、`method`、`theory`，仅理论文章使用。
- `classification_reason`：面向用户的中文理由。
- `classification_evidence`：分段来源、页码/章节或原文片段。
- `classification_source`：`user` 或 `llm`。
- `classification_review_status`：新材料类型使用 `pending`，管理员处理后为 accepted/modified/merged/rejected。

## 材料类型

类型名称是可扩展字符串，不由固定枚举限制。现有 hydride、cuprate、iron_based、nickel_based、carbon、organic、others 作为建议项；用户或 LLM 可提交新名称。新名称在管理员确认前可用于论文提交，但标记待审核。

## 物性数据

`KeyProperty.article_type` 继续独立表示该条物性来自实验还是理论（现有 `e/t` 兼容）；不得由 `Paper.paper_type` 自动覆盖。

## 状态转换

上传中 → 解析中 → 分类中 → 成功；任一步 → 失败并返回原因。材料类型建议 → 待审核 → 接受/修改/合并/拒绝。失败状态不创建历史失败记录。
