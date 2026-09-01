// 论文详情与编辑页文案（Issue #74 全站中英文界面切换）。
//
// 六个叙述字段（summary、keywords_tags、methodology、key_finding、
// research_motivation、knowledge_graph_title）的内容是英文数据，渲染时原样展示，
// 绝不经过 t() 或语言判断（FR-014）；本字典只收录这些字段的「标签」。
export default {
  // ── 页面框架 ──
  backToUpload: '返回上传列表',
  myPapers: '我的论文',
  readOnlyMode: '只读模式',
  paperDetailTitle: '论文详情',
  submittedNotice: '论文已提交审核。普通用户不能在这里直接修改正式记录。',

  // ── 加载失败分流（PaperDetailPage）──
  failure: {
    invalid: '论文编号无效',
    forbidden: '无权查看该论文',
    missing: '论文不存在',
    error: '加载论文失败',
  },

  // ── 基础信息 ──
  basicInfo: '基础信息',
  fieldTitle: '标题',
  fieldYear: '年份',
  fieldJournal: '期刊',
  fieldAuthors: '作者',
  fieldAbstract: '摘要',
  fieldSummary: '论文总结 (LLM)',
  fieldKgTitle: '知识图谱标题 (LLM)',
  reviewStatus: '审核状态',
  dataSource: '数据来源',

  // ── 材料状态 ──
  materialStates: '材料状态',
  materialStateFallback: '材料状态 #{n}',
  fieldMaterialFamily: '材料家族',
  fieldElementCount: '不同元素种类数',
  fieldDimensionality: '材料维度',
  fieldCrystalSystem: '晶系',
  fieldSpaceGroupSymbol: '空间群符号',
  fieldSpaceGroupNumber: '空间群号',
  fieldSuperconductorKind: '超导类型',
  structureFamiliesLabel: '结构家族标签',
  noMaterialStates: '该论文暂无材料状态数据',

  // ── 压强条件 ──
  pressureSection: '压强条件',
  pressureValue: '压强：{value} GPa',
  rawText: '原文：{value}',
  pressureMin: '压强下限：{value} GPa',
  pressureMax: '压强上限：{value} GPa',

  // ── Tc 结果 ──
  tcSection: '临界温度 Tc',
  tcKind: '类型：{value}',
  tcValue: 'Tc：{value} K',
  tcRange: 'Tc 区间：{min} ~ {max} K',
  tcMethod: '判定方法：{value}',
  tcMethodCustom: '自定义方法：{value}',

  // ── 计算上下文 ──
  calculationContexts: '计算上下文',
  epcStrength: '电声耦合强度 λ：{value}',
  omegaLog: '对数声子频率 ωlog：{value} K',
  muStar: '库伦屏蔽常数 μ*：{value}',
  calcMethod: '计算方法：{value}',
  noValues: '（数值全为空）',

  // ── 其他物性 ──
  otherProperties: '其他物性',
  unnamedProperty: '未命名物性',
  rawValue: '原始值：{value}',
  parsedValue: '解析值：{value}',
  unitLabel: '单位：{value}',
  conditionNote: '条件说明：{value}',

  // ── 研究方法与发现 ──
  methodsFindings: '研究方法与发现',
  methodology: '研究方法',
  keyFinding: '关键发现',
  researchMotivation: '研究驱动力',

  // ── 侧栏 ──
  formulaLabel: '化学式',
  keywordsLabel: '关键词',
  structureIndex: '结构 #{n}',
  noStructure: '该记录暂无结构数据',

  // ── 3D 结构查看器 ──
  renderFailed: '3D 渲染失败',
  renderFailedDetail: '3D 结构渲染失败：{error}',

  // ── 我的论文列表（MyPapersList）──
  loadMyPapersFailed: '加载我的论文失败',
  emptyMyPapers: '还没有提交过论文。上传并提交审核后，论文会出现在这里，可随时只读复查。',
  paperIndexFallback: '论文 #{n}',

  // ── lib/paperDetailView 表格标签 ──
  // 实验测量方法；Allen-Dynes / McMillan / Eliashberg 等专有方法名不进字典，
  // 两种语言下均保留原文。
  tcMethods: {
    experimental: '实验测量',
    resistivity: '电阻法',
    magnetization: '磁化法',
    specific_heat: '比热法',
    calculated: '理论计算',
  },
  epcLambda: 'λ (电声耦合)',
} as const
