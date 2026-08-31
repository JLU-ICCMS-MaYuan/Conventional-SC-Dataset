# 资讯接口和命令契约
关联：[Spec](../spec.md)。

## GET /api/news/feed
公开、只读、无触发采集副作用。query：kind 可省略或 news/preprint/journal_article；page 默认 1，page_size 默认 20、范围 1–100；page 最大 10000。非法值 HTTP 400。
HTTP 200 对象：items 数组、total、page、page_size、sources 数组。
items 字段与数据模型一致，authors/links 返回 JSON 数组，增加 notice 恒为“自动采集，未经本站审核”。
sources 固定三个来源，每项 source/status/last_started_at/last_finished_at/last_success_at/error_code/fetched/accepted。状态 never 表示尚未运行；运行超时可由页面根据开始时间提示未完成，超过 48 小时未成功提示可能未更新。
分页按 published_at、first_seen_at、id 倒序。成功空数组与失败 HTTP 500 分开；500 只给通用 error 字段。

## 旧接口兼容
GET /api/news 保留数组响应；数据库错误从错误的 200 改为 500。人工 CRUD 路由与权限不变。
前端自动资讯与人工快讯分别请求、分别显示错误，互不遮蔽；外链采用 http(s) 安全链接、target=_blank、rel=noopener noreferrer，文本不渲染任意 HTML。

## Python 命令
python -m backend.news schedule：持续调度；每 60 秒检查到期/失败任务。
python -m backend.news worker：只消费固定 scwiki-news 队列。
python -m backend.news collect --source arxiv|crossref|physorg|all：人工补跑，但同样受采集锁和请求限速约束。
DATABASE_URL、REDIS_URL 显式配置；默认不自动创建数据库。NEWS_DAILY_HOUR 默认 8、NEWS_TIMEZONE 默认 Asia/Shanghai；NEWS_INITIAL_DAYS 默认 7；NEWS_MAX_PAGES 默认 100；NEWS_CONTACT_EMAIL 可选。
错误代码：http_error、rate_limited、invalid_feed、invalid_record、page_limit、collection_error。详细诊断应在不泄露凭证前提下查本地日志。队列不提供公开触发 API。
