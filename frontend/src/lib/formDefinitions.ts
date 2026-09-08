import { api } from './api'
import type { PropertyRecordDraft } from './propertyModules'

export interface JsonSchema {
  type?: 'object' | 'array' | 'string' | 'number' | 'integer' | 'boolean' | 'null'
  title?: string
  description?: string
  properties?: Record<string, JsonSchema>
  items?: JsonSchema
  required?: string[]
  enum?: Array<string | number | boolean>
  const?: unknown
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
  additionalProperties?: boolean | JsonSchema
  [key: string]: unknown
}

export interface FormDefinition {
  definition_key: string
  version: number
  target_kind: 'property_module' | 'property_record'
  module_code: string
  record_type?: string | null
  method_code?: string | null
  property_code?: string | null
  core_schema: JsonSchema
  json_schema: JsonSchema
  ui_schema: Record<string, any>
  status: 'draft' | 'published' | 'retired'
  checksum: string
}

export interface FormIssue { field: string; code: string; message: string }

const immutableCache = new Map<string, FormDefinition>()
const requestCache = new Map<string, Promise<FormDefinition>>()
const moduleRequestCache = new Map<string, Promise<FormDefinition[]>>()

export function definitionCacheKey(key: string, version: number, checksum: string): string {
  return `${key}@${version}:${checksum}`
}

function remember(definition: FormDefinition): FormDefinition {
  const cached = Object.freeze(structuredClone(definition)) as FormDefinition
  immutableCache.set(`${definition.definition_key}@${definition.version}`, cached)
  immutableCache.set(definitionCacheKey(definition.definition_key, definition.version, definition.checksum), cached)
  return cached
}

export async function loadFormDefinition(definitionKey: string, version?: number): Promise<FormDefinition> {
  const identity = `${definitionKey}@${version ?? 'current'}`
  const cached = version == null ? undefined : immutableCache.get(`${definitionKey}@${version}`)
  if (cached) return cached
  const pending = requestCache.get(identity)
  if (pending) return pending
  const request = api.get<FormDefinition>(version == null
    ? `/api/form-definitions/${encodeURIComponent(definitionKey)}/current`
    : `/api/form-definitions/${encodeURIComponent(definitionKey)}/versions/${version}`)
    .then(remember)
    .finally(() => requestCache.delete(identity))
  requestCache.set(identity, request)
  return request
}

export async function loadModuleDefinitions(moduleCode: string): Promise<FormDefinition[]> {
  const pending = moduleRequestCache.get(moduleCode)
  if (pending) return pending
  const request = api.get<FormDefinition[]>(`/api/form-definitions?target_kind=property_record&module_code=${encodeURIComponent(moduleCode)}`)
    .then(response => {
      if (!Array.isArray(response)) return []
      const latest = new Map<string, FormDefinition>()
      for (const definition of response.filter(item => item?.status === 'published')) {
        const current = latest.get(definition.definition_key)
        if (!current || current.version < definition.version) latest.set(definition.definition_key, remember(definition))
      }
      return [...latest.values()].sort((left, right) => left.definition_key.localeCompare(right.definition_key))
    })
    .finally(() => moduleRequestCache.delete(moduleCode))
  moduleRequestCache.set(moduleCode, request)
  return request
}

export function clearFormDefinitionCache(): void {
  immutableCache.clear()
  requestCache.clear()
  moduleRequestCache.clear()
}

export function getAtPath(value: unknown, path: string): unknown {
  return path.split('.').filter(Boolean).reduce<unknown>((current, key) => (
    current && typeof current === 'object' ? (current as Record<string, unknown>)[key] : undefined
  ), value)
}

export function setAtPath<T>(value: T, path: string, nextValue: unknown): T {
  const clone = structuredClone(value)
  const keys = path.split('.').filter(Boolean)
  let current = clone as Record<string, any>
  keys.forEach((key, index) => {
    if (index === keys.length - 1) current[key] = nextValue
    else {
      if (!current[key] || typeof current[key] !== 'object') current[key] = {}
      current = current[key]
    }
  })
  return clone
}

function addIssue(issues: FormIssue[], field: string, message: string): void {
  issues.push({ field: field.replace(/^\./, ''), code: 'schema_validation_failed', message })
}

function validateSchema(value: unknown, schema: JsonSchema, path: string, issues: FormIssue[]): void {
  if (value == null) return
  if (schema.enum && !schema.enum.includes(value as never)) addIssue(issues, path, '值不在允许范围内')
  if (schema.type === 'object') {
    if (typeof value !== 'object' || Array.isArray(value)) return addIssue(issues, path, '必须是对象')
    const objectValue = value as Record<string, unknown>
    for (const required of schema.required || []) {
      if (objectValue[required] == null || objectValue[required] === '') addIssue(issues, `${path}.${required}`, '字段不能为空')
    }
    for (const [key, childSchema] of Object.entries(schema.properties || {})) {
      if (objectValue[key] != null) validateSchema(objectValue[key], childSchema, `${path}.${key}`, issues)
    }
    if (schema.additionalProperties === false) {
      for (const key of Object.keys(objectValue)) if (!schema.properties?.[key]) addIssue(issues, `${path}.${key}`, '字段未在定义中声明')
    }
    return
  }
  if (schema.type === 'array') {
    if (!Array.isArray(value)) return addIssue(issues, path, '必须是数组')
    value.forEach((item, index) => validateSchema(item, schema.items || {}, `${path}.${index}`, issues))
    return
  }
  if (schema.type === 'number' || schema.type === 'integer') {
    if (typeof value !== 'number' || !Number.isFinite(value)) return addIssue(issues, path, '必须是有效数值')
    if (schema.type === 'integer' && !Number.isInteger(value)) addIssue(issues, path, '必须是整数')
    if (schema.minimum != null && value < schema.minimum) addIssue(issues, path, `不得小于 ${schema.minimum}`)
    if (schema.maximum != null && value > schema.maximum) addIssue(issues, path, `不得大于 ${schema.maximum}`)
    return
  }
  if (schema.type === 'boolean' && typeof value !== 'boolean') return addIssue(issues, path, '必须是布尔值')
  if (schema.type === 'string') {
    if (typeof value !== 'string') return addIssue(issues, path, '必须是文本')
    if (schema.minLength != null && value.length < schema.minLength) addIssue(issues, path, `长度不得少于 ${schema.minLength}`)
    if (schema.maxLength != null && value.length > schema.maxLength) addIssue(issues, path, `长度不得超过 ${schema.maxLength}`)
  }
}

export function validateRecordClient(record: PropertyRecordDraft, definition?: FormDefinition): FormIssue[] {
  const issues: FormIssue[] = []
  if (!record.record_key.trim()) addIssue(issues, 'record_key', '记录键不能为空')
  if (!record.name_raw.trim()) addIssue(issues, 'name_raw', '名称不能为空')
  if (!record.value_raw.trim()) addIssue(issues, 'value_raw', '原始值不能为空')
  const calculation = record.payload.calculation_conditions
  const experimental = record.payload.experimental_conditions
  if (experimental && typeof experimental === 'object' && 'description' in experimental && typeof experimental.description !== 'string') {
    addIssue(issues, 'payload.experimental_conditions.description', '实验 Conditions 描述必须是文本')
  }
  if (record.record_type === 'predicted_tc' && (!calculation || experimental)) {
    issues.push({ field: experimental ? 'payload.experimental_conditions' : 'payload.calculation_conditions', code: 'invalid_condition_type', message: '预测 Tc 只能使用计算 Conditions' })
  }
  if (record.record_type === 'measured_tc' && (!experimental || calculation)) {
    issues.push({ field: calculation ? 'payload.calculation_conditions' : 'payload.experimental_conditions', code: 'invalid_condition_type', message: '测量 Tc 只能使用实验 Conditions' })
  }
  if (record.value_kind === 'range' && (record.value_min == null || record.value_max == null || record.value_min > record.value_max)) addIssue(issues, 'value_min', '范围值无效')
  if (definition && (definition.status === 'draft' || definition.module_code !== record.module_code || definition.record_type !== record.record_type)) {
    issues.push({ field: 'definition_key', code: 'definition_not_available', message: '定义版本不可用于该记录' })
  }
  if (definition) {
    validateSchema(record, definition.core_schema || {}, '', issues)
    validateSchema(record.payload, definition.json_schema || {}, 'payload', issues)
  }
  return issues
}
