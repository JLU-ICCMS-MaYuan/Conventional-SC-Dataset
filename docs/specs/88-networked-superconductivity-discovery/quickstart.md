# 快速验证：联网超导资讯发现

## 前置条件

- 已应用资讯基础迁移和 #88 新迁移的隔离 MySQL。
- 已启动隔离 Redis、Python 依赖和 Go/前端测试工具链。
- 出版商或网页新闻搜索服务凭证仅通过环境变量提供，不写入日志。

## 定向验证

```bash
pytest -q tests/07_researcher_community_forum/test_news_collection.py tests/07_researcher_community_forum/test_news_scheduler.py
go test ./goserver/handlers ./goserver/models
npx vitest run tests/07_researcher_community_forum/news-feed.test.tsx
```

预期：固定来源样本能发现并去重，OpenAlex/Crossref 补充来源保留出版商链接，Phys.org 位于期刊论文栏但显示科研报道标签；Google News 样本归入社会/产业资讯；Redis 短暂故障后 Worker 继续消费。

## 在线样本

使用 `superconduct` 和 `超导` 的定时任务运行一次，检查来源状态、DOI `10.1021/jacs.6c10135` 或等价新记录、发现来源和原文链接；不执行正式业务数据库写入。
