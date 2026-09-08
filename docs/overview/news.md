# 超导快讯与最新论文

## 功能说明
/news 页面展示自动发现的超导新闻、预印本和期刊文章，另保留人工快讯和诺贝尔奖里程碑。
自动内容统一标注“自动采集，未经本站审核”，并提供来源、原文链接、发表时间和采集时间。
自动发现不等于论文入库，不进入正式科研数据库、审核队列、知识图谱或 PDF 解析流程。

## 当前行为
- arXiv 使用 cond-mat.supr-con 分类 API，按更新时间分页；去除版本编号形成稳定身份，版本升级更新原条目。
- Crossref 使用官方 API 和索引日期窗口，查询 `superconduct` 并按题名规则过滤，仅保存书目元数据，不存摘要。APS、ACS、Nature、Science、NSR、CPL、CPB、Materials Today 当前通过各自 DOI 前缀的 Crossref 补充发现，页面保留 `crossref` 发现来源与出版商原文来源；这不是逐家出版社官方 API/RSS 直连。
- OpenAlex 以固定主题滚动检查至少 30 天内的期刊文章，以弥补免费接口不能按更新时间增量查询的限制；请求端限定 `article` 和期刊主来源，本地再次拒绝明确未发表、未接收及 Zenodo 仓储 DOI。题名可直接证明相关性；自动关键词或主题必须达到最低置信度；只有摘要命中时，还必须同时出现临界参量、涡旋、配对、能隙或磁通钉扎等超导学术上下文。
- Phys.org 读取官方超导 RSS，保留原标题与原文链接，只展示订阅摘要，不抓文章全文。
- Google News RSS 用固定查询 `superconduct OR 超导` 发现公开索引的社会、产业、政策或股票资讯。它不保证覆盖未被搜索服务收录的网页或微信公众号内容。
- 相同 DOI 的论文条目在事务内合并，保留来源链接；只按确定标识去重，不按相似标题猜测。
- 自动条目保存 `content_type`、`display_kind`、发现来源、原文来源和相关性命中依据。Phys.org 的真实内容类型为科研报道，但按产品约定展示在期刊论文栏；Google News 为社会/产业资讯并展示在新闻栏。
- 页面按发表时间倒序，以 News、Preprints、Articles 三列并列展示；每列固定请求所属类型且每页 5 条，三列独立维护页码和翻页状态。只有年/月的日期明确标注精度。
- 来源状态显示最近成功时间与失败代码；区分加载中、暂无条目、请求失败、采集失败。
- GET /api/news 保持人工快讯数组契约；数据库错误返回 HTTP 500，不再伪装为空结果。

## 用户界面
- **品牌 Hero**：页面显示 `Superconduct Wiki / 超导维基`、吉林大学物质模拟方法与软件教育部重点实验室署名和平台能力简介；仅保留跳转 Explore（`/search`）的 `Start Exploring / 开始探索` 主按钮。
- **三列资讯流**：自动资讯分为 News、Preprints、Articles 三栏；桌面端三列并排、窄屏纵向排列，每栏最多显示 5 条并独立使用 `Previous`/`Next` 翻页。三栏保持等高，每个资讯槽位使用统一高度，分页控件固定在栏底部对齐。
- **简洁列表**：默认只显示标题、作者和类型标签，隐藏完整摘要避免占满屏幕。
- **详情抽屉**：点击任意条目，右侧滑出半屏抽屉展示完整信息（摘要、期刊、DOI、多来源链接、发表与采集时间）。
- **类型标签颜色**：新闻用浅蓝色（#e3f2fd），预印本用浅紫色（#f3e5f5），期刊论文用浅绿色（#e8f5e9），低饱和度视觉舒适。
- **交互反馈**：列表项悬停显示背景色变化和手型光标；点击关闭按钮或遮罩层关闭抽屉。
- **响应式设计**：抽屉在桌面端占 50% 宽度，移动端全屏显示。

## 工作流程
Python 采集进程负责外部访问、过滤、规范化和写表；Go 仅提供只读列表接口；前端读取持久化结果，不现场抓取。
独立 schedule 进程每分钟检查日任务，默认北京时间 08:00；停机后按成功水位补跑，失败一小时后重试。
Docker Compose 以 `news-scheduler` 运行该调度进程，并以 `news-worker` 专门消费 `scwiki-news` 队列；两者等待迁移成功和 Redis 健康后启动，容器重启时自动恢复。RQ Worker 在 Redis 短暂连接异常或空闲读超时后会重建连接继续消费。上传 Worker 不消费资讯队列。本地开发执行 `scripts/dev.sh start` 时也会默认启动这两个进程，日志和 PID 分别由 `scripts/dev.sh logs/status` 管理。
Redis 互斥锁防止并发采集。
任务最长 900 秒，单请求有限重试；失败不前移成功水位，不清空已有资讯。

## 数据与约束
新增 news_feed_items、news_feed_identities、news_feed_sources 三表，无正式 papers/材料/物性表写入。
来源请求固定白名单端点，响应限 5 MiB；arXiv 请求间隔至少 3.1 秒，其他来源至少 1 秒。
科学元数据与 Phys.org 连接不继承系统代理，避免本地代理故障中断论文采集；Google News 连接保留系统代理，以适应受限网络。单个来源的连接失败仍只记录该来源失败。
通用来源首次回看默认 7 天，后续重叠 2 天；OpenAlex 每次至少回看出版日期 30 天并依靠身份键去重。默认最多 100 页，超限、损坏响应和来源错误显式失败。
RSS 只能补回当前订阅窗口；已移除的历史内容无法保证找回。Crossref 标题筛选及 OpenAlex 的保守期刊/相关性规则会漏掉边界内容，不承诺覆盖全部超导论文。当前自动过滤只能阻止未来误收；规则收紧前写入的 Zenodo 历史条目由 [Issue #92](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/92) 通过独立、可审计的数据清理流程处理。
运行命令不会自动建表，生产迁移和进程部署仍需操作者明确执行。

## 代码与测试
- [采集适配](../../backend/news/sources.py)、[事务与去重](../../backend/news/service.py)、[日调度](../../backend/news/scheduler.py)、[命令入口](../../backend/news/__main__.py)。
- [数据模型](../../backend/news/models.py)、[#63 迁移](../../alembic/versions/20260831_0063_news_feed.py)、[#88 迁移](../../alembic/versions/20260903_0003_networked_news_discovery.py)。
- [Go 列表接口](../../goserver/handlers/news_feed.go)、[React 资讯组件](../../frontend/src/components/NewsFeed.tsx)。
- [Python 与页面测试](../../tests/07_researcher_community_forum/)、[Go 测试](../../goserver/handlers/news_feed_test.go)。
- [#88 完整运行与验证说明](../specs/88-networked-superconductivity-discovery/quickstart.md)、[Compose 部署修复](../specs/86-news-scheduler/quickstart.md)。

## 验证与运行边界
当前工作树通过 Python 单元测试、隔离 MySQL 迁移/RQ Worker 测试、Python 写入后 Go 读取的契约测试、Go 全包测试、页面交互测试和前端生产构建。
在线 OpenAlex 30 天窗口只读验证确认目标 ACS DOI 的发现与原文来源映射，并拒绝 Zenodo DOI；此结果不表示生产运行环境已部署。
浏览器使用真实新闻处理器与隔离数据库检查桌面/手机布局；人工快讯响应在该预览中为测试样本。
分支原有论文删除模块的 Go 编译问题阻断全包验证，未把定向新闻测试当作完整服务构建通过。

## 相关变更记录
[Feature #63](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/63) 与 [Spec](../specs/63-daily-superconductivity-news/spec.md)；[Feature #83](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/83) 完成 News 品牌与三列独立分页；[Bug #86](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/86) 补齐 Compose 中的 scheduler 和 worker；[Feature #88](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/88) 扩展联网发现与过滤；[Maintenance #92](https://github.com/JLU-ICCMS-MaYuan/SC-Wiki/issues/92) 跟踪历史 Zenodo 误收清理。
未完成协作事项以该 Issue 为准；本页不维护第二套任务状态。
