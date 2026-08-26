import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import { api } from '../../frontend/src/lib/api'
import type { DraftMaterialState, UploadDraft } from '../../frontend/src/lib/paperProcessing'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const actual = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  return {
    ...actual,
    loadClassificationCatalogs: vi.fn(async () => ({
      material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
      structure_families: [
        { id: 10, name: '笼状结构', aliases: ['clathrate'] },
        { id: 11, name: '层状结构', aliases: ['layered'] },
      ],
      material_dimensionalities: [
        { value: 'three_dimensional', name: '三维' },
        { value: 'unknown', name: '未知' },
      ],
    })),
  }
})

vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const mockedApi = vi.mocked(api)

const makeState = (overrides: Partial<DraftMaterialState> = {}): DraftMaterialState => ({
  material: 'LaH10',
  material_family: null,
  structure_families: [],
  element_count: 2,
  material_dimensionality: 'unknown',
  tc_results: [],
  properties: [],
  ...overrides,
})

const makeDraft = (states: DraftMaterialState[]) => ({
  paper: {
    title: '测试论文', authors: [], paper_type: 'experimental',
    keywords_tags: ['超导'], methodology: ['高压合成'],
  },
  material_states: states,
  structure_candidates: [], classification_evidence: [], field_evidence: {},
} as UploadDraft)

const collapseContent = (index: number) => document.getElementById(`material-state-${index}-content`)

beforeEach(() => {
  mockedApi.get.mockImplementation((url: string) => {
    if (String(url).includes('/space-groups')) {
      return Promise.resolve({
        space_groups: [
          { number: 139, symbol: 'I4/mmm' },
          { number: 194, symbol: 'P6_3/mmc' },
          { number: 225, symbol: 'Fm-3m' },
        ],
      } as never)
    }
    return Promise.resolve({ ok: true, data: makeDraft([makeState()]) } as never)
  })
  mockedApi.put.mockResolvedValue({ ok: true } as never)
  mockedApi.post.mockResolvedValue({ ok: true, paper_id: 99, review_status: 'pending' } as never)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('上传校对页布局与材料状态折叠', () => {
  it('不显示研究材料输入框，关键词与研究方法在同一并排容器中且等高', async () => {
    render(<UploadTaskEditor taskId={'a'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    const keywords = await screen.findByLabelText('关键词（每行一个）')
    const methodology = screen.getByLabelText('研究方法（每行一项）')
    expect(screen.queryByLabelText('研究材料（每行一个）')).not.toBeInTheDocument()

    const keywordsCell = keywords.closest('.MuiTextField-root')?.parentElement
    const methodologyCell = methodology.closest('.MuiTextField-root')?.parentElement
    expect(keywordsCell).not.toBeNull()
    expect(methodologyCell).not.toBeNull()
    expect(keywordsCell!.parentElement).toBe(methodologyCell!.parentElement)
  })

  it('多于 2 张卡片时默认仅展开第一张，支持全部折叠/全部展开与单卡折叠', async () => {
    render(<UploadTaskEditor taskId={'b'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({ material: 'LaH10' }),
      makeState({ material: 'H3S' }),
      makeState({ material: 'MgB2' }),
    ])} />)

    await screen.findByText('材料状态 #1')
    expect(collapseContent(0)).toHaveClass('MuiCollapse-entered')
    expect(collapseContent(1)).not.toHaveClass('MuiCollapse-entered')
    expect(collapseContent(2)).not.toHaveClass('MuiCollapse-entered')

    fireEvent.click(screen.getByRole('button', { name: '全部折叠' }))
    await waitFor(() => expect(collapseContent(0)).not.toHaveClass('MuiCollapse-entered'))
    expect(collapseContent(1)).not.toHaveClass('MuiCollapse-entered')
    expect(collapseContent(2)).not.toHaveClass('MuiCollapse-entered')

    fireEvent.click(screen.getByRole('button', { name: '全部展开' }))
    await waitFor(() => expect(collapseContent(2)).toHaveClass('MuiCollapse-entered'))
    expect(collapseContent(0)).toHaveClass('MuiCollapse-entered')
    expect(collapseContent(1)).toHaveClass('MuiCollapse-entered')

    fireEvent.click(screen.getByRole('button', { name: /材料状态 #2/ }))
    await waitFor(() => expect(collapseContent(1)).not.toHaveClass('MuiCollapse-entered'))
    expect(collapseContent(0)).toHaveClass('MuiCollapse-entered')
    expect(collapseContent(2)).toHaveClass('MuiCollapse-entered')

    fireEvent.click(screen.getByRole('button', { name: /材料状态 #2/ }))
    await waitFor(() => expect(collapseContent(1)).toHaveClass('MuiCollapse-entered'))
    expect(collapseContent(0)).toHaveClass('MuiCollapse-entered')
  })

  it('不超过 2 张卡片时默认全部展开', async () => {
    render(<UploadTaskEditor taskId={'c'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({ material: 'LaH10' }),
      makeState({ material: 'H3S' }),
    ])} />)

    await screen.findByText('材料状态 #1')
    expect(collapseContent(0)).toHaveClass('MuiCollapse-entered')
    expect(collapseContent(1)).toHaveClass('MuiCollapse-entered')
  })
})

describe('超导类型与条件化 Tc 字段', () => {
  it('未知类型添加 Tc 仅含数值框，常规类型含完整字段组且方法可选其他，切换类型数据保留', async () => {
    render(<UploadTaskEditor taskId={'d'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    fireEvent.click(await screen.findByRole('button', { name: '添加 Tc' }))
    expect(await screen.findByLabelText('Tc 数值 (K)')).toBeInTheDocument()
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Tc 方法' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Tc #1 原始值')).not.toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '常规 (BCS)' }))
    expect(await screen.findByLabelText('电声耦合强度 λ')).toBeInTheDocument()
    expect(screen.getByLabelText('对数声子频率 ωlog (K)')).toBeInTheDocument()
    expect(screen.getByLabelText('库伦屏蔽常数 μ*')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Tc 方法' })).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Tc 方法' }))
    fireEvent.click(await screen.findByRole('option', { name: '其他' }))
    fireEvent.change(await screen.findByLabelText('自定义 Tc 方法'), { target: { value: 'two-band model' } })
    fireEvent.change(screen.getByLabelText('电声耦合强度 λ'), { target: { value: '1.5' } })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '非常规' }))
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Tc 方法' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Tc 数值 (K)')).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '常规 (BCS)' }))
    expect(await screen.findByLabelText('电声耦合强度 λ')).toHaveValue(1.5)
    expect(screen.getByLabelText('自定义 Tc 方法')).toHaveValue('two-band model')
  })

  it('非常规类型添加 Tc 仅含数值框，且不再显示状态级 λ/ωlog 输入框', async () => {
    render(<UploadTaskEditor taskId={'e'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({ superconductor_kind: 'unconventional' }),
    ])} />)

    fireEvent.click(await screen.findByRole('button', { name: '添加 Tc' }))
    expect(await screen.findByLabelText('Tc 数值 (K)')).toBeInTheDocument()
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('对数声子频率 ωlog (K)')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('库伦屏蔽常数 μ*')).not.toBeInTheDocument()
  })

  it('首次添加常规 Tc 条目时用状态级旧值一次性预填 λ/ωlog', async () => {
    render(<UploadTaskEditor taskId={'f'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({
        superconductor_kind: 'conventional',
        calculation_context: { phonon_nuclear_treatment: 'unknown', lambda_ep: 1.2, omega_log_k: 210, mu_star: 0.1 },
      }),
    ])} />)

    fireEvent.click(await screen.findByRole('button', { name: '添加 Tc' }))
    expect(await screen.findByLabelText('电声耦合强度 λ')).toHaveValue(1.2)
    expect(screen.getByLabelText('对数声子频率 ωlog (K)')).toHaveValue(210)
    expect(screen.getByLabelText('库伦屏蔽常数 μ*')).toHaveValue(null)

    fireEvent.click(screen.getByRole('button', { name: '添加 Tc' }))
    const lambdas = screen.getAllByLabelText('电声耦合强度 λ')
    expect(lambdas[1]).toHaveValue(null)
  })
})

describe('空间群标准表自动补全', () => {
  it('选中标准符号 Fm-3m 自动带出群号 225，自由输入原样保留', async () => {
    render(<UploadTaskEditor taskId={'0'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    const symbolInput = await screen.findByLabelText('空间群符号')
    fireEvent.change(symbolInput, { target: { value: 'Fm-3m' } })
    fireEvent.click(await screen.findByRole('option', { name: 'Fm-3m' }))
    expect(screen.getByLabelText('空间群号')).toHaveValue(225)
    expect(screen.getByLabelText('空间群符号')).toHaveValue('Fm-3m')

    fireEvent.change(screen.getByLabelText('空间群符号'), { target: { value: '非标准符号X' } })
    expect(screen.getByLabelText('空间群符号')).toHaveValue('非标准符号X')
  })
})

describe('文案、主结构家族说明与模块顺序', () => {
  it('显示压强文案与主结构家族说明，结构附件渲染在 Tc 与普通物性之后', async () => {
    render(<UploadTaskEditor taskId={'1'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState(),
      makeState({
        material: 'H3S',
        structure_families: [{ id: 10, name: '笼状结构', status: 'confirmed', is_primary: true }],
      }),
    ])} />)

    expect((await screen.findAllByLabelText('压强 (GPa)')).length).toBe(2)
    expect(screen.queryByLabelText('压力 (GPa)')).not.toBeInTheDocument()
    expect(screen.getByText('请先选择结构家族')).toBeInTheDocument()
    expect(screen.getByText('主结构家族为已选结构家族中的主要一项')).toBeInTheDocument()

    const tcHeadings = screen.getAllByText('临界温度 Tc')
    const propertiesHeadings = screen.getAllByText('其他普通物性')
    const panels = screen.getAllByTestId('structure-candidate-panel')
    expect(
      tcHeadings[0].compareDocumentPosition(panels[0]) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
    expect(
      propertiesHeadings[0].compareDocumentPosition(panels[0]) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy()
  })
})

describe('energy above hull 预置物性', () => {
  it('点击预置按钮生成空值条目且重复添加被禁用', async () => {
    render(<UploadTaskEditor taskId={'2'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    const addButton = await screen.findByRole('button', { name: 'energy above hull' })
    expect(addButton).toBeEnabled()

    fireEvent.click(addButton)
    expect(screen.getByDisplayValue('energy above hull')).toBeInTheDocument()
    expect(screen.getByDisplayValue('eV/atom')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'energy above hull' })).toBeDisabled()
  })

  it('已存在同名条目（忽略大小写）时按钮禁用', async () => {
    render(<UploadTaskEditor taskId={'3'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({ properties: [{ name: 'Energy Above Hull', name_raw: 'Energy Above Hull', value_raw: '0', unit: 'eV/atom' }] }),
    ])} />)

    expect(await screen.findByRole('button', { name: 'energy above hull' })).toBeDisabled()
  })
})
