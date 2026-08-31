/**
 * 论文详情读取的公共提取逻辑。
 *
 * 条件化科学数据模型（Issue #46、#51）把不同性质的量拆到了不同表：
 * - Tc 存 `tc_results`，外键 `material_state_id`
 * - λ / ωlog / μ* 存 `calculation_contexts`，同样挂在材料状态下
 * - 其余普通物性才进 `superconductor_properties`（详情接口的 `key_properties`）
 * - 晶体结构存 `structure_models`，经 `material_states[].structures[]` 返回
 *
 * 只读 `key_properties` 会漏掉前两类，只报告 Tc 的实验论文因此整块为空；
 * 读 `key_properties[].structure_text` 更是恒空——该字段在 Go 侧标记 `gorm:"-"`，
 * 从不落库，详情接口也不输出。Issue #59 已在详情页修正过一次，但探索页与社区页
 * 各自留了一份旧实现，本模块把三处收敛为同一来源。
 */

/** 关键物性表的一行，来源已归一，展示侧不需要再判断字段出处。 */
export interface PaperPropertyRow {
  key: string
  material: string
  /** 物性名（Tc、λ、ωlog 或普通物性的显示名） */
  label: string
  /** 已拼好单位的数值文本 */
  value: string
  /** 压强、温度等条件，取自所属材料状态 */
  condition: string
  note: string
}

/** 结构预览的一项，同时供探索页侧栏与社区页弹窗使用。 */
export interface PaperStructureItem {
  structure_text: string
  structure_format: string
  material: string
  name_note: string | null
  pressure_gpa: number | null
}

const textOrNull = (value: unknown): string | null => {
  if (value == null) return null
  const text = String(value).trim()
  return text || null
}

/** 材料状态的条件描述：压强优先用原文，缺失时回退解析值。 */
const conditionOf = (state: any): string => {
  const pressure = textOrNull(state?.pressure_raw)
    ?? (state?.pressure_value_gpa != null ? `${state.pressure_value_gpa} GPa` : null)
  const temperature = state?.temperature_value_k != null ? `${state.temperature_value_k} K` : null
  return [pressure, temperature].filter(Boolean).join(' · ') || '-'
}

/** 数值 + 单位，两者都缺时返回 '-'。 */
const valueWithUnit = (value: unknown, unit?: unknown): string => {
  const text = textOrNull(value)
  if (!text) return '-'
  const unitText = textOrNull(unit)
  return unitText ? `${text} ${unitText}` : text
}

/**
 * Tc 行：数值优先取 `tc_value_k`，只有区间时按 `min–max` 呈现。
 * 单臂区间保持单侧，不补造缺失的一端（Issue #54 的入库语义）。
 */
const tcValueText = (result: any): string => {
  if (result?.tc_value_k != null) return `${result.tc_value_k} K`
  const { tc_min_k: min, tc_max_k: max } = result || {}
  if (min != null && max != null) return min === max ? `${max} K` : `${min}–${max} K`
  if (min != null) return `≥ ${min} K`
  if (max != null) return `≤ ${max} K`
  return valueWithUnit(result?.value_raw, result?.unit_raw)
}

const TC_METHOD_LABELS: Record<string, string> = {
  experimental: '实验测量',
  resistivity: '电阻法',
  magnetization: '磁化法',
  specific_heat: '比热法',
  calculated: '理论计算',
  allen_dynes: 'Allen-Dynes',
  mcmillan: 'McMillan',
  eliashberg: 'Eliashberg',
}

/** Tc 的判定方法作为备注，自定义方法优先于枚举值。 */
const tcNote = (result: any): string => {
  const method = textOrNull(result?.tc_method_custom)
    ?? (textOrNull(result?.tc_method) ? (TC_METHOD_LABELS[result.tc_method] || result.tc_method) : null)
  const uncertainty = result?.uncertainty_k != null ? `± ${result.uncertainty_k} K` : null
  return [method, uncertainty].filter(Boolean).join('；') || '-'
}

/** 普通物性的数值：区间优先，其次解析值，最后原文。 */
const propertyValueText = (property: any): string => {
  if (property?.value_min != null) {
    return property.value_min !== property.value_max
      ? `${property.value_min}–${property.value_max}${property.unit ? ` ${property.unit}` : ''}`
      : valueWithUnit(property.value_max, property.unit)
  }
  return valueWithUnit(property?.value_number ?? property?.value_raw, property?.unit)
}

/**
 * 汇总一篇论文的全部关键物性行：Tc、计算参数、普通物性。
 *
 * 顺序固定为 Tc → 计算参数 → 普通物性：Tc 是超导论文的核心结论，应排在最前。
 * 计算参数中数值全为 NULL 的记录不产生行——它们对读者没有信息量，但后端仍然
 * 返回（读取侧不擅自筛选，见 `calculationContextsToDict` 注释）。
 */
export function collectPropertyRows(paper: any): PaperPropertyRow[] {
  const rows: PaperPropertyRow[] = []
  const states: any[] = Array.isArray(paper?.material_states) ? paper.material_states : []

  for (const state of states) {
    const material = textOrNull(state?.material) || '-'
    const condition = conditionOf(state)

    for (const result of (Array.isArray(state?.tc_results) ? state.tc_results : [])) {
      rows.push({
        key: `tc-${result?.id ?? rows.length}`,
        material,
        label: 'Tc',
        value: tcValueText(result),
        condition,
        note: tcNote(result),
      })
    }

    for (const context of (Array.isArray(state?.calculation_contexts) ? state.calculation_contexts : [])) {
      const params: Array<[string, unknown, string]> = [
        ['λ (电声耦合)', context?.lambda_ep, ''],
        ['ωlog', context?.omega_log_k, 'K'],
        ['μ*', context?.mu_star, ''],
      ]
      for (const [label, value, unit] of params) {
        if (value == null) continue
        rows.push({
          key: `calc-${context?.id ?? rows.length}-${label}`,
          material,
          label,
          value: valueWithUnit(value, unit),
          condition,
          note: textOrNull(context?.calculation_code) || '-',
        })
      }
    }
  }

  // 普通物性挂在论文上，用 material_state_id 回查所属状态的条件。
  const properties: any[] = Array.isArray(paper?.key_properties) ? paper.key_properties : []
  for (const property of properties) {
    const state = states.find(item => item?.id === property?.material_state_id)
    rows.push({
      key: `prop-${property?.id ?? rows.length}`,
      material: textOrNull(property?.material) || textOrNull(state?.material) || '-',
      label: textOrNull(property?.name) || textOrNull(property?.name_raw) || '-',
      value: propertyValueText(property),
      condition: state ? conditionOf(state) : '-',
      note: textOrNull(property?.condition_note) || '-',
    })
  }

  return rows
}

/**
 * 提取结构预览项。数据源是 `material_states[].structures[]`（`structure_models` 表），
 * 不是 `key_properties[].structure_text`——后者从不落库，读它必然得到空列表。
 */
export function collectStructures(paper: any): PaperStructureItem[] {
  const states: any[] = Array.isArray(paper?.material_states) ? paper.material_states : []
  return states.flatMap((state: any) => {
    const structures: any[] = Array.isArray(state?.structures) ? state.structures : []
    return structures
      .filter(item => textOrNull(item?.structure_text))
      .map(item => ({
        structure_text: String(item.structure_text),
        structure_format: textOrNull(item?.structure_format) || 'cif',
        material: textOrNull(state?.material) || '-',
        name_note: textOrNull(item?.space_group_symbol),
        pressure_gpa: state?.pressure_value_gpa ?? null,
      }))
  })
}

/** 3Dmol 只认 cif 与 vasp 两种格式，poscar 是 vasp 的别名。 */
export function viewerFormat(format: string | null | undefined): 'cif' | 'vasp' {
  return format === 'poscar' || format === 'vasp' ? 'vasp' : 'cif'
}
