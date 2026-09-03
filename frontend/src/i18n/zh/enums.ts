// 固定枚举的显示标签，按后端返回的 value 索引。
//
// 枚举 value 是接口契约的一部分（后端以集合校验，如 rag.py 的 PAPER_TYPES、
// scientific_drafts.py 的 SUPERCONDUCTOR_KINDS），只有标签随语言变化，提交值恒定不变。
// 目录接口 material_dimensionalities[].name 仍是中文，前端一律改按 value 查本表，
// 避免后端承担语言协商。
export default {
  // 材料维度：与 backend/services/classification_catalog.py 的 MATERIAL_DIMENSIONALITIES 对齐
  materialDimensionality: {
    zero_dimensional: '零维',
    one_dimensional: '一维',
    two_dimensional: '二维',
    three_dimensional: '三维',
    quasi_one_dimensional: '准一维',
    quasi_two_dimensional: '准二维',
    unknown: '未知',
  },
  // 晶系：与 backend/services/space_groups.py 的 CRYSTAL_SYSTEMS 对齐
  crystalSystem: {
    triclinic: '三斜',
    monoclinic: '单斜',
    orthorhombic: '正交',
    tetragonal: '四方',
    trigonal: '三方',
    hexagonal: '六方',
    cubic: '立方',
    unknown: '未知',
  },
  // Tc 计算与测量方法。专有方法名保留原文，中文界面补足方法语义。
  tcMethod: {
    unknown: '未知',
    experimental: '实验测量',
    mcmillan: 'McMillan 方法',
    allen_dynes: 'Allen-Dynes 方法',
    isotropic_eliashberg: '各向同性 Migdal-Eliashberg 方法',
    anisotropic_eliashberg: '各向异性 Migdal-Eliashberg 方法',
    scdft: '超导密度泛函理论（SCDFT）',
    other: '其他',
  },
  // 论文整体类型：与 backend/api/rag.py 的 PAPER_TYPES 对齐（unknown 为前端待选态）
  paperType: {
    theoretical: '理论文章',
    experimental: '实验文章',
    review: '综述文章',
    unknown: '暂不确定',
  },
  // 理论二级类型：与 backend/api/rag.py 的 THEORETICAL_SUBTYPES 对齐
  theoreticalSubtype: {
    calculation: '计算类',
    method: '方法类',
    theory: '理论模型与机制',
  },
  // 超导类型：与 backend/ingest/scientific_drafts.py 的 SUPERCONDUCTOR_KINDS 对齐
  superconductorKind: {
    conventional: '常规超导体（BCS超导体）',
    unconventional: '非常规超导体',
    unknown: '未知',
  },
  // 材料状态的数据来源性质
  stateKind: {
    theoretical: '理论',
    experimental: '实验',
    mixed: '理论与实验',
    unknown: '未知',
  },
  // 论文审核状态。needs_revision 是历史遗留状态，仍可能出现在旧数据中。
  reviewStatus: {
    pending: '待审核',
    approved: '审核完成',
    rejected: '已拒绝',
    needs_revision: '待审核（旧状态）',
  },
  // 用户角色
  role: {
    user: '用户',
    admin: '管理员',
    superadmin: '超级管理员',
  },
} as const
