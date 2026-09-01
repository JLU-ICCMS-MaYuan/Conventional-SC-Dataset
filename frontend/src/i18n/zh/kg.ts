export default {
  relation: { first_discovery: '首次发现', experimental_validation: '实验验证', theoretical_basis: '理论基础', correction_or_dispute: '修正争议', development_extension: '发展延续', material_system_extension: '材料扩展', same_research_direction: '同方向', supporting_evidence: '支撑证据' },
  title: '论文之间的发现、验证与发展关系', description: '默认展示已审核里程碑论文，不把 Tc、压强、空间群等参数画成图谱节点', relationCount: '。当前共 {count} 条关系',
  selectHint: '点选节点或关系边', selectDescription: '点击论文节点查看详情和关联关系，点击边查看关系证据原文。', selectedPaper: '选中论文',
  year: '年份: {value}', journal: '期刊: {value}', authors: '作者: {value}', actions: '操作', expand: '展开一层关联', relationDetail: '关系详情', evidence: '证据原文',
} as const
