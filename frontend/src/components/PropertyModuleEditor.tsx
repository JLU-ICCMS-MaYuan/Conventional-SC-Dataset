import React from 'react'
import { Accordion, AccordionDetails, AccordionSummary, Button, MenuItem, Select, Typography } from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { PROPERTY_MODULES, emptyPropertyRecord, type PropertyModuleDraft } from '../lib/propertyModules'
import SchemaDrivenRecordForm from './SchemaDrivenRecordForm'

interface Props { modules: PropertyModuleDraft[]; readOnly?: boolean; onChange: (modules: PropertyModuleDraft[]) => void }

const PropertyModuleEditor: React.FC<Props> = ({ modules, readOnly = false, onChange }) => {
  const addModule = (code: PropertyModuleDraft['module_code']) => {
    if (modules.some(item => item.module_code === code)) return
    onChange([...modules, { module_key: `module-${code}`, module_code: code, display_order: modules.length, records: [] }])
  }
  return <>
    {!readOnly && <Select displayEmpty value="" onChange={event => addModule(event.target.value as PropertyModuleDraft['module_code'])} renderValue={() => '添加物性模块'}>
      <MenuItem value="" disabled>添加物性模块</MenuItem>{PROPERTY_MODULES.filter(item => !modules.some(module => module.module_code === item.code)).map(item => <MenuItem key={item.code} value={item.code}>{item.label}</MenuItem>)}
    </Select>}
    {modules.map((module, moduleIndex) => <Accordion key={module.module_key} defaultExpanded>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}><Typography>{PROPERTY_MODULES.find(item => item.code === module.module_code)?.label || module.module_code}</Typography></AccordionSummary>
      <AccordionDetails>
        {module.records.map((record, recordIndex) => <SchemaDrivenRecordForm key={record.record_key} record={record} readOnly={readOnly} onChange={next => onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: item.records.map((current, i) => i === recordIndex ? next : current) } : item))} onDelete={readOnly ? undefined : () => onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: item.records.filter((_, i) => i !== recordIndex) } : item))} />)}
        {!readOnly && <Button onClick={() => onChange(modules.map((item, index) => index === moduleIndex ? { ...item, records: [...item.records, emptyPropertyRecord(module.module_code, item.records.length)] } : item))}>添加记录</Button>}
      </AccordionDetails>
    </Accordion>)}
  </>
}

export default PropertyModuleEditor

