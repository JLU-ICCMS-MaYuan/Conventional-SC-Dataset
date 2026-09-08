import '@testing-library/jest-dom/vitest'
import React, { useState } from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import PropertyModuleEditor from '../../frontend/src/components/PropertyModuleEditor'
import SchemaDrivenRecordForm from '../../frontend/src/components/SchemaDrivenRecordForm'
import { api } from '../../frontend/src/lib/api'
import { clearFormDefinitionCache, validateRecordClient, type FormDefinition } from '../../frontend/src/lib/formDefinitions'
import { emptyPropertyModule, type PropertyModuleDraft, type PropertyRecordDraft } from '../../frontend/src/lib/propertyModules'
import matrix from '../fixtures/issue90/form-definition-matrix.json'

vi.mock('../../frontend/src/lib/api', () => ({ api: { get: vi.fn() } }))
const definitions = matrix.definitions as FormDefinition[]
const measuredDefinition = definitions.find(item => item.record_type === 'measured_tc')!
const measured = (key: string, value: number): PropertyRecordDraft => ({
  record_key: key, module_code: 'superconductive_properties', record_type: 'measured_tc',
  property_code: 'tc', definition_key: measuredDefinition.definition_key, definition_version: 1,
  method_code: 'resistivity', name_raw: 'Tc', value_kind: 'number', value_raw: `${value} K`,
  value_number: value, unit_raw: 'K', canonical_unit: 'K',
  payload: { experimental_conditions: { description: `Conditions for ${value} K` } },
})
const initialModules = (): PropertyModuleDraft[] => [{
  ...emptyPropertyModule('superconductive_properties'), module_key: 'superconductive',
  records: [measured('first', 4.2), measured('second', 3.8)],
}]

beforeEach(() => {
  vi.mocked(api.get).mockImplementation(async path => {
    if (path.startsWith('/api/form-definitions?')) return definitions as never
    return definitions.find(item => path.includes(encodeURIComponent(item.definition_key))) as never
  })
})
afterEach(() => { cleanup(); vi.clearAllMocks(); clearFormDefinitionCache() })

describe('Issue #94 记录表单', () => {
  it('实验条件只有一个多行框，旧字段和 Evidence 在编辑后保留', () => {
    const legacy = { sample: 'Hg', preparation_method: 'annealed', measurement_method: 'four probe', apparatus: 'DAC', external_field_t: 0, pressure_uncertainty_gpa: 0.2, extensions: [{ name_raw: 'contact', value_raw: 'Pt', evidences: [{ paper_evidence_id: 9 }] }] }
    const record = { ...measured('old', 4.2), payload: { experimental_conditions: legacy } }
    const onChange = vi.fn()
    const { rerender } = render(<SchemaDrivenRecordForm record={record} definition={measuredDefinition} onChange={onChange} />)
    const input = screen.getByLabelText('实验 Conditions')
    expect(input.tagName).toBe('TEXTAREA')
    expect((input as HTMLTextAreaElement).value).toContain('外场 (T)：0')
    expect((input as HTMLTextAreaElement).value).toContain('four probe')
    expect((input as HTMLTextAreaElement).value).toContain('Pt')
    for (const label of ['样品', '制备方式', '测量方法', '测量装置', '外场 (T)', '压力不确定度 (GPa)']) {
      expect(screen.queryByLabelText(label)).not.toBeInTheDocument()
    }
    expect(screen.queryByText('补充实验条件')).not.toBeInTheDocument()
    const text = 'Four-probe resistivity in a DAC.\nNo applied field.'
    fireEvent.change(input, { target: { value: text } })
    const next = onChange.mock.calls.at(-1)![0]
    expect(next.payload.experimental_conditions).toEqual({ ...legacy, description: text })
    expect(record.payload.experimental_conditions).toEqual(legacy)
    expect(validateRecordClient(next, measuredDefinition)).toEqual([])
    rerender(<SchemaDrivenRecordForm record={next} definition={measuredDefinition} onChange={onChange} />)
    expect(screen.getByLabelText('实验 Conditions')).toHaveValue(text)
    fireEvent.change(screen.getByLabelText('实验 Conditions'), { target: { value: '' } })
    rerender(<SchemaDrivenRecordForm record={onChange.mock.calls.at(-1)![0]} definition={measuredDefinition} onChange={onChange} readOnly />)
    expect(screen.getByLabelText('实验 Conditions')).toHaveValue('')
    expect(screen.getByLabelText('实验 Conditions')).toBeDisabled()
  })

  it('实验条件描述的非法类型定位报错', () => {
    const record = { ...measured('bad', 4.2), payload: { experimental_conditions: { description: 7 } } }
    expect(validateRecordClient(record, measuredDefinition)).toContainEqual(expect.objectContaining({ field: 'payload.experimental_conditions.description' }))
  })

  it('标题和添加选项不含版本号，提交保留定义版本', async () => {
    const onChange = vi.fn()
    render(<PropertyModuleEditor modules={initialModules()} onChange={onChange} />)
    await waitFor(() => expect(api.get).toHaveBeenCalled())
    expect(screen.queryByText(/· v\d+/)).not.toBeInTheDocument()
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '添加记录' }))
    fireEvent.click(await screen.findByRole('option', { name: '测量 Tc · resistivity', exact: true }))
    const next = onChange.mock.calls.at(-1)![0]
    expect(next[0].records[2]).toMatchObject({ definition_key: measuredDefinition.definition_key, definition_version: 1 })
    expect(next[0].records).toHaveLength(3)
  })

  it('多条记录独立折叠，编辑值、复制及删除不影响其他记录状态', async () => {
    const changed = vi.fn()
    const Harness = () => {
      const [modules, setModules] = useState(initialModules)
      return <PropertyModuleEditor modules={modules} onChange={next => { changed(next); setModules(next) }} />
    }
    render(<Harness />)
    const user = userEvent.setup()
    const first = await screen.findByRole('button', { name: /记录 1.*测量 Tc.*4.2 K/ })
    const second = screen.getByRole('button', { name: /记录 2.*测量 Tc.*3.8 K/ })
    fireEvent.change(within(screen.getByTestId('property-record-first')).getByLabelText('实验 Conditions'), { target: { value: 'Edited first\nconditions' } })
    changed.mockClear()
    first.focus()
    await user.keyboard('{Enter}')
    expect(first).toHaveAttribute('aria-expanded', 'false')
    expect(second).toHaveAttribute('aria-expanded', 'true')
    expect(changed).not.toHaveBeenCalled()
    await user.click(within(screen.getByTestId('property-record-second')).getByRole('button', { name: '复制记录' }))
    expect(screen.getByRole('button', { name: /记录 3.*测量 Tc.*3.8 K/ })).toHaveAttribute('aria-expanded', 'true')
    expect(first).toHaveAttribute('aria-expanded', 'false')
    await user.click(within(screen.getByTestId('property-record-second')).getByRole('button', { name: '删除记录' }))
    expect(first).toHaveAttribute('aria-expanded', 'false')
    await user.click(first)
    expect(within(screen.getByTestId('property-record-first')).getByLabelText('实验 Conditions')).toHaveValue('Edited first\nconditions')
    expect(changed.mock.calls.at(-1)![0][0].records).toHaveLength(2)
  })

  it('只读记录可收起但不能编辑，服务端错误在收起时可见', async () => {
    const onChange = vi.fn()
    render(<PropertyModuleEditor modules={initialModules()} onChange={onChange} readOnly issues={[{ field: '0.records.0.payload.experimental_conditions.description', code: 'invalid', message: '核对实验条件' }]} />)
    const first = await screen.findByRole('button', { name: /记录 1.*测量 Tc/ })
    fireEvent.click(first)
    expect(first).toHaveAttribute('aria-expanded', 'false')
    expect(first).toHaveTextContent('核对实验条件')
    expect(screen.queryByRole('button', { name: '删除记录' })).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: '添加记录' })).not.toBeInTheDocument()
    expect(screen.getAllByLabelText('实验 Conditions').every(input => (input as HTMLTextAreaElement).disabled)).toBe(true)
    expect(onChange).not.toHaveBeenCalled()
  })

  it('同状态下的预测 Tc 和自定义性质也可独立折叠，计算参数不变', async () => {
    const predicted: PropertyRecordDraft = {
      ...measured('predicted', 5), record_type: 'predicted_tc', method_code: 'allen_dynes',
      definition_key: definitions[0].definition_key,
      payload: structuredClone(matrix.valid_records.predicted_tc.payload),
    }
    const custom: PropertyRecordDraft = {
      ...measured('custom', 1), record_type: 'property', property_code: 'custom',
      custom_property_key: 'custom-lambda', method_code: null, name_raw: 'lambda',
      definition_key: 'record.superconductive_properties.custom', payload: {},
    }
    const onChange = vi.fn()
    render(<PropertyModuleEditor modules={[{ ...initialModules()[0], records: [measured('measured', 4.2), predicted, custom] }]} onChange={onChange} />)
    const prediction = await screen.findByRole('button', { name: /记录 2.*预测 Tc.*allen_dynes/ })
    const property = screen.getByRole('button', { name: /记录 3.*自定义性质.*lambda/ })
    expect(await screen.findByLabelText('计算软件')).toHaveValue('Quantum ESPRESSO')
    expect(screen.getByLabelText('μ*')).toHaveValue(0.1)
    const user = userEvent.setup()
    prediction.focus()
    await user.keyboard(' ')
    expect(prediction).toHaveAttribute('aria-expanded', 'false')
    expect(property).toHaveAttribute('aria-expanded', 'true')
    await user.click(property)
    expect(property).toHaveAttribute('aria-expanded', 'false')
    expect(screen.getByRole('button', { name: /记录 1.*测量 Tc/ })).toHaveAttribute('aria-expanded', 'true')
    expect(onChange).not.toHaveBeenCalled()
  })
})
