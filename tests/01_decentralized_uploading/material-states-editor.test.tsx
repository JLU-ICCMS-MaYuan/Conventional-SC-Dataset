/**
 * Feature #76-4：材料状态编辑区抽成共享受控组件（FR-023）
 * Spec: docs/specs/76-review-scientific-data-editing/（R5、T017）
 *
 * - T017-1：readOnly 模式下组件不可编辑（编辑不触发 onChange、卡片恒展开、无折叠交互）。
 * - T017-2：传入 issues 时对应字段显示错误态（data-issue-field 锚点 + helperText 错误文案）。
 * - T017-3：交互后 onChange 回调传出**完整**状态数组（改化学式后数组含更新后的 material）。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MaterialStatesEditor from '../../frontend/src/components/MaterialStatesEditor'
import PaperEditView from '../../frontend/src/components/PaperEditView'
import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import { normalizeUploadDraft, type DraftMaterialState } from '../../frontend/src/lib/paperProcessing'
import { api } from '../../frontend/src/lib/api'
import SchemaDrivenRecordForm from '../../frontend/src/components/SchemaDrivenRecordForm'
import {
  clearFormDefinitionCache, loadFormDefinition, type FormDefinition,
} from '../../frontend/src/lib/formDefinitions'
import {
  clonePropertyRecord, emptyPropertyModule, PROPERTY_SCHEMA_VERSION, type PropertyRecordDraft,
} from '../../frontend/src/lib/propertyModules'
import { collectPropertyRows } from '../../frontend/src/lib/paperDetailView'
import formDefinitionMatrix from '../fixtures/issue90/form-definition-matrix.json'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { download: vi.fn(), get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const actual = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  return {
    ...actual,
    loadClassificationCatalogs: vi.fn(async () => ({
      material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
      structure_families: [{ id: 10, name: '笼状结构', aliases: ['clathrate'] }],
      material_dimensionalities: [{ value: 'unknown', name: '未知' }],
    })),
  }
})

vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const makeState = (overrides: Partial<DraftMaterialState> = {}): DraftMaterialState => ({
  material: 'LaH10',
  structure_families: [],
  element_count: 2,
  material_dimensionality: 'unknown',
  tc_results: [],
  properties: [],
  ...overrides,
})

const renderEditor = (overrides: Partial<React.ComponentProps<typeof MaterialStatesEditor>> = {}) => {
  const onChange = vi.fn()
  const utils = render(
    <MaterialStatesEditor
      states={[makeState()]}
      onChange={onChange}
      catalogs={null}
      taskId={'5'.repeat(32)}
      {...overrides}
    />,
  )
  return { onChange, ...utils }
}

describe('MaterialStatesEditor 共享组件（T017）', () => {
  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('readOnly 模式下不可编辑：编辑输入不触发 onChange，卡片恒展开且无折叠交互', () => {
    const { onChange, rerender } = renderEditor({
      readOnly: true,
      states: [makeState(), makeState({ material: 'H3S' }), makeState({ material: 'MgB2' })],
    })

    // 卡片数 >2 时默认折叠规则失效：readOnly 下恒展开
    expect(document.getElementById('material-state-0-content')).toHaveClass('MuiCollapse-entered')
    expect(document.getElementById('material-state-1-content')).toHaveClass('MuiCollapse-entered')
    expect(document.getElementById('material-state-2-content')).toHaveClass('MuiCollapse-entered')

    // 点击卡片头部不改变展开状态（不可折叠交互）
    const header = screen.getByRole('button', { name: /材料状态 #1/ })
    expect(header).toHaveAttribute('aria-expanded', 'true')
    fireEvent.click(header)
    expect(header).toHaveAttribute('aria-expanded', 'true')

    // 编辑输入不触达父级 onChange
    fireEvent.change(screen.getAllByLabelText('化学式')[0], { target: { value: 'H3S' } })
    expect(onChange).not.toHaveBeenCalled()
  })

  it('传入 issues 时对应字段显示错误态（data-issue-field 锚点与错误文案）', async () => {
    renderEditor({
      issues: [{ stateIndex: 0, field: 'material_states[0].material', message: '第 1 个材料状态缺少化学式' }],
    })

    const anchor = document.querySelector('[data-issue-field="material_states[0].material"]')
    expect(anchor).not.toBeNull()
    expect(anchor).toHaveTextContent('第 1 个材料状态缺少化学式')

    const input = await screen.findByLabelText('化学式')
    expect(input).toHaveAttribute('aria-invalid', 'true')
  })

  it('交互后 onChange 回调传出完整状态数组', () => {
    const { onChange } = renderEditor({ states: [makeState({ material: 'H3S' }), makeState()] })

    fireEvent.change(screen.getAllByLabelText('化学式')[1], { target: { value: 'MgB2' } })

    expect(onChange).toHaveBeenCalledTimes(1)
    const nextStates = onChange.mock.calls[0][0] as DraftMaterialState[]
    // 完整数组：长度不变，更新项含新化学式，未编辑项原样保留
    expect(nextStates).toHaveLength(2)
    expect(nextStates[0]).toEqual(expect.objectContaining({ material: 'H3S' }))
    expect(nextStates[1]).toEqual(expect.objectContaining({ material: 'MgB2', element_count: 2 }))
    expect(nextStates[0]).not.toBe(nextStates[1])
  })

  it('Tc 方法决定字段集：新增条目先选方法，切为实验后删除计算上下文', async () => {
    const { onChange, rerender } = renderEditor({
      superconductorKind: 'unconventional',
      states: [makeState({
        tc_results: [{
          result_kind: 'theoretical', tc_method: 'mcmillan', tc_value_k: 39,
          calculation_context: { lambda_ep: 1.1, omega_log_k: 600, mu_star: 0.1 },
        }],
      })],
    })

    expect(await screen.findByLabelText('电声耦合强度 λ')).toHaveValue(1.1)
    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Tc 方法' }))
    fireEvent.click(await screen.findByRole('option', { name: '实验测量' }))

    const switchedStates = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(switchedStates[0].tc_results?.[0]).toMatchObject({
      result_kind: 'experimental', tc_method: 'experimental',
    })
    expect(switchedStates[0].tc_results?.[0].calculation_context).toBeUndefined()

    rerender(
      <MaterialStatesEditor
        states={switchedStates}
        onChange={onChange}
        catalogs={null}
        taskId={'5'.repeat(32)}
        superconductorKind="unconventional"
      />,
    )
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: '添加 Tc' }))
    const addedStates = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(addedStates[0].tc_results).toHaveLength(2)
    expect(addedStates[0].tc_results?.[1]).toMatchObject({
      result_kind: 'theoretical', tc_method: 'unknown',
    })
    expect(addedStates[0].tc_results?.[1].calculation_context).toBeUndefined()
  })

  it('中文界面的 Tc 方法选项均使用中文说明', async () => {
    renderEditor({ states: [makeState({ tc_results: [{ result_kind: 'theoretical', tc_method: 'unknown' }] })] })

    fireEvent.mouseDown(await screen.findByRole('combobox', { name: 'Tc 方法' }))

    expect(await screen.findByRole('option', { name: 'McMillan 方法' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'Allen-Dynes 方法' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '各向同性 Migdal-Eliashberg 方法' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '各向异性 Migdal-Eliashberg 方法' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: '超导密度泛函理论（SCDFT）' })).toBeInTheDocument()
  })
})

describe('Issue #90 模块化物性与 Schema 表单', () => {
  const definitions = formDefinitionMatrix.definitions as FormDefinition[]
  const predictedDefinition = definitions[0]
  const predictedRecord = (overrides: Partial<PropertyRecordDraft> = {}): PropertyRecordDraft => ({
    record_key: 'tc-a', module_code: 'superconductive_properties', record_type: 'predicted_tc',
    property_code: 'tc', definition_key: predictedDefinition.definition_key, definition_version: 1,
    name_raw: 'critical temperature', value_kind: 'number', value_raw: '250 K', value_number: 250,
    unit_raw: 'K', canonical_unit: 'K', method_code: 'allen_dynes', is_representative: true,
    payload: structuredClone(formDefinitionMatrix.valid_records.predicted_tc.payload), evidences: [], ...overrides,
  })

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
    clearFormDefinitionCache()
  })

  it('新材料状态可直接添加四类模块，模块带定义版本且未生成空记录', async () => {
    const { onChange } = renderEditor({ states: [makeState({ property_modules: [] })] })
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '添加物性模块' }))
    fireEvent.click(await screen.findByRole('option', { name: '电子性质' }))

    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules).toEqual([
      expect.objectContaining({
        module_code: 'electronic_properties', definition_key: 'module.electronic_properties',
        definition_version: 1, display_order: 0, records: [],
      }),
    ])
  })

  it('新建材料状态使用共享 Schema v2，且不再生成旧物性字段', () => {
    const { onChange } = renderEditor({ states: [] })
    fireEvent.click(screen.getByRole('button', { name: '添加材料状态' }))

    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(formDefinitionMatrix.schema_version).toBe(PROPERTY_SCHEMA_VERSION)
    expect(states[0]).toMatchObject({
      schema_version: formDefinitionMatrix.schema_version,
      property_modules: [],
      deleted_record_keys: [],
      deleted_module_keys: [],
    })
    expect(states[0]).not.toHaveProperty('calculation_context')
    expect(states[0]).not.toHaveProperty('experimental_context')
    expect(states[0]).not.toHaveProperty('tc_results')
    expect(states[0]).not.toHaveProperty('properties')
  })

  it('按模块获取定义并通过定义选择新增预测 Tc', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.startsWith('/api/form-definitions?')) return Promise.resolve(definitions.slice(0, 2) as never)
      const definition = definitions.find(item => url.includes(encodeURIComponent(item.definition_key)))
      return definition ? Promise.resolve(definition as never) : Promise.reject(new Error('not found'))
    })
    const module = emptyPropertyModule('superconductive_properties', 0)
    const { onChange } = renderEditor({ states: [makeState({ property_modules: [module] })] })

    fireEvent.mouseDown(await screen.findByRole('combobox', { name: '添加记录' }))
    fireEvent.click(await screen.findByRole('option', { name: /预测 Tc · allen_dynes/ }))
    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules?.[0].records[0]).toMatchObject({
      record_type: 'predicted_tc', method_code: 'allen_dynes',
      definition_key: predictedDefinition.definition_key,
      payload: { calculation_conditions: {}, parameters: {} },
    })
  })

  it('定义按键和版本缓存，同一历史版本只请求一次', async () => {
    vi.mocked(api.get).mockResolvedValue(predictedDefinition as never)
    const first = await loadFormDefinition(predictedDefinition.definition_key, 1)
    const second = await loadFormDefinition(predictedDefinition.definition_key, 1)
    expect(first).toBe(second)
    expect(api.get).toHaveBeenCalledTimes(1)
  })

  it('仅允许删除空模块，并把稳定模块键写入删除元数据', () => {
    const emptyModule = { ...emptyPropertyModule('electronic_properties', 0), module_key: 'module-empty' }
    const occupiedModule = {
      ...emptyPropertyModule('superconductive_properties', 1), module_key: 'module-occupied', records: [predictedRecord()],
    }
    const { onChange } = renderEditor({
      states: [makeState({ property_modules: [emptyModule, occupiedModule] })],
    })

    const emptyRegion = screen.getByTestId('property-module-electronic_properties')
    const occupiedRegion = screen.getByTestId('property-module-superconductive_properties')
    expect(within(emptyRegion).getByRole('button', { name: '删除模块' })).toBeEnabled()
    expect(within(occupiedRegion).getByRole('button', { name: '删除模块' })).toBeDisabled()

    fireEvent.click(within(emptyRegion).getByRole('button', { name: '删除模块' }))
    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules).toEqual([
      expect.objectContaining({ module_key: 'module-occupied', display_order: 0 }),
    ])
    expect(states[0].deleted_module_keys).toEqual(['module-empty'])
  })

  it('删除记录时保留模块，并把稳定记录键写入删除元数据', async () => {
    vi.mocked(api.get).mockResolvedValue(predictedDefinition as never)
    const module = {
      ...emptyPropertyModule('superconductive_properties', 0), records: [predictedRecord({ record_key: 'record-deleted' })],
    }
    const { onChange } = renderEditor({ states: [makeState({ property_modules: [module] })] })

    fireEvent.click(await screen.findByRole('button', { name: '删除记录' }))
    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules?.[0].records).toEqual([])
    expect(states[0].deleted_record_keys).toEqual(['record-deleted'])
  })

  it('模块上下移动后按视觉顺序重写 display_order', () => {
    const superconductive = { ...emptyPropertyModule('superconductive_properties', 0), module_key: 'module-first' }
    const electronic = { ...emptyPropertyModule('electronic_properties', 1), module_key: 'module-second' }
    const { onChange } = renderEditor({
      states: [makeState({ property_modules: [superconductive, electronic] })],
    })

    const firstRegion = screen.getByTestId('property-module-superconductive_properties')
    fireEvent.click(within(firstRegion).getByRole('button', { name: '下移模块' }))
    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules).toEqual([
      expect.objectContaining({ module_key: 'module-second', display_order: 0 }),
      expect.objectContaining({ module_key: 'module-first', display_order: 1 }),
    ])
  })

  it('记录定义由预测 Tc 切为测量 Tc 时替换条件分组', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (url.startsWith('/api/form-definitions?')) return Promise.resolve(definitions.slice(0, 2) as never)
      const definition = definitions.find(item => url.includes(encodeURIComponent(item.definition_key)))
      return definition ? Promise.resolve(definition as never) : Promise.reject(new Error('not found'))
    })
    const module = {
      ...emptyPropertyModule('superconductive_properties', 0), records: [predictedRecord()],
    }
    const { onChange } = renderEditor({ states: [makeState({ property_modules: [module] })] })

    fireEvent.mouseDown(await screen.findByRole('combobox', { name: '记录定义' }))
    fireEvent.click(await screen.findByRole('option', { name: /测量 Tc · resistivity/ }))
    const states = onChange.mock.calls.at(-1)?.[0] as DraftMaterialState[]
    expect(states[0].property_modules?.[0].records[0]).toMatchObject({
      record_type: 'measured_tc',
      method_code: 'resistivity',
      definition_key: 'record.superconductive_properties.measured_tc.resistivity',
      payload: { experimental_conditions: {} },
    })
    expect(states[0].property_modules?.[0].records[0].payload).not.toHaveProperty('calculation_conditions')
    expect(states[0].property_modules?.[0].records[0].payload).not.toHaveProperty('parameters')
  })

  it('Schema 表单渲染 Conditions/参数/预留分组并保持嵌套错误路径', () => {
    const onChange = vi.fn()
    render(<SchemaDrivenRecordForm record={predictedRecord()} definition={predictedDefinition} onChange={onChange} />)
    expect(screen.getByLabelText('计算软件')).toHaveValue('Quantum ESPRESSO')
    expect(screen.getByLabelText('μ*')).toHaveValue(0.1)
    fireEvent.change(screen.getByLabelText('计算软件'), { target: { value: 'VASP' } })
    expect(onChange.mock.calls.at(-1)?.[0].payload.calculation_conditions.calculation_code).toBe('VASP')
    fireEvent.click(screen.getAllByRole('button', { name: '新增字段' })[1])
    expect(onChange.mock.calls.at(-1)?.[0].payload.parameters.extensions[0]).toMatchObject({
      name_raw: '', value_kind: 'number', value_raw: '', unit_raw: '',
    })
  })

  it('复制记录深复制 Conditions、参数和 extensions，并生成独立稳定键', () => {
    const original = predictedRecord()
    const copy = clonePropertyRecord(original)
    ;(copy.payload.parameters as Record<string, any>).mu_star = 0.15
    ;((copy.payload.parameters as Record<string, any>).extensions as any[]).push({ field_key: 'local' })
    expect(copy.record_key).not.toBe(original.record_key)
    expect((original.payload.parameters as Record<string, any>).mu_star).toBe(0.1)
    expect((original.payload.parameters as Record<string, any>).extensions).toEqual([])
  })

  it('详情只消费目标记录，迁移观察期存在旧字段也不重复计数', () => {
    const rows = collectPropertyRows({
      key_properties: [{ id: 1, name: 'legacy', value_raw: '250' }],
      material_states: [{
        id: 1, material: 'LaH10', tc_results: [{ id: 1, tc_value_k: 250 }],
        property_modules: [{ module_code: 'superconductive_properties', records: [predictedRecord()] }],
      }],
    })
    expect(rows.filter(row => row.label === 'Tc')).toHaveLength(1)
    expect(rows.find(row => row.label === 'Tc')).toMatchObject({ label: 'Tc', value: '250 K' })
  })

  it('详情页提供材料状态 JSON 导出入口并调用版本化导出接口', async () => {
    vi.mocked(api.download).mockResolvedValue(new Blob(['{}'], { type: 'application/json' }) as never)
    const createObjectURL = vi.fn(() => 'blob:material-state')
    const revokeObjectURL = vi.fn()
    Object.defineProperty(URL, 'createObjectURL', { configurable: true, value: createObjectURL })
    Object.defineProperty(URL, 'revokeObjectURL', { configurable: true, value: revokeObjectURL })
    const linkClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

    render(<PaperEditView paper={{
      id: 90,
      title: 'Issue 90',
      content_revision: 7,
      material_states: [{ id: 12, state_key: 'state-lah10-170gpa', material: 'LaH10', property_modules: [] }],
    }} onBack={() => undefined} />)

    fireEvent.click(screen.getByRole('button', { name: '导出材料状态' }))
    await waitFor(() => expect(api.download).toHaveBeenCalledWith('/api/papers/90/material-states/state-lah10-170gpa/export'))
    expect(createObjectURL).toHaveBeenCalled()
    expect(linkClick).toHaveBeenCalled()
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:material-state')
  })

  it('旧草稿单向转换为带版本的统一模块，未知未来版本明确失败', () => {
    const converted = normalizeUploadDraft({
      paper: {},
      material_states: [{ material: 'LaH10', tc_results: [{ result_kind: 'theoretical', tc_method: 'allen_dynes', tc_value_k: 250 }] }],
    })
    expect(formDefinitionMatrix.schema_version).toBe(PROPERTY_SCHEMA_VERSION)
    expect(converted.material_states[0]).toMatchObject({ schema_version: formDefinitionMatrix.schema_version })
    expect(converted.material_states[0].property_modules?.[0].records[0]).toMatchObject({
      record_type: 'predicted_tc', value_number: 250,
    })
    expect(converted.material_states[0].tc_results).toBeUndefined()
    expect(() => normalizeUploadDraft({ paper: {}, material_states: [{ schema_version: 99 }] })).toThrow('不支持的物性草稿 Schema 版本')
  })
})

describe('未分配结构候选的分配与确认（Issue #77）', () => {
  const unassignedCandidate = (overrides: Record<string, unknown> = {}) => ({
    candidate_id: 'cand-unassigned-1',
    material_state_ref: 'unassigned:file-1',
    source_kind: 'attachment',
    status: 'valid',
    confirmation: 'unreviewed',
    original_format: 'vasp',
    original_text: null,
    validation: { ase_valid: true, structure_hash: 'h1', atom_count: 1 },
    derivation: null,
    representations: { conventional: { cif: { text: 'data_Hg', available: true } } },
    sources: [{ file_id: 'file-1', filename: 'Hg-R-3m.vasp', role: 'attachment' }],
    conflicts: [],
    user_note: null,
    ...overrides,
  })

  const renderWithCandidates = (overrides: Partial<React.ComponentProps<typeof MaterialStatesEditor>> = {}) => {
    const onStructureCandidatesChange = vi.fn()
    const utils = render(
      <MaterialStatesEditor
        states={[makeState({ material: 'Hg' })]}
        onChange={vi.fn()}
        catalogs={null}
        taskId={'5'.repeat(32)}
        structureCandidates={[unassignedCandidate()]}
        onStructureCandidatesChange={onStructureCandidatesChange}
        {...overrides}
      />,
    )
    return { onStructureCandidatesChange, ...utils }
  }

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('T004：存在 unassigned 候选时渲染未分配区（文件名与校验状态可见）', () => {
    renderWithCandidates()
    const region = document.querySelector('[data-testid="unassigned-candidates"]')
    expect(region).not.toBeNull()
    expect(region).toHaveTextContent('Hg-R-3m.vasp')
    expect(region).toHaveTextContent('待确认')
  })

  it('T005：选择材料状态并「采用」后候选被分配确认', () => {
    const { onStructureCandidatesChange } = renderWithCandidates()

    fireEvent.mouseDown(screen.getByLabelText('分配到材料状态'))
    fireEvent.click(screen.getByRole('option', { name: /材料状态 #1/ }))
    fireEvent.click(screen.getByRole('button', { name: '采用此结构' }))

    expect(onStructureCandidatesChange).toHaveBeenCalledTimes(1)
    const next = onStructureCandidatesChange.mock.calls[0][0] as Array<Record<string, unknown>>
    expect(next[0]).toMatchObject({
      candidate_id: 'cand-unassigned-1',
      material_state_ref: 'material_states[0]',
      confirmation: 'confirmed',
      status: 'confirmed',
    })
  })

  it('T006：无材料状态时采用禁用并提示先创建', () => {
    renderWithCandidates({ states: [] })
    const region = document.querySelector('[data-testid="unassigned-candidates"]')
    expect(region).toHaveTextContent('请先创建材料状态后再分配结构')
    expect(screen.getByRole('button', { name: '采用此结构' })).toBeDisabled()
  })

  it('T007：blocked 候选采用禁用并显示校验失败原因', () => {
    renderWithCandidates({
      structureCandidates: [unassignedCandidate({
        status: 'blocked',
        validation: { ase_valid: false, message: '无法解析结构', code: 'structure_read_failed' },
      })],
    })
    const region = document.querySelector('[data-testid="unassigned-candidates"]')
    expect(region).toHaveTextContent('需要人工处理')
    expect(region).toHaveTextContent('校验失败：无法解析结构')
    // blocked 候选不提供采用入口（不得确认，FR-004）
    expect(screen.queryByRole('button', { name: '采用此结构' })).not.toBeInTheDocument()
  })

  it('T008：排除后候选标记 excluded 且不再显示', () => {
    const { onStructureCandidatesChange, rerender } = renderWithCandidates()
    fireEvent.click(screen.getByRole('button', { name: '不采用' }))
    expect(onStructureCandidatesChange).toHaveBeenCalledTimes(1)
    const next = onStructureCandidatesChange.mock.calls[0][0] as Array<Record<string, unknown>>
    expect(next[0]).toMatchObject({ confirmation: 'excluded', status: 'excluded' })

    // 排除后重新渲染：未分配区消失
    rerender(
      <MaterialStatesEditor
        states={[makeState({ material: 'Hg' })]}
        onChange={vi.fn()}
        catalogs={null}
        taskId={'5'.repeat(32)}
        structureCandidates={[{ ...unassignedCandidate(), confirmation: 'excluded', status: 'excluded' }]}
        onStructureCandidatesChange={onStructureCandidatesChange}
      />,
    )
    expect(document.querySelector('[data-testid="unassigned-candidates"]')).toBeNull()
  })

  it('T009：readOnly 下不渲染未分配区', () => {
    renderWithCandidates({ readOnly: true })
    expect(document.querySelector('[data-testid="unassigned-candidates"]')).toBeNull()
  })
})


describe('T010：UploadTaskEditor 集成（Issue #77）', () => {
  const unassignedCandidate = (overrides: Record<string, unknown> = {}) => ({
    candidate_id: 'cand-unassigned-1',
    material_state_ref: 'unassigned:file-1',
    source_kind: 'attachment',
    status: 'valid',
    confirmation: 'unreviewed',
    original_format: 'vasp',
    original_text: null,
    validation: { ase_valid: true, structure_hash: 'h1', atom_count: 1 },
    derivation: null,
    representations: { conventional: { cif: { text: 'data_Hg', available: true } } },
    sources: [{ file_id: 'file-1', filename: 'Hg-R-3m.vasp', role: 'attachment' }],
    conflicts: [],
    user_note: null,
    ...overrides,
  })

  const draftWithUnassigned = {
    paper: {
      title: 'Hg study', authors: [], paper_type: 'experimental',
      research_materials: ['Hg'], keywords_tags: [], methodology: [],
      material_families: [{ id: 1, name: '单质超导体', status: 'confirmed' }],
    },
    material_states: [{
      material: 'Hg', structure_families: [],
      element_count: 1, material_dimensionality: 'unknown',
      tc_results: [], properties: [],
    }],
    structure_candidates: [unassignedCandidate()],
    classification_evidence: [], field_evidence: {},
  }

  afterEach(() => {
    cleanup()
    vi.clearAllMocks()
  })

  it('校对页展示未分配候选；分配确认后保存草稿的 structure_candidates 含 confirmed 候选', async () => {
    vi.mocked(api.get).mockImplementation((url: string) => {
      if (String(url).includes('/space-groups')) {
        return Promise.resolve({ space_groups: [] } as never)
      }
      return Promise.resolve({ ok: true, data: structuredClone(draftWithUnassigned) } as never)
    })
    vi.mocked(api.put).mockResolvedValue({ ok: true } as never)

    render(<UploadTaskEditor taskId={'c'.repeat(32)} onSubmitted={vi.fn()} draftOverride={draftWithUnassigned} />)

    const region = await screen.findByTestId('unassigned-candidates')
    expect(region).toHaveTextContent('Hg-R-3m.vasp')

    fireEvent.mouseDown(screen.getByLabelText('分配到材料状态'))
    fireEvent.click(await screen.findByRole('option', { name: /材料状态 #1/ }))
    fireEvent.click(screen.getByRole('button', { name: '采用此结构' }))

    fireEvent.click(screen.getByRole('button', { name: '立即保存' }))
    await waitFor(() => expect(api.put).toHaveBeenCalledTimes(1))
    const body = api.put.mock.calls[0][1] as { structure_candidates: Array<Record<string, unknown>> }
    expect(body.structure_candidates[0]).toMatchObject({
      material_state_ref: 'material_states[0]',
      confirmation: 'confirmed',
      status: 'confirmed',
    })
  })
})
