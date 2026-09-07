export const PROPERTY_MODULES = [
  { code: 'superconductive_properties', label: '超导性质' },
  { code: 'dynamical_properties', label: '动力学性质' },
  { code: 'thermodynamical_properties', label: '热力学性质' },
  { code: 'electronic_properties', label: '电子性质' },
] as const

export type PropertyModuleCode = typeof PROPERTY_MODULES[number]['code']
export type PropertyValueKind = 'number' | 'range' | 'text' | 'boolean'
export type PropertyRecordType = 'predicted_tc' | 'measured_tc' | 'property'

export interface PropertyRecordDraft {
  record_key: string
  module_code: PropertyModuleCode
  record_type: PropertyRecordType
  property_code: string
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
  unit_raw?: string | null
  canonical_unit?: string | null
  method_code?: string | null
  is_representative?: boolean
  payload: Record<string, unknown>
  evidences?: unknown[]
}

export interface PropertyModuleDraft {
  module_key: string
  module_code: PropertyModuleCode
  definition_key?: string
  definition_version?: number
  display_order: number
  records: PropertyRecordDraft[]
}

export const emptyPropertyRecord = (module_code: PropertyModuleCode, index = 0): PropertyRecordDraft => ({
  record_key: `record-${module_code}-${Date.now()}-${index}`,
  module_code,
  record_type: 'property',
  property_code: 'custom',
  definition_key: `record.${module_code}.custom`,
  definition_version: 1,
  name_raw: '',
  value_kind: 'number',
  value_raw: '',
  value_number: null,
  payload: {},
  evidences: [],
})

export const clonePropertyRecord = (record: PropertyRecordDraft, index = 0): PropertyRecordDraft => ({
  ...structuredClone(record),
  record_key: `record-copy-${Date.now()}-${index}`,
})

