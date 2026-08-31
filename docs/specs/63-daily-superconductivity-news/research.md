# 技术研究与取舍
关联：[Spec](spec.md)、[Plan](plan.md)。

## 基础库而非整仓复制
决策：HTTPX 负责超时与 HTTP，feedparser 解析 Atom/RSS，SQLAlchemy 事务，RQ/Redis 队列。理由：现有项目已用 Python/RQ；避免部署另一套数据库和阅读器。借鉴开源阅读器的稳定 ID、来源状态和幂等思想，不复制其实现代码。备选：Miniflux/TrendRadar 整体部署，因跨栈运维与功能重复不采用。
证据：[RQ 文档](https://python-rq.org/docs/)、[HTTPX 超时](https://www.python-httpx.org/advanced/timeouts/)。

## 官方来源和复用边界
- arXiv 用 API，分类 cond-mat.supr-con；稳定编号去版本后缀；保留摘要（CC0 元数据），原文指向摘要页。按更新日期分页，不把重复版本算新论文。[API 手册](https://info.arxiv.org/help/api/user-manual.html)、[使用条件](https://info.arxiv.org/help/api/tou.html)。
- Crossref 提供 DOI、作者、期刊和日期；摘要可能带版权，首版不存不展示。可选配置真实联系邮箱进入 polite pool，不编造邮件地址。[REST API](https://www.crossref.org/documentation/retrieve-metadata/rest-api/)、[访问说明](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication/)。
- Phys.org 使用官方超导 RSS，保持标题、链接，只展示订阅摘要并署名；不追抓全文，不采图片。[官方订阅说明](https://phys.org/feeds/)。
核验日期：2026-08-31。使用条件可能变化，维护时需重新核验。

## 精确去重
决策：按来源稳定编号和标准 DOI 合并；不按模糊标题合并。理由：标题相似可能是不同实验；同一 DOI 才提供确定关联证据。无 DOI 新闻仅按规范化原文 URL 去重，不与所报道论文混成一项。
例：arXiv v1 无 DOI → Crossref 期刊条目单独存在 → arXiv v2 补充同 DOI → 合为期刊类型，保留两个来源与预印本摘要来源。

## 范围和失败
采用标题明确的 superconduct*、超导、Josephson、Cooper pair、Meissner 词，arXiv/Phys.org 官方超导专栏直接认可。不会用 Tc、quantum 等宽泛词作为充分条件。
RSS 无法历史补全；API 以成功水位回补。重试上限和分页上限使故障有界；达到上限标失败而非漏数据后报成功。状态仅暴露稳定错误代码，不回显凭证/网络响应。
