// 顶栏与侧边导航文案。
export default {
  // 侧边导航项。文案短，与 NAV_ITEMS 的 path 一一对应。
  news: '热点',
  search: '探索',
  knowledge: '脉络',
  share: '社区',
  upload: '上传',
  rag: '对话',
  tcPredict: '预测',

  // 顶栏
  accountMenu: '打开账户菜单',
  logout: '退出登录',
  login: '登录',
  mainNav: '主导航',
  notFoundTitle: '页面不存在',
  notFoundPath: '找不到地址 {path}',
  backHome: '返回首页',
  goUpload: '前往上传',
  forbidden: '403 · 无权访问此页面',
  backAccount: '返回用户中心',

  // 语言切换控件
  languageGroup: '界面语言',
  switchToZh: '切换为简体中文',
  switchToEn: '切换为英文',
  langZhShort: 'CH',
  langEnShort: 'EN',

  llmDefault: '默认模型',
  llmServerDefault: '服务端默认',
  llmCurrentServer: '当前服务端默认：{provider} · {model}',
  llmConfigure: '配置 AI 供应商',
  llmTitle: 'AI 供应商',
  llmModel: '模型名',
  llmKeyRequired: '模型名和 API Key 不能为空',
  llmKeyStorage: '密钥仅保存在你当前浏览器，不会上传或存入服务器数据库。',
  llmStoredKey: '已保存密钥：{key}',
  llmClear: '清除配置',
  llmTest: '测试连接',
  llmTesting: '测试中…',
  llmCancel: '取消',
  llmSave: '保存',
  llmConnected: '连接成功，耗时 {latency} ms',
  llmDefaultActive: '当前使用服务端默认模型',
  llmConnectionFailed: '连接失败',
} as const
