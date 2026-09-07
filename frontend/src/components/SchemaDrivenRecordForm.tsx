import React from 'react'
import {
  Alert, Box, Button, Checkbox, FormControl, FormControlLabel, InputLabel, MenuItem, Select, TextField, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import type { FormDefinition, FormIssue, JsonSchema } from '../lib/formDefinitions'
import { getAtPath, setAtPath, validateRecordClient } from '../lib/formDefinitions'
import { newStableKey, type PropertyRecordDraft, type PropertyValueKind } from '../lib/propertyModules'

interface Props {
  record: PropertyRecordDraft
  definition?: FormDefinition
  definitionError?: string
  issues?: FormIssue[]
  basePath?: string
  readOnly?: boolean
  onChange: (record: PropertyRecordDraft) => void
  onDelete?: () => void
  onClone?: () => void
}

const VALUE_KIND_LABELS: Record<PropertyValueKind, string> = {
  number: '数值', range: '范围', text: '文本', boolean: '布尔',
}

const FALLBACK_GROUP_SCHEMAS: Record<string, JsonSchema> = {
  calculation_conditions: {
    type: 'object',
    title: '计算 Conditions',
    properties: {
      calculation_code: { type: 'string', title: '计算软件' },
      electronic_method: { type: 'string', title: '电子结构方法' },
      exchange_correlation_functional: { type: 'string', title: '交换关联泛函' },
      k_grid: { type: 'string', title: 'k 网格' },
      q_grid: { type: 'string', title: 'q 网格' },
      k_broadening: { type: 'number', title: 'k 展宽' },
      q_broadening: { type: 'number', title: 'q 展宽' },
      extensions: { type: 'array', title: '补充计算条件', items: { type: 'object' } },
    },
  },
  experimental_conditions: {
    type: 'object',
    title: '实验 Conditions',
    properties: {
      sample: { type: 'string', title: '样品' },
      preparation_method: { type: 'string', title: '制备方式' },
      measurement_method: { type: 'string', title: '测量方法' },
      apparatus: { type: 'string', title: '测量装置' },
      external_field_t: { type: 'number', title: '外场 (T)' },
      pressure_uncertainty_gpa: { type: 'number', title: '压力不确定度 (GPa)' },
      extensions: { type: 'array', title: '补充实验条件', items: { type: 'object' } },
    },
  },
  parameters: {
    type: 'object',
    title: '参数',
    properties: {
      lambda_ep: { type: 'number', title: '电声耦合强度 λ', minimum: 0 },
      omega_log: { type: 'number', title: 'ωlog (K)', minimum: 0 },
      mu_star: { type: 'number', title: 'μ*', minimum: 0 },
      extensions: { type: 'array', title: '补充参数', items: { type: 'object' } },
    },
  },
}

const titleFor = (definition: FormDefinition | undefined, path: string, schema: JsonSchema, fallback: string): string => {
  const fields = definition?.ui_schema?.fields
  const pointer = `/${path.replace(/\./g, '/')}`
  const configured = Array.isArray(fields)
    ? fields.find((item: any) => item?.pointer === pointer || item?.path === path)
    : fields?.[path] || fields?.[pointer]
  return configured?.label || configured?.title || schema.title || fallback
}

const effectivePayloadSchema = (definition: FormDefinition | undefined, recordType: PropertyRecordDraft['record_type']): JsonSchema => {
  const schema = structuredClone(definition?.json_schema || { type: 'object', properties: {} }) as JsonSchema
  schema.type ||= 'object'
  const properties: Record<string, JsonSchema> = schema.properties || {}
  schema.properties = properties
  if (recordType === 'predicted_tc') {
    properties.calculation_conditions ||= FALLBACK_GROUP_SCHEMAS.calculation_conditions
    properties.parameters ||= FALLBACK_GROUP_SCHEMAS.parameters
  } else if (recordType === 'measured_tc') {
    properties.experimental_conditions ||= FALLBACK_GROUP_SCHEMAS.experimental_conditions
  }
  for (const [group, fallback] of Object.entries(FALLBACK_GROUP_SCHEMAS)) {
    const declared = properties[group]
    if (!declared) continue
    properties[group] = {
      ...fallback,
      ...declared,
      properties: { ...fallback.properties, ...(declared.properties || {}) },
    }
  }
  return schema
}

const parseGridOrText = (raw: string, schema: JsonSchema): unknown => {
  if (schema.type !== 'array') return raw
  return raw.split(/[x,\s]+/).map(item => Number(item)).filter(Number.isFinite)
}

const extensionValuePatch = (item: Record<string, any>, kind: PropertyValueKind, raw: string): Record<string, any> => {
  const next: Record<string, any> = { ...item, value_kind: kind, value_raw: raw }
  delete next.value_number
  delete next.value_min
  delete next.value_max
  delete next.value_text
  delete next.value_boolean
  if (kind === 'number') next.value_number = raw === '' ? null : Number(raw)
  if (kind === 'text') next.value_text = raw
  if (kind === 'boolean') next.value_boolean = raw === 'true'
  return next
}

const SchemaDrivenRecordForm: React.FC<Props> = ({
  record,
  definition,
  definitionError = '',
  issues: externalIssues = [],
  basePath = '',
  readOnly = false,
  onChange,
  onDelete,
  onClone,
}) => {
  const issues = [...validateRecordClient(record, definition), ...externalIssues]
  const issue = (field: string) => issues.find(item => item.field === field || item.field.endsWith(`.${field}`))?.message
  const fieldPath = (field: string) => basePath ? `${basePath}.${field}` : field
  const update = (patch: Partial<PropertyRecordDraft>) => onChange({ ...record, ...patch })
  const updatePath = (path: string, value: unknown) => onChange(setAtPath(record, path, value))

  const renderExtensions = (path: string, schema: JsonSchema) => {
    const items = getAtPath(record, path)
    const values = Array.isArray(items) ? items as Array<Record<string, any>> : []
    return (
      <Box key={path} data-issue-field={fieldPath(path)} sx={{ gridColumn: '1 / -1', borderLeft: '3px solid', borderColor: 'divider', pl: 1.5 }}>
        <Typography variant="subtitle2">{titleFor(definition, path, schema, '扩展字段')}</Typography>
        {values.map((item, index) => {
          const itemPath = `${path}.${index}`
          const kind = (item.value_kind || 'number') as PropertyValueKind
          return (
            <Box key={item.field_key || index} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '2fr 1fr 2fr 1fr auto' }, gap: 1, mt: 1 }}>
              <TextField size="small" label="字段名称" value={item.name_raw || ''} disabled={readOnly}
                error={Boolean(issue(`${itemPath}.name_raw`))} helperText={issue(`${itemPath}.name_raw`)}
                onChange={event => updatePath(`${itemPath}.name_raw`, event.target.value)} />
              <FormControl size="small">
                <InputLabel>值类型</InputLabel>
                <Select label="值类型" value={kind} disabled={readOnly}
                  onChange={event => updatePath(itemPath, extensionValuePatch(item, event.target.value as PropertyValueKind, item.value_raw || ''))}>
                  {Object.entries(VALUE_KIND_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
                </Select>
              </FormControl>
              {kind === 'boolean' ? (
                <FormControl size="small">
                  <InputLabel>值</InputLabel>
                  <Select label="值" value={String(Boolean(item.value_boolean))} disabled={readOnly}
                    onChange={event => updatePath(itemPath, extensionValuePatch(item, kind, event.target.value))}>
                    <MenuItem value="true">是</MenuItem><MenuItem value="false">否</MenuItem>
                  </Select>
                </FormControl>
              ) : (
                <TextField size="small" label={kind === 'range' ? '值（下界..上界）' : '值'} value={item.value_raw || ''} disabled={readOnly}
                  error={Boolean(issue(`${itemPath}.value_raw`))} helperText={issue(`${itemPath}.value_raw`)}
                  onChange={event => {
                    const next = extensionValuePatch(item, kind, event.target.value)
                    if (kind === 'range') {
                      const [min, max] = event.target.value.split('..').map(Number)
                      next.value_min = Number.isFinite(min) ? min : null
                      next.value_max = Number.isFinite(max) ? max : null
                    }
                    updatePath(itemPath, next)
                  }} />
              )}
              <TextField size="small" label="单位" value={item.unit_raw || ''} disabled={readOnly}
                onChange={event => updatePath(`${itemPath}.unit_raw`, event.target.value)} />
              {!readOnly && <Button color="error" aria-label="删除扩展字段" onClick={() => updatePath(path, values.filter((_, itemIndex) => itemIndex !== index))}><DeleteIcon /></Button>}
            </Box>
          )
        })}
        {!readOnly && <Button size="small" startIcon={<AddIcon />} onClick={() => updatePath(path, [...values, {
          field_key: newStableKey('field'), name_raw: '', value_kind: 'number', value_raw: '', value_number: null, unit_raw: '', evidences: [],
        }])}>新增字段</Button>}
      </Box>
    )
  }

  const renderSchema = (schema: JsonSchema, path: string, fallbackLabel: string): React.ReactNode => {
    const label = titleFor(definition, path, schema, fallbackLabel)
    if (schema.type === 'array' && path.endsWith('.extensions')) return renderExtensions(path, schema)
    if (schema.type === 'object' || schema.properties) {
      return (
        <Box key={path} data-issue-field={fieldPath(path)} sx={{ gridColumn: '1 / -1', display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, gap: 1, borderLeft: '3px solid', borderColor: 'divider', pl: 1.5 }}>
          <Typography variant="subtitle2" sx={{ gridColumn: '1 / -1' }}>{label}</Typography>
          {Object.entries(schema.properties || {}).map(([key, child]) => renderSchema(child, `${path}.${key}`, key))}
          {issue(path) && <Typography color="error" variant="caption">{issue(path)}</Typography>}
        </Box>
      )
    }
    const value = getAtPath(record, path)
    if (schema.enum) {
      return (
        <FormControl key={path} size="small" error={Boolean(issue(path))} data-issue-field={fieldPath(path)}>
          <InputLabel>{label}</InputLabel>
          <Select label={label} value={value ?? ''} disabled={readOnly} onChange={event => updatePath(path, event.target.value)}>
            {schema.enum.map(option => <MenuItem key={String(option)} value={String(option)}>{String(option)}</MenuItem>)}
          </Select>
        </FormControl>
      )
    }
    if (schema.type === 'boolean') {
      return <FormControlLabel key={path} data-issue-field={fieldPath(path)} control={<Checkbox checked={Boolean(value)} disabled={readOnly} onChange={event => updatePath(path, event.target.checked)} />} label={label} />
    }
    const numeric = schema.type === 'number' || schema.type === 'integer'
    return (
      <TextField key={path} size="small" label={label} type={numeric ? 'number' : 'text'} value={Array.isArray(value) ? value.join(' x ') : value ?? ''} disabled={readOnly}
        data-issue-field={fieldPath(path)} error={Boolean(issue(path))} helperText={issue(path) || schema.description}
        slotProps={numeric ? { htmlInput: { min: schema.minimum, max: schema.maximum, step: schema.type === 'integer' ? 1 : 'any' } } : undefined}
        onChange={event => updatePath(path, numeric ? (event.target.value === '' ? null : Number(event.target.value)) : parseGridOrText(event.target.value, schema))} />
    )
  }

  return (
    <Box data-testid={`property-record-${record.record_key}`} sx={{ display: 'grid', gap: 1, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' }, p: 1.5, border: '1px solid', borderColor: 'divider', borderRadius: 1, mb: 1 }}>
      {definitionError && <Alert severity="error" sx={{ gridColumn: '1 / -1' }}>{definitionError}</Alert>}
      <TextField label="名称" value={record.name_raw} disabled={readOnly} data-issue-field={fieldPath('name_raw')} error={Boolean(issue('name_raw'))} helperText={issue('name_raw')} onChange={event => update({ name_raw: event.target.value })} />
      <FormControl>
        <InputLabel>值类型</InputLabel>
        <Select label="值类型" value={record.value_kind} disabled={readOnly} onChange={event => update({ value_kind: event.target.value as PropertyValueKind })}>
          {Object.entries(VALUE_KIND_LABELS).map(([value, label]) => <MenuItem key={value} value={value}>{label}</MenuItem>)}
        </Select>
      </FormControl>
      <TextField label="原始值" value={record.value_raw} disabled={readOnly} data-issue-field={fieldPath('value_raw')} error={Boolean(issue('value_raw'))} helperText={issue('value_raw')} onChange={event => update({ value_raw: event.target.value })} />
      <TextField label="单位" value={record.unit_raw || ''} disabled={readOnly} onChange={event => update({ unit_raw: event.target.value || null })} />
      {record.value_kind === 'number' && <TextField label="数值" type="number" value={record.value_number ?? ''} disabled={readOnly} onChange={event => update({ value_number: event.target.value === '' ? null : Number(event.target.value) })} />}
      {record.value_kind === 'range' && <><TextField label="下界" type="number" value={record.value_min ?? ''} disabled={readOnly} data-issue-field={fieldPath('value_min')} error={Boolean(issue('value_min'))} helperText={issue('value_min')} onChange={event => update({ value_min: event.target.value === '' ? null : Number(event.target.value) })} /><TextField label="上界" type="number" value={record.value_max ?? ''} disabled={readOnly} onChange={event => update({ value_max: event.target.value === '' ? null : Number(event.target.value) })} /></>}
      {record.value_kind === 'text' && <TextField label="文本值" value={record.value_text || ''} disabled={readOnly} onChange={event => update({ value_text: event.target.value })} />}
      {record.value_kind === 'boolean' && <FormControlLabel control={<Checkbox checked={Boolean(record.value_boolean)} disabled={readOnly} onChange={event => update({ value_boolean: event.target.checked })} />} label="布尔值" />}
      {(record.record_type === 'predicted_tc' || record.record_type === 'measured_tc') && <FormControlLabel control={<Checkbox checked={Boolean(record.is_representative)} disabled={readOnly} onChange={event => update({ is_representative: event.target.checked })} />} label="代表结果" />}
      {Object.entries(effectivePayloadSchema(definition, record.record_type).properties || {}).map(([key, schema]) => renderSchema(schema, `payload.${key}`, key))}
      {!readOnly && <Box sx={{ gridColumn: '1 / -1', display: 'flex', justifyContent: 'flex-end', gap: 1 }}>
        {onClone && <Button onClick={onClone}>复制记录</Button>}
        {onDelete && <Button color="error" startIcon={<DeleteIcon />} onClick={onDelete}>删除记录</Button>}
      </Box>}
    </Box>
  )
}

export default SchemaDrivenRecordForm
