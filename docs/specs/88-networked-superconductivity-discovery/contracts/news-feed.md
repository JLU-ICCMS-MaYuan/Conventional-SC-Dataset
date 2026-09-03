# 资讯发现接口契约

## `GET /api/news/feed`

保留 `kind`、`page`、`page_size` 兼容参数。响应条目新增 `content_type`、`display_kind`、`discovery_source`、`original_source`、`relevance_evidence` 字段；`links` 中区分发现链接与原文链接。

`sources` 返回本次已配置来源的状态。数据库失败返回 HTTP 500，不能返回成功空列表。

## 采集任务

定时任务固定使用 `superconduct` 与 `超导`，不接受用户输入。来源适配器返回规范化记录；官方入口失败时可由 Crossref/OpenAlex 记录补充发现，但不得伪造官方来源。

## 安全

只保存公开元数据和允许展示的摘要片段；响应不得包含 API 密钥、完整上游正文、Redis key 或 RQ job id。
