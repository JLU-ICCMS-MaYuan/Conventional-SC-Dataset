# 数据模型：英文规范值与原文证据

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

## 字段语言分类

| 数据位置 | 英文生成字段 | 保持原文的事实字段 |
| --- | --- | --- |
| 分段候选 | `methodology`、`key_findings`、`research_materials`、关系描述、材料/结构家族 | `metadata.title`、`metadata.abstract`、所有 `quote`、原始物性文本 |
| 汇总草稿 | `summary`、`keywords_tags`、`methodology`、`key_finding`、`research_motivation`、`knowledge_graph_title`、生成的分类/关系/材料名称 | 标题、摘要、作者、DOI、化学式、原始值、单位、证据 |
| 正式论文 | 上述生成字段 | 原文论文列和证据表 |

## 状态流转

```text
LLM chunk output
  -> validate/generated-fields-English
  -> chunk manifest + partial draft (Redis)
  -> summary normalize + validate (canonical English draft)
  -> final draft (Redis)
  -> submit validate
  -> MySQL Paper / scientific entities
```

`ai_original`、`ai_suggestions` 和 `suggestion_language` 不属于当前模型。旧数据可被读取并忽略；新状态、草稿、快照和正式数据均不得写入这些键。
