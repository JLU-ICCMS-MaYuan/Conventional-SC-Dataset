# 数据模型：联网超导资讯发现

## 发现条目

现有 `news_feed_items` 保留兼容字段，并新增：

| 字段 | 含义 | 约束 |
|---|---|---|
| `content_type` | `peer_reviewed`、`preprint`、`research_report`、`social_industry` | 表示真实内容语义 |
| `display_kind` | `news`、`preprint`、`journal_article` | 表示页面展示栏位；Phys.org 为 `journal_article` |
| `discovery_source` | 实际发现该条目的外部服务 | 不等同原文出版商 |
| `original_source` | 原文站点或出版商标识 | 可为空但必须有安全 URL |
| `relevance_evidence` | 命中的字段和关键词摘要 | 不保存完整上游响应 |

`kind` 在迁移期间保留作为 `display_kind` 的兼容别名；新写入同时设置两者。

## 身份与生命周期

优先使用 `doi:`、`arxiv:` 或规范化原文 URL 身份；同一条目可关联多个发现来源和原文链接。采集失败不前移来源成功水位，不删除已有条目。

## 来源状态

`news_feed_sources` 继续记录每个来源的运行状态、最近成功时间、抓取和接受计数；来源标识长度需支持出版社和聚合源名称。
