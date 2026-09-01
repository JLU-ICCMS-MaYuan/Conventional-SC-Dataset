// 英文对话/问答文案。键集必须与 zh/rag.ts 完全一致——字典类型由中文侧推导，
// 缺键会在 `tsc -b` 阶段报错，不会静默回退。
export default {
  // 页面标题区
  pageTitle: 'Answers must trace back to evidence',
  pageDescription: 'The chat stream, citation markers and evidence side sheet work together; candidate structured records are explicitly marked as pending review.',
  // 会话列表
  conversations: 'Conversations',
  noConversations: 'No conversations yet',
  done: 'Done',
  newConversation: 'New Conversation',
  // 对话流
  chatStream: 'Chat Stream',
  emptyHint: 'Ask me a superconductivity question and the answer will come with evidence citations.',
  suggestion1: 'What is the Tc of LaH10?',
  suggestion2: 'Which superconductors exceed 200 K?',
  suggestion3: 'What are clathrate hydrides?',
  waitingResponse: 'Waiting for response…',
  // 输入区
  inputPlaceholder: 'Type a question',
  inputPlaceholderExplore: 'Share your idea…',
  explore: '🔬 Explore',
  // 证据面板
  evidencePanel: 'Evidence Panel',
  topResults: 'Top results',
  topHeaders: { compound: 'Compound', value: 'Value', reference: 'Reference' },
  filteredPapers: 'Filtered papers ({count})',
  searchingEvidence: 'Searching for evidence…',
  evidenceEmptyHint: 'Evidence appears after you send a question.',
  // 流式对话状态（useStreamingChat）
  exploreMode: 'Explore Mode',
  analyzingQuestion: 'Analyzing your question…',
  analyzing: 'Analyzing…',
  filteringPapers: 'Filtering papers: {n} - {s}',
  querying: '🔍 Querying: {name}',
  queryDone: '✅ Query finished: {name}',
  exploreDone: '✅ Exploration finished{label}',
  aiError: 'AI error',
} as const
