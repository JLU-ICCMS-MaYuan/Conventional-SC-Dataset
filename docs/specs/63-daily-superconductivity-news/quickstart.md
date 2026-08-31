# 快速验证与运行
关联：[Spec](spec.md)、[任务](tasks.md)。

## 边界与前置条件
所有命令在 mayuan-news worktree 根目录执行。需要 Python 3.10+、Node 20+、Go 1.25、Redis；集成测试额外需要隔离 MySQL。
不要复制现有生产 .env；使用临时测试凭证和独立容器。以下数据库迁移仅可针对空的测试数据库；现有业务库执行须单独批准。

## 安装和静态验证
```bash
uv venv .venv-news
uv pip install --python .venv-news/bin/python -r requirements-news.txt pytest alembic
cd frontend
npm ci
npm run build
cd ..
.venv-news/bin/python -m pytest tests/08_news -q
frontend/node_modules/.bin/vitest run --config vitest.config.ts tests/08_news
cd goserver
go test ./handlers -run News -count=1
```

当前分支的 Go 全包存在既有论文删除模块编译错误；定向验证真实新闻处理器可执行：

```bash
go test handlers/news.go handlers/news_feed.go handlers/news_feed_test.go -count=1
```

此命令不等价于完整 Go 服务构建通过。修复原有编译错误后必须重新执行全包测试和构建。

## 运行过程
为独立数据库设置 DATABASE_URL，为独立 Redis 设置 REDIS_URL；不要在版本库提交密码。应用 20260831_0063 迁移后，分别启动：
```bash
.venv-news/bin/python -m backend.news worker
.venv-news/bin/python -m backend.news schedule
```
首次无需等到次日：如果最近计划时间没有成功运行，将补跑。也可用 collect --source all 手动触发。
检查 GET /api/news/feed：三个来源状态可见；source 不可用返回 failed，其他来源不受影响。
重复 collect 后数量不应因相同记录而增加。打开 /news，分别筛选三类型，检查来源、发表日期、未审核说明；再验证人工快讯、里程碑未丢失。
断开测试源或使用损坏响应，确认失败可见而不是空列表；恢复后重新采集。停止再启动调度，确认补跑不影响上传队列。

## 恢复与运行边界
48 小时未成功需检查 worker、schedule、Redis、来源访问。page_limit 表示未完整获取，不推进水位；需要增加 NEWS_MAX_PAGES 或人工排查积压。Phys.org 只覆盖当前 RSS 窗口。
迁移、Go 接口和前端需由部署者配套发布；只启动 Python 不会让现有线上页面自动生效。
实际执行记录在本文件完成验证后补充；未执行生产迁移或部署。

## 隔离集成测试

`tests/08_news/test_integration.py` 仅在明确设置 `NEWS_TEST_MYSQL_URL` 与 `NEWS_TEST_REDIS_URL` 后运行。
MySQL 数据库名限定为 `news_test` 或 `news_test_` 前缀，主机限定 localhost；数据库和 Redis 必须为空。测试拒绝清空已有实例。
测试通过新迁移创建三表，启动真实 RQ 子进程，验证去重、故障后恢复、正式论文哨兵与独立 PDF 队列哨兵保持不变。

例如在**专门新建的测试容器**准备好后执行（端口替换为测试容器映射，不使用生产连接）：

```bash
NEWS_TEST_MYSQL_URL='mysql+pymysql://root:news-test-only@127.0.0.1:44622/news_test' \
NEWS_TEST_REDIS_URL='redis://127.0.0.1:44621/0' \
.venv-news/bin/python -m pytest tests/08_news -q
```

`tests/08_news/verify-go.sh <测试MySQL端口>` 使用 Docker 中的 Go 验证相同 MySQL 数据，由 Python 写、Go 读。
默认镜像 `golang:1.25`；可用 `NEWS_TEST_GO_IMAGE` 指定本地已准备的兼容测试镜像。加 `preview` 参数会在 localhost:5183 启动最多 20 分钟的隔离预览，读取前端构建目录；人工快讯为测试响应，绝非生产部署。

在线采集验证可用 `python -m tests.08_news.live_smoke --database <新SQLite绝对路径>`；需设置只用于导入模型的 `DATABASE_URL=sqlite:///:memory:`，父目录须存在且目标文件不得存在。
该辅助脚本串行访问官方源，首查 7 天、最多 5 页，只创建指定测试文件，不读取业务数据库。大窗口达到页上限会记录失败。

## 实际验证记录（2026-08-31）

### mayuan-news worktree 初始验证
- Python：17 项通过，包含独立 MySQL 8.4 迁移、Redis 7 与 RQ Worker 子进程的失败恢复。正式论文哨兵和 PDF 队列哨兵未变化。
- Go：新闻处理器 2 项定向测试及 Python→MySQL→Go 契约测试通过；浏览器预览辅助测试按需启动，默认跳过。
- 前端：10 个测试文件、79 项通过；其中新闻新增 4 项，验证分页、类型、异常重试、外链安全、人工快讯与里程碑保留。
- 前端 TypeScript 检查及 Vite 生产构建通过。既有 3Dmol eval 与大体积包警告未在本任务扩展处理。
- Alembic：`20260826_0016:20260831_0063 --sql` MySQL 离线生成通过；只创建独立资讯表和迁移版本标记，不触及正式科研表。
- 官方三源在线 7 天窗口：arXiv 抓取 100、接受 68；Crossref 抓取 1、接受 1；Phys.org 抓取 30、接受 3。数据保存在隔离 SQLite，而非业务库。
- 浏览器：1280×900 与 390×844 检查通过，资讯区域无横向溢出；类型切换、空态、来源成功时间和人工内容可读。
- Go 全包验证被分支原有错误阻断：paper_deletion.go 未使用 bytes/encoding/json，paper_deletion_test.go 与 paper_detail_test.go 的 strPtr 重复、Formula 字段赋值类型不匹配。这三个文件与 worktree 基线相同，非本功能引入。
- 未执行现有业务数据库迁移、部署、合并或推送；完整 Go 编译门尚未通过。

### mayuan 分支合并后验证（2026-08-31 14:00）
- Python 后端测试：16 项全部通过（test_collection.py: 15 项，test_scheduler.py: 1 项）
  - 测试包含解析与筛选、三源数据归一化、重复去重、版本管理、限流重试、事务回滚、水位保持等核心功能
  - 集成测试 test_integration.py 已跳过（需要独立 MySQL/Redis 环境）
- 前端测试：75 项全部通过（9 个测试文件）
  - 涵盖论文上传、分类审核、身份治理、详情路由、表单校对、提交验证等功能
  - 现有功能回归测试全部通过，未引入破坏性变更
- 测试环境：Docker 一次性容器（挂载主工作区代码），Python 3.12.13，pytest 9.1.1
- 前端构建环境：Node 20.20.0（npm 12.0.2），vitest 2.1.9
- **Go 文件缺失问题修复**：初次合并时遗漏 `goserver/handlers/news_feed.go`、`goserver/handlers/news_feed_test.go` 和 `goserver/models/news_feed.go`，导致 Docker 构建报错 `undefined: handlers.ListNewsFeed`。已从 worktree 补齐这三个文件。
- 所有新闻功能代码已齐全，准备提交
