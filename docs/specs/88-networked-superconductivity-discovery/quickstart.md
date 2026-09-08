# 快速验证：联网超导资讯发现

## 前置条件

- 已应用资讯基础迁移和 #88 新迁移的隔离 MySQL。
- 已启动隔离 Redis、Python 依赖和 Go/前端测试工具链。
- 出版商或网页新闻搜索服务凭证仅通过环境变量提供，不写入日志。

## 定向验证

```bash
python -m pytest -q tests/07_researcher_community_forum/test_news_collection.py tests/07_researcher_community_forum/test_news_scheduler.py
(cd goserver && go test ./handlers ./models)
frontend/node_modules/.bin/vitest run --config vitest.config.ts tests/07_researcher_community_forum/news-feed.test.tsx
```

预期：固定来源样本能发现并去重；OpenAlex 请求至少滚动回看 30 天，只接受已发表期刊 article，低置信度主题不能单独放行，仅摘要命中时必须同时存在超导学术上下文；Crossref/OpenAlex 补充来源保留出版商链接；Phys.org 位于期刊论文栏但显示科研报道标签；Google News 样本归入社会/产业资讯；Redis 短暂故障后 Worker 继续消费。

## 隔离集成验证

集成测试只接受数据库名为 `news_test` 或以 `news_test_` 开头的本机空 MySQL，以及本机空 Redis；
测试会拒绝非空实例，不读取业务数据库配置。准备专用临时实例后运行：

```bash
NEWS_TEST_MYSQL_URL='mysql+pymysql://root:news-test-only@127.0.0.1:33308/news_test' \
NEWS_TEST_REDIS_URL='redis://127.0.0.1:6388/0' \
python -m pytest -q \
  tests/07_researcher_community_forum/test_news_collection.py \
  tests/07_researcher_community_forum/test_news_scheduler.py \
  tests/07_researcher_community_forum/test_news_integration.py \
  tests/07_researcher_community_forum/test_news_compose.py
```

该测试实际应用 #63 与 #88 的 MySQL 迁移，启动 RQ Worker，验证全部来源入队、单来源失败隔离、
两小时后重试恢复，并确认正式论文哨兵和 PDF 队列哨兵不变。随后可在同一测试库验证 Go 读取契约：

```bash
(cd goserver && \
  NEWS_TEST_MYSQL_DSN='root:news-test-only@tcp(127.0.0.1:33308)/news_test?parseTime=true' \
  go test handlers/news.go handlers/news_feed.go handlers/news_feed_test.go \
  -run News -count=1)
```

## 在线样本

先使用无写库的 `Sources.fetch("openalex", ...)` 检查真实 30 天窗口：DOI `10.1021/jacs.6c10135` 必须出现，已知 Zenodo 仓储 DOI 不得出现。再运行固定 `superconduct` 和 `超导` 的定时任务，检查来源状态、目标 DOI 或等价新记录、发现来源和原文链接。真实采集只写独立资讯表，不执行正式论文等业务数据写入；历史误收资讯应先备份，再在明确的数据维护操作中清理。

## 验收记录（2026-09-08）

- Python 定向与隔离集成：25 项通过；MySQL 8.4、Redis 7 和真实 RQ Worker 边界均已覆盖。
- Go：`go test ./...` 全包通过；Python 写入后的 MySQL 资讯由 Go 契约测试正确读取。
- 前端：单 Worker 全量 29 个测试文件、227 项测试通过；生产构建通过，仅保留既有 3Dmol `eval` 与大包体积警告。
- 在线只读 OpenAlex：30 天窗口扫描 830 条候选、接受 277 条；目标 DOI `10.1021/jacs.6c10135` 被识别为 `openalex` 发现、`acs` 原文来源，未接受 `10.5281/` Zenodo DOI。
- 本地历史表中既有 164 条 Zenodo 误收记录不由本 Feature 直接删除，已转交 [Issue #92](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/92) 以可审计流程处理。
- 本轮未迁移或修改现有业务数据库，未执行生产部署。
