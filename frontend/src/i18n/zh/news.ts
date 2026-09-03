// 快讯域文案：首页快讯 Hero、自动采集信息流（NewsFeed）、来源状态、详情抽屉与人工快讯（ManualNews）。
// 通用按钮（重试等）复用 common 域；仅此页专有的文案放在这里。
export default {
  // Hero 区
  heroAffiliation: '吉林大学 物质模拟方法与软件教育部重点实验室',
  heroTitle: '超导维基',
  heroSubtitle: '面向超导研究的 AI 驱动去中心化科研数据基础设施，融合可追溯科学数据、Tc 预测、超导知识图谱与 RAG 智能问答。',
  startExploring: '开始探索',

  // 诺贝尔奖里程碑
  nobelMilestones: '诺贝尔奖里程碑',
  // 里程碑条目是站点静态编辑内容（非论文数据），随界面语言切换。
  nobelMilestoneItems: [
    {
      year: 1913,
      name: 'Heike Kamerlingh Onnes',
      title: '液氦制备与超导电性的发现',
      feat: '1908年首次液化氦气（沸点4.2K），1911年发现汞在4.2K时电阻突然降至零——人类第一次观测到超导现象。这不仅证明了极低温下物质的新物态，更开启了长达百年的超导研究序幕。Onnes 当时在笔记中写下「Mercury practically zero」，这一时刻被铭刻在物理学的历史上。',
    },
    {
      year: 1972,
      name: 'John Bardeen, Leon Cooper, John Schrieffer',
      title: 'BCS 超导微观理论',
      feat: '1957年三人提出以姓氏命名的 BCS 理论，首次从量子力学微观机制完整解释了超导电性：电子通过晶格振动（声子）交换形成库珀对（Cooper Pair），在无电阻的宏观量子态中运动。Bardeen 因此成为历史上唯一两次获得诺贝尔物理学奖的人（第一次是1956年发明晶体管）。BCS 理论至今仍是凝聚态物理最重要的理论基石之一。',
    },
    {
      year: 1973,
      name: '江崎玲於奈, Ivar Giaever, Brian Josephson',
      title: '半导体与超导体中的隧穿效应',
      feat: '江崎玲於奈于1957年发现半导体中的电子隧穿效应（Esaki Diode），Giaever 于1960年实验验证了超导体中的单电子隧穿，而当时年仅22岁的研究生 Josephson 则从理论上预言了超导隧道结中库珀对的隧穿效应——即著名的约瑟夫森效应（Josephson Effect）。这一预言后来被精确验证（误差<10⁻¹²），成为超导电子学、SQUID 磁强计和电压标准的物理基础。',
    },
    {
      year: 1987,
      name: 'Georg Bednorz, Alex Müller',
      title: '铜氧化物高温超导体的突破',
      feat: '1986年，IBM 苏黎世实验室的 Bednorz 和 Müller 在镧钡铜氧（LaBaCuO）陶瓷材料中发现35K的超导电性，打破了此前 Nb₃Ge 保持13年的23K记录。更重要的是，这种氧化物陶瓷是传统 BCS 理论无法解释的新型超导体。这一发现引发了全球「超导淘金热」，随后朱经武、赵忠贤等人迅速将 Tc 推至液氮温区（77K）以上，使超导应用成本骤降，彻底改变了超导技术的产业化前景。',
    },
    {
      year: 2003,
      name: 'Alexei Abrikosov, Vitaly Ginzburg, Anthony Leggett',
      title: '第二类超导体与超流理论',
      feat: 'Ginzburg 和 Landau 于1950年提出超导相变的唯象理论（GL 理论），成功描述了超导态的宏观波函数行为。Abrikosov 在1957年基于 GL 理论预言了第二类超导体中的磁通涡旋晶格——即著名的 Abrikosov 涡旋，直接解释了实用超导磁体（如 MRI、粒子加速器磁铁）在高场下的工作机制。Leggett 则因超流³He 的理论工作分享了该奖项。这三位科学家的贡献共同奠定了现代超导应用的理论基础。',
    },
  ],

  // 信息流
  feedTitle: '超导快讯与最新论文',
  feedSubtitle: '官方来源每日采集 · 按发表时间排序',
  kindNews: '新闻',
  kindPreprint: '预印本',
  kindJournalArticle: '期刊论文',
  feedNewsColumn: '新闻',
  feedPreprintsColumn: '预印本',
  feedArticlesColumn: '期刊论文',
  autoCollected: '自动采集，未经本站审核',
  loadingFeed: '正在加载资讯…',
  feedLoadFailed: '资讯读取失败，请重试。此状态不代表没有新闻。',
  feedEmpty: '当前筛选下暂无资讯',
  feedEmptyHint: '可切换资讯类型，或查看下方来源是否已成功采集。',
  publishedAt: '发表：{date}',
  publishedLabel: '发表：',
  etAl: ' 等',
  pageInfo: '共 {total} 条 · 第 {page} / {pages} 页',
  prevPage: '上一页',
  nextPage: '下一页',

  // 来源更新状态
  sourceStatusTitle: '来源更新状态',
  sourcesNeedAttention: ' · 有来源需要关注',
  sourceItem: '{name}：{status}',
  errorCode: '（{code}）',
  sourceFailed: '采集失败，将自动重试',
  sourceNever: '尚未采集',
  sourceStalled: '上次采集未完成，等待恢复',
  sourceRunning: '正在采集',
  sourceStale: '超过 {hours} 小时未更新',
  sourceUpdated: '已更新',
  lastSuccess: '最后成功：{time}',
  noSuccessRecord: '暂无成功记录',
  timeUnknown: '时间未知',
  physorgNote: 'Phys.org 仅覆盖当前订阅窗口；停机期间已移除的历史新闻可能无法补回。',

  // 详情抽屉
  authorLabel: '作者：',
  journalLabel: '期刊：',
  sourceLabel: '来源：',
  versionLabel: '版本：',
  collectedLabel: '采集：',
  summaryLabel: '摘要',
  summarySourceLabel: '摘要来源：',
  doiLabel: 'DOI：',
  originalLinks: '原文链接',

  // 日期显示
  dateNotProvided: '日期未提供',
  yearOnly: '{year} 年',
  monthOnly: '{month}（仅提供月份）',

  // 人工快讯
  manualTitle: '人工快讯',
  loadingManual: '正在加载人工快讯…',
  retryManual: '重试人工快讯',
  manualLoadFailed: '人工快讯读取失败',
  manualEmpty: '暂无人工发布的快讯。',
} as const
