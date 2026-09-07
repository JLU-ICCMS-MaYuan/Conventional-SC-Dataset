/**
 * 论文详情读取的公共提取逻辑。
 *
 * Issue #90 Read switch 后，全部物性只消费
 * `material_states[].property_modules[].records[]`。旧 `tc_results`、
 * `calculation_contexts` 与 `key_properties` 不再作为回退，避免迁移观察期双计数。
 *
 * 展示标签（Tc 判定方法、λ 名称）支持按语言解析：`collectPropertyRows(paper, t?)`
 * 的第二个参数传入 `useLanguage().t`；缺省时回退中文字典，保证旧调用方
 * （如 share.tsx，由 i18n 转换任务组负责接入）行为不变。
 */
import { dictionaries } from '../i18n'

/** 文案解析函数，与 useLanguage 返回的 t 签名对齐。 */
export type TranslateFn = (key: string) => string

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

/**
 * Tc 判定方法的显示标签。
 *
 * 实验测量方法（experimental、resistivity 等）查 paperDetail.tcMethods 字典；
 * Allen-Dynes / McMillan / Eliashberg 等专有方法名两种语言下均保留原文。
 * 传入 t 时按当前语言解析，缺省时回退中文字典，保证旧调用方行为不变。
 */
const tcMethodLabel = (method: string, t?: TranslateFn): string => {
  const key = `paperDetail.tcMethods.${method}`
  const translated = t
    ? t(key)
    : (dictionaries.zh.paperDetail.tcMethods as Record<string, string>)[method]
  // t 在两侧字典都缺键时返回键名本身，此时回退方法枚举原文。
  return translated && translated !== key ? translated : method
}

/** Tc 的判定方法作为备注，自定义方法优先于枚举值。 */
const tcNote = (result: any, t?: TranslateFn): string => {
  const method = textOrNull(result?.tc_method_custom)
    ?? (textOrNull(result?.tc_method) ? tcMethodLabel(result.tc_method, t) : null)
  const uncertainty = result?.uncertainty_k != null ? `± ${result.uncertainty_k} K` : null
  return [method, uncertainty].filter(Boolean).join('; ') || '-'
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
 *
 * `t` 可选：传入 `useLanguage().t` 时展示标签按当前语言解析（如 Tc 判定方法、
 * λ 名称）；缺省回退中文字典，旧调用方无需改动即可保持原行为。
 */
export function collectPropertyRows(paper: any, t?: TranslateFn): PaperPropertyRow[] {
  const tcRows: PaperPropertyRow[] = []
  const parameterRows: PaperPropertyRow[] = []
  const propertyRows: PaperPropertyRow[] = []
  const states: any[] = Array.isArray(paper?.material_states) ? paper.material_states : []

  for (const state of states) {
    const material = textOrNull(state?.material) || '-'
    const condition = conditionOf(state)

    for (const module of (Array.isArray(state?.property_modules) ? state.property_modules : [])) {
      for (const record of (Array.isArray(module?.records) ? module.records : [])) {
        const isTc = record?.record_type === 'predicted_tc' || record?.record_type === 'measured_tc'
        const target = isTc ? tcRows : propertyRows
        target.push({
          key: `record-${record?.record_key ?? target.length}`,
          material,
          label: isTc ? 'Tc' : (textOrNull(record?.name_raw) || textOrNull(record?.property_code) || '-'),
          value: isTc ? tcValueText({ tc_value_k: record?.value_number, tc_min_k: record?.value_min, tc_max_k: record?.value_max, value_raw: record?.value_raw, unit_raw: record?.unit_raw }) : propertyValueText({ value_number: record?.value_number, value_min: record?.value_min, value_max: record?.value_max, value_raw: record?.value_text ?? record?.value_raw, unit: record?.unit_raw }),
          condition,
          note: isTc ? tcNote({ tc_method: record?.method_code, uncertainty_k: record?.uncertainty }, t) : '-',
        })

        if (record?.record_type === 'predicted_tc') {
          const parameters = record?.payload?.parameters || {}
          const conditions = record?.payload?.calculation_conditions || {}
          const epcLabel = t ? t('paperDetail.epcLambda') : dictionaries.zh.paperDetail.epcLambda
          const values: Array<[string, unknown, string]> = [
            [epcLabel, parameters.lambda_ep, ''],
            ['ωlog', parameters.omega_log ?? parameters.omega_log_k, 'K'],
            ['μ*', parameters.mu_star, ''],
          ]
          for (const [label, rawValue, fallbackUnit] of values) {
            const wrapped = rawValue && typeof rawValue === 'object' ? rawValue as Record<string, unknown> : null
            const value = wrapped ? wrapped.value_number ?? wrapped.value_raw : rawValue
            if (value == null || value === '') continue
            parameterRows.push({
              key: `parameter-${record?.record_key ?? parameterRows.length}-${label}`,
              material,
              label,
              value: valueWithUnit(value, wrapped?.unit_raw ?? fallbackUnit),
              condition,
              note: textOrNull(conditions.calculation_code) || '-',
            })
          }
        }
      }
    }
  }

  return [...tcRows, ...parameterRows, ...propertyRows]
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
