// 对话/问答（RAG 页面与流式对话）
export default {
  // 页面标题区
  pageTitle: '回答必须能追溯到证据',
  pageDescription: '对话流、引用标记和证据 Side Sheet 联动，候选结构化记录明确标注为待审核。',
  // 会话列表
  conversations: '会话',
  noConversations: '暂无会话',
  done: '完成',
  newConversation: '新对话',
  // 对话流
  chatStream: '对话流',
  emptyHint: '可以问我一个超导问题，回答会带证据引用。',
  suggestion1: 'LaH10 的 Tc 是多少?',
  suggestion2: '超导温度高于 200K 的有哪些?',
  suggestion3: '笼状氢化物是什么?',
  waitingResponse: '等待响应...',
  // 输入区
  inputPlaceholder: '输入问题',
  inputPlaceholderExplore: '说说你的想法...',
  explore: '🔬 探索',
  // 证据面板
  evidencePanel: '证据面板',
  topResults: 'Top 结果',
  topHeaders: { compound: '化合物', value: '数值', reference: '文献' },
  filteredPapers: '筛选文献 ({count})',
  searchingEvidence: '正在检索证据...',
  evidenceEmptyHint: '发送问题后显示证据。',
  // 流式对话状态（useStreamingChat）
  exploreMode: '探索模式',
  analyzingQuestion: '正在分析问题...',
  analyzing: '正在分析...',
  filteringPapers: '筛选文献: {n} 篇 - {s}',
  querying: '🔍 正在查询: {name}',
  queryDone: '✅ 查询完成: {name}',
  exploreDone: '✅ 探索完成{label}',
  aiError: 'AI 错误',
} as const
