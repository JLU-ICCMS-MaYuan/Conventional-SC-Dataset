export const PROPERTY_MODULES = [
  { code: 'superconductive_properties', label: '超导性质' },
  { code: 'dynamical_properties', label: '动力学性质' },
  { code: 'thermodynamical_properties', label: '热力学性质' },
  { code: 'electronic_properties', label: '电子性质' },
] as const

export const PROPERTY_SCHEMA_VERSION = 2

export type PropertyModuleCode = typeof PROPERTY_MODULES[number]['code']
export type PropertyValueKind = 'number' | 'range' | 'text' | 'boolean'
export type PropertyRecordType = 'predicted_tc' | 'measured_tc' | 'property'

export interface PropertyRecordDraft {
  record_key: string
  module_code: PropertyModuleCode
  record_type: PropertyRecordType
  property_code: string
  custom_property_key?: string | null
  definition_key: string
  definition_version: number
  name_raw: string
  value_kind: PropertyValueKind
  value_raw: string
  value_number?: number | null
  value_min?: number | null
  value_max?: number | null
  value_text?: string | null
  value_boolean?: boolean | null
  uncertainty?: number | null
  unit_raw?: string | null
  canonical_unit?: string | null
  method_code?: string | null
  method_raw?: string | null
  criterion_code?: string | null
  criterion_raw?: string | null
  is_representative?: boolean
  structure_key?: string | null
  payload: Record<string, unknown>
  evidences?: unknown[]
}

export interface PropertyModuleDraft {
  module_key: string
  module_code: PropertyModuleCode
  definition_key: string
  definition_version: number
  display_order: number
  records: PropertyRecordDraft[]
}

let fallbackKeySequence = 0

export function newStableKey(prefix: string): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') return `${prefix}-${crypto.randomUUID()}`
  fallbackKeySequence += 1
  return `${prefix}-${Date.now()}-${fallbackKeySequence}`
}

export const emptyPropertyModule = (module_code: PropertyModuleCode, displayOrder: number): PropertyModuleDraft => ({
  module_key: newStableKey(`module-${module_code}`),
  module_code,
  definition_key: `module.${module_code}`,
  definition_version: 1,
  display_order: displayOrder,
  records: [],
})

export const emptyPropertyRecord = (module_code: PropertyModuleCode): PropertyRecordDraft => ({
  record_key: newStableKey(`record-${module_code}`),
  module_code,
  record_type: 'property',
  property_code: 'custom',
  custom_property_key: newStableKey('custom-property'),
  definition_key: `record.${module_code}.custom`,
  definition_version: 1,
  name_raw: '',
  value_kind: 'number',
  value_raw: '',
  value_number: null,
  payload: {},
  evidences: [],
})

export const clonePropertyRecord = (record: PropertyRecordDraft): PropertyRecordDraft => ({
  ...structuredClone(record),
  record_key: newStableKey('record-copy'),
  custom_property_key: record.custom_property_key ? newStableKey('custom-property') : record.custom_property_key,
})

const numberParameter = (value: unknown, unit: string) => (
  typeof value === 'number' ? { value_raw: String(value), value_number: value, unit_raw: unit } : undefined
)

export function convertLegacyPropertyModules(state: Record<string, any>): PropertyModuleDraft[] {
  if (Array.isArray(state.property_modules)) {
    return state.property_modules.map((module: PropertyModuleDraft, index: number) => ({
      ...module,
      definition_key: module.definition_key || `module.${module.module_code}`,
      definition_version: module.definition_version || 1,
      display_order: index,
      records: Array.isArray(module.records) ? module.records : [],
    }))
  }

  const records: PropertyRecordDraft[] = []
  for (const result of Array.isArray(state.tc_results) ? state.tc_results : []) {
    const experimental = result.result_kind === 'experimental' || result.tc_method === 'experimental'
    const methodCode = experimental ? (result.tc_method === 'experimental' ? 'resistivity' : result.tc_method) : (result.tc_method || 'unknown')
    const context = result.calculation_context || state.calculation_context || {}
    const parameters = Object.fromEntries(Object.entries({
      lambda_ep: numberParameter(context.lambda_ep, '1'),
      omega_log: numberParameter(context.omega_log_k, 'K'),
      mu_star: numberParameter(context.mu_star, '1'),
    }).filter(([, value]) => value !== undefined))
    records.push({
      record_key: newStableKey('legacy-tc'),
      module_code: 'superconductive_properties',
      record_type: experimental ? 'measured_tc' : 'predicted_tc',
      property_code: 'tc',
      definition_key: `record.superconductive_properties.${experimental ? 'measured_tc' : 'predicted_tc'}.${methodCode}`,
      definition_version: 1,
      name_raw: 'critical temperature',
      value_kind: result.tc_value_k != null ? 'number' : 'range',
      value_raw: String(result.value_raw ?? result.tc_value_k ?? ''),
      value_number: result.tc_value_k ?? null,
      value_min: result.tc_min_k ?? null,
      value_max: result.tc_max_k ?? null,
      uncertainty: result.uncertainty_k ?? null,
      unit_raw: result.unit_raw || 'K',
      canonical_unit: 'K',
      method_code: methodCode,
      method_raw: result.tc_method_custom ?? null,
      criterion_code: result.criterion_code ?? null,
      criterion_raw: result.criterion_raw ?? null,
      is_representative: Boolean(result.is_representative),
      payload: experimental
        ? { experimental_conditions: structuredClone(state.experimental_context || {}) }
        : { calculation_conditions: structuredClone(context.conditions || {}), parameters },
      evidences: structuredClone(result.evidences || result.evidence || []),
    })
  }

  for (const property of Array.isArray(state.properties) ? state.properties : []) {
    const rawValue = property.value_raw ?? property.value ?? ''
    const isNumber = typeof property.value_number === 'number' || typeof property.value === 'number'
    records.push({
      ...emptyPropertyRecord('superconductive_properties'),
      record_key: newStableKey('legacy-property'),
      name_raw: String(property.name_raw || property.name || ''),
      value_kind: isNumber ? 'number' : 'text',
      value_raw: String(rawValue),
      value_number: isNumber ? Number(property.value_number ?? property.value) : null,
      value_text: isNumber ? null : String(rawValue),
      unit_raw: property.unit || property.unit_raw || null,
      evidences: structuredClone(property.evidences || property.evidence || []),
    })
  }

  return records.length > 0
    ? [{ ...emptyPropertyModule('superconductive_properties', 0), records }]
    : []
}
