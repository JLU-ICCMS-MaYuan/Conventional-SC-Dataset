# 超导快讯与最新论文

## 功能说明
/news 页面展示自动发现的超导新闻、预印本和期刊文章，另保留人工快讯和诺贝尔奖里程碑。
自动内容统一标注“自动采集，未经本站审核”，并提供来源、原文链接、发表时间和采集时间。
自动发现不等于论文入库，不进入正式科研数据库、审核队列、知识图谱或 PDF 解析流程。

## 当前行为
- arXiv 使用 cond-mat.supr-con 分类 API，按更新时间分页；去除版本编号形成稳定身份，版本升级更新原条目。
- Crossref 使用官方 API 和索引日期窗口，查询 superconduct 并按标题规则过滤，仅保存书目元数据，不存摘要。
- Phys.org 读取官方超导 RSS，保留原标题与原文链接，只展示订阅摘要，不抓文章全文。
- 相同 DOI 的论文条目在事务内合并，保留来源链接；只按确定标识去重，不按相似标题猜测。
- 页面按发表时间倒序，以 News、Preprints、Articles 三列并列展示；每列固定请求所属类型且每页 5 条，三列独立维护页码和翻页状态。只有年/月的日期明确标注精度。
- 来源状态显示最近成功时间与失败代码；区分加载中、暂无条目、请求失败、采集失败。
- GET /api/news 保持人工快讯数组契约；数据库错误返回 HTTP 500，不再伪装为空结果。

## 用户界面
- **品牌 Hero**：页面显示 `Superconduct Wiki / 超导维基`、吉林大学物质模拟方法与软件教育部重点实验室署名和平台能力简介；仅保留跳转 Explore（`/search`）的 `Start Exploring / 开始探索` 主按钮。
- **三列资讯流**：自动资讯分为 News、Preprints、Articles 三栏；桌面端三列并排、窄屏纵向排列，每栏最多显示 5 条并独立使用 `Previous`/`Next` 翻页。
- **简洁列表**：默认只显示标题、作者和类型标签，隐藏完整摘要避免占满屏幕。
- **详情抽屉**：点击任意条目，右侧滑出半屏抽屉展示完整信息（摘要、期刊、DOI、多来源链接、发表与采集时间）。
- **类型标签颜色**：新闻用浅蓝色（#e3f2fd），预印本用浅紫色（#f3e5f5），期刊论文用浅绿色（#e8f5e9），低饱和度视觉舒适。
- **交互反馈**：列表项悬停显示背景色变化和手型光标；点击关闭按钮或遮罩层关闭抽屉。
- **响应式设计**：抽屉在桌面端占 50% 宽度，移动端全屏显示。

## 工作流程
Python 采集进程负责外部访问、过滤、规范化和写表；Go 仅提供只读列表接口；前端读取持久化结果，不现场抓取。
独立 schedule 进程每分钟检查日任务，默认北京时间 08:00；停机后按成功水位补跑，失败一小时后重试。
worker 仅消费 scwiki-news 队列，与上传解析队列分离；Redis 互斥锁防止并发采集。
任务最长 900 秒，单请求有限重试；失败不前移成功水位，不清空已有资讯。

## 数据与约束
新增 news_feed_items、news_feed_identities、news_feed_sources 三表，无正式 papers/材料/物性表写入。
来源请求固定白名单端点，响应限 5 MiB；arXiv 请求间隔至少 3.1 秒，其他来源至少 1 秒。
首次回看默认 7 天，后续重叠 2 天；默认最多 100 页。超限、损坏响应和来源错误显式失败。
RSS 只能补回当前订阅窗口；已移除的历史内容无法保证找回。Crossref 标题筛选会漏掉没有相关标题词的文章，不承诺覆盖全部超导论文。
运行命令不会自动建表，生产迁移和进程部署仍需操作者明确执行。

## 代码与测试
- [采集适配](../../backend/news/sources.py)、[事务与去重](../../backend/news/service.py)、[日调度](../../backend/news/scheduler.py)、[命令入口](../../backend/news/__main__.py)。
- [数据模型](../../backend/news/models.py)、[迁移](../../alembic/versions/20260831_0063_news_feed.py)。
- [Go 列表接口](../../goserver/handlers/news_feed.go)、[React 资讯组件](../../frontend/src/components/NewsFeed.tsx)。
- [Python 与页面测试](../../tests/07_researcher_community_forum/)、[Go 测试](../../goserver/handlers/news_feed_test.go)。
- [完整运行与验证说明](../specs/63-daily-superconductivity-news/quickstart.md)。

## 验证与运行边界
当前工作树通过 Python 单元测试、隔离 MySQL 迁移/RQ Worker 测试、Python 写入后 Go 读取的契约测试、页面交互测试和前端生产构建。
在线 7 天窗口采集验证三源均成功；此结果不表示生产运行环境已部署。
浏览器使用真实新闻处理器与隔离数据库检查桌面/手机布局；人工快讯响应在该预览中为测试样本。
分支原有论文删除模块的 Go 编译问题阻断全包验证，未把定向新闻测试当作完整服务构建通过。

## 相关变更记录
[Feature #63](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/63) 与 [Spec](../specs/63-daily-superconductivity-news/spec.md)。
未完成协作事项以该 Issue 为准；本页不维护第二套任务状态。
