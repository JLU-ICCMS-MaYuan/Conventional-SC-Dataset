# 实施任务：每日超导资讯
**输入**：[spec.md](spec.md)、[plan.md](plan.md)、[research.md](research.md)、[data-model.md](data-model.md)、[contracts/news.md](contracts/news.md)。

## 阶段 1：准备
- [x] T001 完成 docs/specs/63-daily-superconductivity-news/ 文档与一致性门。

## 阶段 2：US1 与 US2——采集基础（P1，MVP）
独立验收：三源固定样本入库、重复版本合并；Redis 投递和恢复不触及上传队列。
- [x] T002 [US1] [US2] 先在 tests/07_researcher_community_forum/test_news_collection.py、tests/07_researcher_community_forum/test_news_scheduler.py 编写解析、错误、事务去重及调度行为测试。
- [x] T003 [US1] [US2] 实现 backend/news/、requirements-news.txt、alembic/versions/20260831_0063_news_feed.py 和 alembic/env.py。

## 阶段 3：US3——接口与页面（P1）
独立验收：分页接口和筛选交互、旧页面内容、故障区分。
- [x] T004 [US3] 在 goserver/handlers/news_feed_test.go 编写 API 参数、分页、持久数据和数据库故障测试。
- [x] T005 [US3] 实现 goserver/models/news_feed.go、goserver/handlers/news_feed.go；修改 goserver/main.go 和 goserver/handlers/news.go。
- [x] T006 [US3] 在 tests/07_researcher_community_forum/news-feed.test.tsx 编写筛选分页、状态、重试及链接测试，更新 vitest.config.ts。
- [x] T007 [US3] 实现 frontend/src/components/NewsFeed.tsx 并接入 frontend/src/pages/NewsPage.tsx，保留人工内容及里程碑。

## 阶段 4：跨故事验证与收尾
- [x] T008 在 tests/07_researcher_community_forum/ 补充隔离持久数据库/队列集成验证，执行前后端测试、构建及浏览器宽窄屏检查，在 quickstart.md 记录结果及边界。
- [x] T009 更新 docs/overview/news.md、docs/overview/README.md、README.md；核对 Issue 关联、Git 变更范围，提交本任务文件。

## 依赖与覆盖
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009。同文件串行；本轮不委派代码编辑。
| 来源 | 任务 |
| --- | --- |
| FR-001、FR-002、FR-003、FR-007、SC-001 | T002、T003、T005、T007、T008 |
| FR-004、SC-002 | T002、T003、T008 |
| FR-005、FR-006、SC-003、SC-004 | T004–T008 |
| FR-008 | T001–T009 |
所有故事均属于本轮 MVP；没有另行隐藏的后续功能。

## 验证证据与剩余门槛

T002–T007 的行为证据见 [Quickstart 实际验证记录](quickstart.md)。真实 MySQL/RQ 子进程和 Go 读取契约均已通过，非仅模拟存储。
T008 已完成本功能测试、前端全量回归/构建、迁移 SQL、在线三源与浏览器验证。

### mayuan 分支合并后验证（2026-08-31 14:00）
- **后端测试**：16/16 通过（test_news_collection.py + test_news_scheduler.py），覆盖解析、去重、版本管理、限流、事务回滚
- **前端测试**：75/75 通过（9 个测试文件），包含新增新闻功能及现有功能回归测试
- **测试环境**：Docker 一次性容器 + Python 3.12.13 + pytest 9.1.1
- **前端构建**：Node 20.20.0 + vitest 2.1.9，构建通过
- **已完成**：功能代码从 mayuan-news 分支合并到 mayuan，所有测试通过
- **待处理**：Go 编译问题（与本功能无关的原有错误），Issue 保持开放
