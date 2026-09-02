export default {
  title: '超导论文引用发展图谱', description: '箭头从引用论文指向被引论文；圆点越大，代表该论文在 SC-Wiki 内被更多已审核论文引用。',
  mysqlSource: '引用事实来自 SC-Wiki', materialFamily: '材料家族', superconductorKind: '超导类型', allKinds: '全部类型', conventional: '常规超导', unconventional: '非常规超导', applyFilters: '应用筛选', familyOption: '{name}',
  searchPaper: '按题名或 DOI 搜索论文', searchAction: '搜索论文', citationEdge: '引用关系',
  selectHint: '选择一篇论文', selectDescription: '点选圆点查看详情；上游是本文引用的来源，下游是后续引用本文的重要论文。', selectedPaper: '当前论文',
  yearUnknown: '年份未知', citationCount: '库内被引 {count} 篇', expandHint: '每次最多显示 5 篇，继续点击可按页展开。',
  loadUpstream: '显示上游论文', loadDownstream: '显示下游论文', moreUpstream: '查看更多上游（尚有 {count} 篇）', moreDownstream: '查看更多下游（尚有 {count} 篇）', noMoreUpstream: '没有更多上游论文', noMoreDownstream: '没有更多下游论文',
  origin: '源头', breakthrough: '突破', milestone: '领域里程碑', saveMarks: '保存里程碑',
  catalogLoadFailed: '材料家族目录加载失败', graphLoadFailed: '引用图谱加载失败', searchFailed: '论文搜索失败', neighborLoadFailed: '关联论文加载失败', markSaveFailed: '里程碑保存失败',
} as const
