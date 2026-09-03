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
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import MaterialStatesEditor from '../../frontend/src/components/MaterialStatesEditor'
import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import type { DraftMaterialState } from '../../frontend/src/lib/paperProcessing'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
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
