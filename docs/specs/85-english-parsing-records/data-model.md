# 数据模型：上传解析记录的英文输出与持久化语言一致性

**GitHub Issue**：[#85](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/85)

## 字段语言分类

| 数据位置 | 英文生成字段 | 保持原文的事实字段 |
| --- | --- | --- |
| 分段候选 | `methodology`、`key_findings`、`research_materials`、关系描述、材料/结构家族建议 | `metadata.title`、`metadata.abstract`、所有 `quote`、原始物性文本 |
| 汇总/草稿 | `summary`、`keywords_tags`、`methodology`、`key_finding`、`research_motivation`、`knowledge_graph_title`、生成的分类/关系/材料名 | 标题、摘要、作者、DOI、化学式、原始值/单位、证据 |
| 正式论文 | 上述论文级叙述字段及作为 AI 建议写入的相关文本 | 原文论文列和证据表 |

## 状态流转

```text
LLM chunk output
  -> validate/generated-fields-English
  -> chunk manifest + partial draft (Redis)
  -> summary normalize + validate
  -> final draft (Redis)
  -> submit validate
  -> MySQL Paper / scientific entities
```

任何验证失败都不得推进到下一个持久化节点；已有的上传任务失败与重试机制负责恢复。

## 历史数据

一次性脚本只扫描正式 MySQL 论文的已定义生成字段，逐行产生“已修复 / 跳过为空 / 无法安全修复”的审计结果。脚本成功验证后从仓库移除。Redis 任务数据按 TTL 自然消失，不做迁移。
