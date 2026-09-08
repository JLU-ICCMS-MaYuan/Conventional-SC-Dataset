import React, { useEffect, useMemo, useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, IconButton, MenuItem, Select, Tooltip, Typography,
} from '@mui/material'
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward'
import ArrowUpwardIcon from '@mui/icons-material/ArrowUpward'
import DeleteIcon from '@mui/icons-material/Delete'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import {
  loadFormDefinition, loadModuleDefinitions, type FormDefinition, type FormIssue,
} from '../lib/formDefinitions'
import {
  PROPERTY_MODULES, clonePropertyRecord, emptyPropertyModule, emptyPropertyRecord,
  type PropertyModuleCode, type PropertyModuleDraft, type PropertyRecordDraft,
} from '../lib/propertyModules'
import SchemaDrivenRecordForm from './SchemaDrivenRecordForm'

export interface ModuleDeletion {
  deletedModuleKey?: string
  deletedRecordKey?: string
}

interface Props {
  modules: PropertyModuleDraft[]
  issues?: FormIssue[]
  basePath?: string
  readOnly?: boolean
  onChange: (modules: PropertyModuleDraft[], deletion?: ModuleDeletion) => void
}

const fallbackDefinitionRefs = (moduleCode: PropertyModuleCode): Array<Pick<FormDefinition, 'definition_key' | 'version' | 'module_code' | 'record_type' | 'method_code' | 'property_code'>> => {
  const custom = {
    definition_key: `record.${moduleCode}.custom`, version: 1, module_code: moduleCode,
    record_type: 'property', method_code: null, property_code: 'custom',
  }
  return moduleCode === 'superconductive_properties'
    ? [
        {
          definition_key: 'record.superconductive_properties.predicted_tc.unknown', version: 1,
          module_code: moduleCode, record_type: 'predicted_tc', method_code: 'unknown', property_code: 'tc',
        },
        {
          definition_key: 'record.superconductive_properties.predicted_tc.mcmillan', version: 1,
          module_code: moduleCode, record_type: 'predicted_tc', method_code: 'mcmillan', property_code: 'tc',
        },
        {
          definition_key: 'record.superconductive_properties.predicted_tc.allen_dynes', version: 1,
          module_code: moduleCode, record_type: 'predicted_tc', method_code: 'allen_dynes', property_code: 'tc',
        },
        {
          definition_key: 'record.superconductive_properties.measured_tc.resistivity', version: 1,
          module_code: moduleCode, record_type: 'measured_tc', method_code: 'resistivity', property_code: 'tc',
        },
        custom,
      ]
    : [custom]
}

const definitionIdentity = (definition: Pick<FormDefinition, 'definition_key' | 'version'>) => (
  `${definition.definition_key}@${definition.version}`
)

const definitionLabel = (definition: Pick<FormDefinition, 'definition_key' | 'record_type' | 'method_code' | 'property_code'>) => {
  if (definition.record_type === 'predicted_tc') return `预测 Tc · ${definition.method_code || 'unknown'}`
  if (definition.record_type === 'measured_tc') return `测量 Tc · ${definition.method_code || 'unknown'}`
  return definition.property_code === 'custom' ? '自定义性质' : definition.property_code || definition.definition_key
}

const recordForDefinition = (
  current: PropertyRecordDraft,
  definition: Pick<FormDefinition, 'definition_key' | 'version' | 'record_type' | 'method_code' | 'property_code'>,
): PropertyRecordDraft => {
  const recordType = (definition.record_type || 'property') as PropertyRecordDraft['record_type']
  const payload = structuredClone(current.payload || {})
  if (recordType === 'predicted_tc') {
    delete payload.experimental_conditions
    payload.calculation_conditions ||= {}
    payload.parameters ||= {}
  } else if (recordType === 'measured_tc') {
    delete payload.calculation_conditions
    delete payload.parameters
    payload.experimental_conditions ||= {}
  } else {
    delete payload.calculation_conditions
    delete payload.experimental_conditions
    delete payload.parameters
  }
  return {
    ...current,
    record_type: recordType,
    property_code: definition.property_code || (recordType === 'property' ? 'custom' : 'tc'),
    definition_key: definition.definition_key,
    definition_version: definition.version,
    method_code: definition.method_code || null,
    name_raw: current.name_raw || (recordType === 'property' ? '' : 'critical temperature'),
    unit_raw: current.unit_raw || (recordType === 'property' ? null : 'K'),
    canonical_unit: recordType === 'property' ? current.canonical_unit : 'K',
    payload,
  }
}

const normalizeOrder = (modules: PropertyModuleDraft[]) => modules.map((module, index) => ({ ...module, display_order: index }))

const PropertyModuleEditor: React.FC<Props> = ({
  modules,
  issues = [],
  basePath = '',
  readOnly = false,
  onChange,
}) => {
  const [definitions, setDefinitions] = useState<Record<string, FormDefinition[]>>({})
  const [boundDefinitions, setBoundDefinitions] = useState<Record<string, FormDefinition>>({})
  const [definitionErrors, setDefinitionErrors] = useState<Record<string, string>>({})
  const moduleCodes = useMemo(() => [...new Set(modules.map(module => module.module_code))], [modules])

  useEffect(() => {
    let active = true
    moduleCodes.forEach(moduleCode => {
      loadModuleDefinitions(moduleCode)
        .then(items => { if (active) setDefinitions(current => ({ ...current, [moduleCode]: items })) })
        .catch(() => { if (active) setDefinitions(current => ({ ...current, [moduleCode]: [] })) })
    })
    return () => { active = false }
  }, [moduleCodes.join('|')])

  useEffect(() => {
    let active = true
    modules.flatMap(module => module.records).forEach(record => {
      const identity = `${record.definition_key}@${record.definition_version}`
      const listed = definitions[record.module_code]?.find(item => definitionIdentity(item) === identity)
      if (listed) {
        setBoundDefinitions(current => ({ ...current, [record.record_key]: listed }))
        return
      }
      loadFormDefinition(record.definition_key, record.definition_version)
        .then(item => {
          if (!active) return
          setBoundDefinitions(current => ({ ...current, [record.record_key]: item }))
          setDefinitionErrors(current => ({ ...current, [record.record_key]: '' }))
        })
        .catch(() => {
          if (active) setDefinitionErrors(current => ({ ...current, [record.record_key]: '定义版本不可用，当前记录不能安全提交' }))
        })
    })
    return () => { active = false }
  }, [modules, definitions])

  const addModule = (code: PropertyModuleCode) => {
    if (modules.some(item => item.module_code === code)) return
    onChange([...modules, emptyPropertyModule(code, modules.length)])
  }

  const moveModule = (index: number, offset: number) => {
    const target = index + offset
    if (target < 0 || target >= modules.length) return
    const next = [...modules]
    ;[next[index], next[target]] = [next[target], next[index]]
    onChange(normalizeOrder(next))
  }

  const choicesFor = (moduleCode: PropertyModuleCode) => (
    definitions[moduleCode]?.length ? definitions[moduleCode] : fallbackDefinitionRefs(moduleCode)
  )

  const addRecord = (moduleIndex: number, identity: string) => {
    const module = modules[moduleIndex]
    const definition = choicesFor(module.module_code).find(item => definitionIdentity(item) === identity)
    if (!definition) return
    const record = recordForDefinition(emptyPropertyRecord(module.module_code), definition)
    onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: [...item.records, record] } : item))
  }

  const updateRecord = (moduleIndex: number, recordIndex: number, record: PropertyRecordDraft) => {
    onChange(modules.map((item, index) => index === moduleIndex
      ? { ...item, records: item.records.map((current, currentIndex) => currentIndex === recordIndex ? record : current) }
      : item))
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {!readOnly && (
        <Select size="small" displayEmpty value="" inputProps={{ 'aria-label': '添加物性模块' }}
          onChange={event => addModule(event.target.value as PropertyModuleCode)}
          renderValue={() => '添加物性模块'}>
          <MenuItem value="" disabled>添加物性模块</MenuItem>
          {PROPERTY_MODULES.filter(item => !modules.some(module => module.module_code === item.code))
            .map(item => <MenuItem key={item.code} value={item.code}>{item.label}</MenuItem>)}
        </Select>
      )}
      {modules.length === 0 && readOnly && <Alert severity="info">未报告物性模块</Alert>}
      {modules.map((module, moduleIndex) => {
        const moduleBasePath = basePath ? `${basePath}.${moduleIndex}` : String(moduleIndex)
        const choices = choicesFor(module.module_code)
        return (
          <Accordion key={module.module_key} defaultExpanded data-testid={`property-module-${module.module_code}`}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />} sx={{ flex: 1 }}>
              <Typography>{PROPERTY_MODULES.find(item => item.code === module.module_code)?.label || module.module_code}</Typography>
            </AccordionSummary>
              {!readOnly && (
                <Box sx={{ pr: 1 }}>
                  <Tooltip title="上移模块"><span><IconButton size="small" aria-label="上移模块" disabled={moduleIndex === 0} onClick={() => moveModule(moduleIndex, -1)}><ArrowUpwardIcon /></IconButton></span></Tooltip>
                  <Tooltip title="下移模块"><span><IconButton size="small" aria-label="下移模块" disabled={moduleIndex === modules.length - 1} onClick={() => moveModule(moduleIndex, 1)}><ArrowDownwardIcon /></IconButton></span></Tooltip>
                  <Tooltip title={module.records.length ? '请先删除模块内记录' : '删除模块'}>
                    <span><IconButton size="small" aria-label="删除模块" disabled={module.records.length > 0}
                      onClick={() => onChange(normalizeOrder(modules.filter((_, index) => index !== moduleIndex)), { deletedModuleKey: module.module_key })}><DeleteIcon /></IconButton></span>
                  </Tooltip>
                </Box>
              )}
            </Box>
            <AccordionDetails>
              {module.records.map((record, recordIndex) => {
                const recordBasePath = `${moduleBasePath}.records.${recordIndex}`
                const recordIssues = issues.flatMap(item => item.field.startsWith(recordBasePath)
                  ? [{ ...item, field: item.field.slice(recordBasePath.length + 1) }]
                  : [])
                const allChoices = choices.some(item => definitionIdentity(item) === `${record.definition_key}@${record.definition_version}`)
                  ? choices
                  : [boundDefinitions[record.record_key], ...choices].filter(Boolean)
                const recordLabel = definitionLabel(record)
                const summary = [recordLabel, record.name_raw, record.value_raw].filter(Boolean).join(' · ')
                const recordError = definitionErrors[record.record_key] || recordIssues[0]?.message
                return (
                  <Accordion key={record.record_key} defaultExpanded sx={{ mb: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />} aria-label={`记录 ${recordIndex + 1} · ${summary}`}>
                      <Box sx={{ minWidth: 0 }}>
                        <Typography sx={{ overflowWrap: 'anywhere' }}>{summary}</Typography>
                        {recordError && <Typography color="error" variant="caption">{recordError}</Typography>}
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails>
                      {!readOnly && (
                        <Select fullWidth size="small" inputProps={{ 'aria-label': '记录定义' }} value={`${record.definition_key}@${record.definition_version}`}
                          onChange={event => {
                            const definition = allChoices.find(item => definitionIdentity(item) === event.target.value)
                            if (definition) updateRecord(moduleIndex, recordIndex, recordForDefinition(record, definition))
                          }} sx={{ mb: 1 }}>
                          {allChoices.map(definition => <MenuItem key={definitionIdentity(definition)} value={definitionIdentity(definition)}>{definitionLabel(definition)}</MenuItem>)}
                        </Select>
                      )}
                      <SchemaDrivenRecordForm
                        record={record}
                        definition={boundDefinitions[record.record_key] || definitions[record.module_code]?.find(item => definitionIdentity(item) === `${record.definition_key}@${record.definition_version}`)}
                        definitionError={definitionErrors[record.record_key]}
                        issues={recordIssues}
                        basePath={recordBasePath}
                        readOnly={readOnly}
                        onChange={next => updateRecord(moduleIndex, recordIndex, next)}
                        onClone={readOnly ? undefined : () => onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: [...item.records, clonePropertyRecord(record)] } : item))}
                        onDelete={readOnly ? undefined : () => onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: item.records.filter((_, currentIndex) => currentIndex !== recordIndex) } : item), { deletedRecordKey: record.record_key })}
                      />
                    </AccordionDetails>
                  </Accordion>
                )
              })}
              {!readOnly && (
                <Select size="small" displayEmpty value="" inputProps={{ 'aria-label': '添加记录' }} onChange={event => addRecord(moduleIndex, event.target.value)}
                  renderValue={() => '添加记录'}>
                  <MenuItem value="" disabled>添加记录</MenuItem>
                  {choices.map(definition => <MenuItem key={definitionIdentity(definition)} value={definitionIdentity(definition)}>{definitionLabel(definition)}</MenuItem>)}
                </Select>
              )}
            </AccordionDetails>
          </Accordion>
        )
      })}
    </Box>
  )
}

export default PropertyModuleEditor
