import type { PropertyRecordDraft } from './propertyModules'

export interface FormDefinition {
  definition_key: string
  version: number
  target_kind: 'property_module' | 'property_record'
  module_code: string
  record_type?: string | null
  method_code?: string | null
  property_code?: string | null
  core_schema: Record<string, unknown>
  json_schema: Record<string, unknown>
  ui_schema: Record<string, unknown>
  status: 'draft' | 'published' | 'retired'
  checksum: string
}

export interface FormIssue { field: string; code: string; message: string }

export function validateRecordClient(record: PropertyRecordDraft, definition?: FormDefinition): FormIssue[] {
  const issues: FormIssue[] = []
  if (!record.record_key.trim()) issues.push({ field: 'record_key', code: 'schema_validation_failed', message: '记录键不能为空' })
  if (!record.name_raw.trim()) issues.push({ field: 'name_raw', code: 'schema_validation_failed', message: '名称不能为空' })
  if (!record.value_raw.trim()) issues.push({ field: 'value_raw', code: 'schema_validation_failed', message: '原始值不能为空' })
  if (record.record_type === 'predicted_tc' && !record.payload.calculation_conditions) issues.push({ field: 'payload.calculation_conditions', code: 'invalid_condition_type', message: '预测 Tc 需要计算 Conditions' })
  if (record.record_type === 'measured_tc' && !record.payload.experimental_conditions) issues.push({ field: 'payload.experimental_conditions', code: 'invalid_condition_type', message: '测量 Tc 需要实验 Conditions' })
  if (record.value_kind === 'range' && (record.value_min == null || record.value_max == null || record.value_min > record.value_max)) issues.push({ field: 'value_min', code: 'schema_validation_failed', message: '范围值无效' })
  if (definition && (definition.status === 'draft' || definition.module_code !== record.module_code)) issues.push({ field: 'definition_key', code: 'definition_not_available', message: '定义版本不可用于该记录' })
  return issues
}

export function definitionCacheKey(key: string, version: number, checksum: string): string { return `${key}@${version}:${checksum}` }

