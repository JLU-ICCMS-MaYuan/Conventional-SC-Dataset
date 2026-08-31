# 实施计划：每日超导资讯
**GitHub Issue**：[＃63](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/63)
**日期**：2026-08-31
**Spec**：[spec.md](spec.md)

## 摘要与技术上下文
Python 3.10+ 以 HTTPX、feedparser、SQLAlchemy 和 RQ/Redis 采集；MySQL 为持久层，Go 1.25/Gin/GORM 只读新表；React 19/TypeScript 5.6/MUI 7 展示。测试使用 pytest、SQLite、隔离 Redis/MySQL、Go httptest、Vitest 和浏览器。
新增最小 requirements-news.txt，不安装主 requirements 的科学计算栈，不升级前端核心依赖。
每来源请求分页大小 100，最多 100 页；超出上限或任务时限记录失败且不推进成功水位，可调整窗口。单页 UI 默认 20，上限 100。不做无依据延迟性能承诺。

## 质量门
| 来源 | 要求 | 设计 | 状态 |
| --- | --- | --- | --- |
| 用户隔离要求 | 主工作区不变 | 所有文件在 mayuan-news | 通过 |
| FR-003、FR-004 | 数据与 PDF 隔离 | 三张新表、固定 scwiki-news 队列 | 通过 |
| FR-007 | 权利与安全 | 固定官方地址、纯文本、摘要按来源控制 | 通过 |
| FR-006 | 不隐藏错误 | HTTP 400/500 与逐来源状态 | 通过 |
| FR-008 | 不迁移生产 | 迁移仅交付，测试使用独立数据库 | 通过 |

## 文档与源码结构
本目录含 Spec、Plan、Research、Data Model、Quickstart、Contracts、Tasks、Requirements Checklist。
- backend/news/{domain,sources,models,service,scheduler,__main__}.py：规范化、来源适配、存储、任务和命令。
- requirements-news.txt；alembic/versions/20260831_0063_news_feed.py；alembic/env.py。
- goserver/models/news_feed.go；goserver/handlers/news_feed.go；goserver/main.go；goserver/handlers/news.go。
- frontend/src/components/NewsFeed.tsx；frontend/src/pages/NewsPage.tsx。
- tests/08_news/；goserver/handlers/news_feed_test.go；vitest.config.ts。
- docs/overview/news.md、docs/overview/README.md、README.md。

## 设计决策与职责
Python 是新表唯一写入者；Go 不重新做科学筛选或合并。来源身份与 DOI 用唯一键映射到资讯；若后补 DOI 连接两个既有条目，在事务内合并身份和链接，以期刊元数据为主，arXiv 摘要保留来源标注。
调度进程每分钟检查北京时间最近一次计划时间；仅向固定独立队列投递三个来源任务。Redis 调度锁避免重复投递，采集锁避免跨进程并发请求，任务 900 秒超时且锁自动到期。状态记录最近开始、成功水位、结束、错误代码。失败一小时后可再入队。进程异常退出没有成功水位，下一轮可恢复。
HTTPX 单连接，每次请求前限速（arXiv 至少 3 秒，其他至少 1 秒）；429/5xx/网络错误最多三次，支持 Retry-After，过长等待报告限流后由调度重试。响应限制 5 MiB，不跟随任意重定向。只请求固定官方端点。
arXiv 按 lastUpdatedDate 倒序分页到上次成功水位（重叠两天），分类 cond-mat.supr-con；初次七天。Crossref 按索引日期窗口+superconduct 查询、cursor 分页，本地标题词筛选；无合法 DOI 不接收。Phys.org 当前 RSS 解析并按日期窗口筛选。缺字段/损坏日期不得推进完整成功水位，避免静默漏数。
采集开始记录 running；全部分页采集并在一个事务中入库后标记 success；失败保留原数据和水位。不执行外链内容、不记录原始响应或含 URL 的异常消息到公开状态。

## 需求到设计与任务映射
| 来源 | 设计/事实来源 | 任务 | 验证 |
| --- | --- | --- | --- |
| FR-001、FR-007、US1 | sources/domain | T002、T003 | 三源样本、错误/限流测试 |
| FR-002、FR-003、SC-001、SC-004 | models/service，资讯表 | T002、T003、T005 | 真实数据库去重、合并、接口上限 |
| FR-004、US2、SC-002 | scheduler，来源状态/Redis | T002、T003、T008 | 隔离队列与故障恢复 |
| FR-005、US3、SC-003 | NewsFeed/API | T004–T007 | 接口及 UI 交互 |
| FR-006 | handlers/NewsPage | T004–T007 | DB 错误和加载重试 |
| FR-008 | tests、迁移、文档 | T001–T009 | 隔离集成验证、文档核验 |

## 阶段与依赖
T001 文档门 → Python 测试/实现 → Go 测试/实现 → 页面测试/实现 → 集成验证 → 文档提交。
同文件串行；不同语言测试准备可并行。MVP 已包含三故事，因为自动更新与真实状态是用户基本承诺。

## 必要复杂度
身份表支持“先有无 DOI 预印本、后来有 DOI”的真实情况，单一 DOI 字段不足。独立调度进程使停机后能检查持久水位；仅使用一次 enqueue_in 无法证明每天持续执行。
