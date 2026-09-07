import React from 'react'
import { Box, Button, Checkbox, FormControlLabel, MenuItem, Select, TextField } from '@mui/material'
import type { FormDefinition } from '../lib/formDefinitions'
import { validateRecordClient } from '../lib/formDefinitions'
import type { PropertyRecordDraft } from '../lib/propertyModules'

interface Props {
  record: PropertyRecordDraft
  definition?: FormDefinition
  readOnly?: boolean
  onChange: (record: PropertyRecordDraft) => void
  onDelete?: () => void
}

const SchemaDrivenRecordForm: React.FC<Props> = ({ record, definition, readOnly = false, onChange, onDelete }) => {
  const issues = validateRecordClient(record, definition)
  const issue = (field: string) => issues.find(item => item.field === field)?.message
  const update = (patch: Partial<PropertyRecordDraft>) => onChange({ ...record, ...patch })
  return <Box sx={{ display: 'grid', gap: 1, gridTemplateColumns: { xs: '1fr', sm: 'repeat(2, 1fr)' } }}>
    <TextField label="名称" value={record.name_raw} disabled={readOnly} error={Boolean(issue('name_raw'))} helperText={issue('name_raw')} onChange={event => update({ name_raw: event.target.value })} />
    <Select value={record.value_kind} disabled={readOnly} onChange={event => update({ value_kind: event.target.value as PropertyRecordDraft['value_kind'] })}>
      <MenuItem value="number">数值</MenuItem><MenuItem value="range">范围</MenuItem><MenuItem value="text">文本</MenuItem><MenuItem value="boolean">布尔</MenuItem>
    </Select>
    <TextField label="原始值" value={record.value_raw} disabled={readOnly} error={Boolean(issue('value_raw'))} helperText={issue('value_raw')} onChange={event => update({ value_raw: event.target.value })} />
    <TextField label="单位" value={record.unit_raw || ''} disabled={readOnly} onChange={event => update({ unit_raw: event.target.value })} />
    {record.value_kind === 'number' && <TextField label="数值" type="number" value={record.value_number ?? ''} disabled={readOnly} onChange={event => update({ value_number: event.target.value === '' ? null : Number(event.target.value) })} />}
    {record.value_kind === 'range' && <><TextField label="下界" type="number" value={record.value_min ?? ''} disabled={readOnly} onChange={event => update({ value_min: Number(event.target.value) })} /><TextField label="上界" type="number" value={record.value_max ?? ''} disabled={readOnly} onChange={event => update({ value_max: Number(event.target.value) })} /></>}
    {(record.record_type === 'predicted_tc' || record.record_type === 'measured_tc') && <FormControlLabel control={<Checkbox checked={Boolean(record.is_representative)} disabled={readOnly} onChange={event => update({ is_representative: event.target.checked })} />} label="代表结果" />}
    {!readOnly && onDelete && <Button color="error" onClick={onDelete}>删除记录</Button>}
  </Box>
}

export default SchemaDrivenRecordForm

