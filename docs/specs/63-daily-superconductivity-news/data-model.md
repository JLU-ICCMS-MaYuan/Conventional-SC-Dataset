# 数据模型
关联：[Spec](spec.md)、[接口契约](contracts/news.md)。

## news_feed_items：统一公开条目
id：32 位 UUID 主键。kind：news/preprint/journal_article。title：非空文本；summary：纯文本；summary_source：arxiv/physorg/空。
source：主来源；url：原文 HTTP(S) URL；doi：规范化小写 DOI 或空；arxiv_id：去版本编号或空；version：非负整数。
authors：JSON 数组文本；journal：期刊名；links：JSON 数组文本，每项 source、url。
published_at：UTC ISO 8601 字符串或空；date_precision：day/month/year/unknown；source_updated_at：来源更新时间；first_seen_at/last_seen_at：采集时间。
排序：published_at 降序，first_seen_at 降序，id 降序；发表时间未知不冒充采集时间。索引(kind,published_at)、published_at。

## news_feed_identities：确定身份
key：SHA-256（source:稳定ID 或 doi:规范DOI），64 字符主键。
item_id：引用资讯主键，索引+外键。一个资讯可有多个身份。
URL 身份规范化仅用于去重，展示保留源链接。合并在事务内把全部身份转给保留项，再删重复项；只删资讯表内重复记录。

## news_feed_sources：来源运行状态
source：arxiv/crossref/physorg 主键。
status：running/success/failed；last_started_at、last_finished_at、last_success_at：UTC ISO 字符串。
error_code：稳定代码；fetched、accepted：上次完整运行统计。
未运行来源由 API 返回 never 状态，不伪造成功。
每次开始先持久化 running；成功水位取开始时刻（防止采集期间新增数据遗漏），完成时刻单独记录。失败不前移水位。
所有外部字符串在入库前限长。资讯存储与正式 papers 等无外键和写操作。

## 迁移与回滚
新迁移 20260831_0063 基于 20260826_0016，只创建三表及索引；新模型加入 Alembic metadata。
停止采集与新读取版本后可回退代码，数据表可保留；downgrade 删除三张资讯表，会丢失采集数据，必须另行确认。绝不自动执行生产迁移。
