import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import UploadTaskEditor from '../../frontend/src/components/UploadTaskEditor'
import { api } from '../../frontend/src/lib/api'
import type { ApiError } from '../../frontend/src/lib/api'
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
          { number: 227, symbol: 'Fd-3m' },
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

  // 重度交互用例：并行下实测约 3s，默认 5s 上限余量不足
  it('多于 2 张卡片时默认仅展开第一张，支持全部折叠/全部展开与单卡折叠', { timeout: 15000 }, async () => {
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
  // 重度交互用例：单跑约 3s，默认 5s 上限在多文件并行下余量不足，会偶发超时
  it('未知类型添加 Tc 仅含数值框，常规类型含完整字段组且方法可选其他，切换类型数据保留', { timeout: 15000 }, async () => {
    render(<UploadTaskEditor taskId={'d'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    fireEvent.click(await screen.findByRole('button', { name: '添加 Tc' }))
    expect(await screen.findByLabelText('Tc 数值 (K)')).toBeInTheDocument()
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Tc 方法' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Tc #1 原始值')).not.toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '常规超导体（BCS超导体）' }))
    expect(await screen.findByLabelText('电声耦合强度 λ')).toBeInTheDocument()
    expect(screen.getByLabelText('对数声子频率 ωlog (K)')).toBeInTheDocument()
    expect(screen.getByLabelText('库伦屏蔽常数 μ*')).toBeInTheDocument()
    expect(screen.getByRole('combobox', { name: 'Tc 方法' })).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: 'Tc 方法' }))
    fireEvent.click(await screen.findByRole('option', { name: '其他' }))
    fireEvent.change(await screen.findByLabelText('自定义 Tc 方法'), { target: { value: 'two-band model' } })
    fireEvent.change(screen.getByLabelText('电声耦合强度 λ'), { target: { value: '1.5' } })

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '非常规超导体' }))
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByRole('combobox', { name: 'Tc 方法' })).not.toBeInTheDocument()
    expect(screen.getByLabelText('Tc 数值 (K)')).toBeInTheDocument()

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '超导类型' }))
    fireEvent.click(await screen.findByRole('option', { name: '常规超导体（BCS超导体）' }))
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

  it('超导类型下拉仅含两项全称选项，值为 unknown 时显示占位', async () => {
    render(<UploadTaskEditor taskId={'9'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    const kindSelect = await screen.findByRole('combobox', { name: '超导类型' })
    expect(kindSelect).toHaveTextContent('请选择')

    fireEvent.mouseDown(kindSelect)
    const options = await screen.findAllByRole('option')
    expect(options.map(option => option.textContent)).toEqual(['常规超导体（BCS超导体）', '非常规超导体'])
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

describe('文案、类型标签与模块顺序', () => {
  it('显示压强文案与新类型标签，无主结构家族字段，结构附件渲染在 Tc 与普通物性之后', async () => {
    render(<UploadTaskEditor taskId={'1'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState(),
      makeState({
        material: 'H3S',
        structure_families: [{ id: 10, name: '笼状结构', status: 'confirmed', is_primary: true }],
      }),
    ])} />)

    expect((await screen.findAllByLabelText('压强 (GPa)')).length).toBe(2)
    expect(screen.queryByLabelText('压力 (GPa)')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('主结构家族')).not.toBeInTheDocument()
    expect(screen.getAllByLabelText('更多类型标签（可以填写不止一个类型）')).toHaveLength(2)

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

describe('AI 建议单行截断与展开收起', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('长建议默认单行截断，点击展开显示全文，再点击收起恢复单行；短建议无展开按钮', async () => {
    // jsdom 无布局，用 scrollHeight 模拟：含长建议的内容块 240px（>120 阈值），其余 48px
    vi.spyOn(HTMLElement.prototype, 'scrollHeight', 'get').mockImplementation(function (this: HTMLElement) {
      return this.textContent?.includes('超长AI建议') ? 240 : 48
    })
    const draftWithAi = {
      ...makeDraft([makeState()]),
      ai_original: {
        paper: { keywords_tags: [Array.from({ length: 12 }, (_, index) => `超长AI建议${index + 1}`).join('、')] },
      },
    } as UploadDraft
    render(<UploadTaskEditor taskId={'4'.repeat(32)} onSubmitted={vi.fn()} draftOverride={draftWithAi} />)

    const keywordsCell = (await screen.findByLabelText('关键词（每行一个）')).closest('.MuiTextField-root')!.parentElement!
    const collapsedSuggestion = within(keywordsCell).getByText(/^AI 建议：/)
    expect(collapsedSuggestion).toHaveStyle({ whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' })
    // 单行截断仅影响展示，完整文本仍保留在 DOM 中
    expect(collapsedSuggestion.textContent).toContain('超长AI建议12')

    fireEvent.click(within(keywordsCell).getByRole('button', { name: '展开 关键词（每行一个）的 AI 解释' }))
    expect(within(keywordsCell).getByText(/^AI 建议：/)).toHaveStyle({ whiteSpace: 'pre-wrap' })

    fireEvent.click(within(keywordsCell).getByRole('button', { name: '收起 关键词（每行一个）的 AI 解释' }))
    expect(within(keywordsCell).getByText(/^AI 建议：/)).toHaveStyle({ whiteSpace: 'nowrap' })
    expect(within(keywordsCell).getByRole('button', { name: '展开 关键词（每行一个）的 AI 解释' })).toBeInTheDocument()

    // 短建议（标题的「未提供」）未溢出，不出现展开按钮
    const titleCell = screen.getByLabelText('标题').closest('.MuiTextField-root')!.parentElement!
    expect(within(titleCell).getByText('AI 建议：未提供')).toBeInTheDocument()
    expect(within(titleCell).queryByRole('button', { name: /展开/ })).not.toBeInTheDocument()
  })
})

describe('晶系与空间群三方联动', () => {
  it('仅改晶系为四方后，空间群符号下拉仅含 75–142 号符号，已填符号与群号不被清除', async () => {
    render(<UploadTaskEditor taskId={'6'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([
      makeState({ reported_space_group_symbol: 'P6_3/mmc', reported_space_group_number: 194 }),
    ])} />)

    fireEvent.mouseDown(await screen.findByRole('combobox', { name: '晶系' }))
    fireEvent.click(await screen.findByRole('option', { name: '四方' }))

    expect(screen.getByLabelText('空间群符号')).toHaveValue('P6_3/mmc')
    expect(screen.getByLabelText('空间群号')).toHaveValue(194)

    fireEvent.keyDown(screen.getByLabelText('空间群符号'), { key: 'ArrowDown' })
    expect(await screen.findByRole('option', { name: 'I4/mmm' })).toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'P6_3/mmc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Fm-3m' })).not.toBeInTheDocument()
    expect(screen.queryByRole('option', { name: 'Fd-3m' })).not.toBeInTheDocument()
  })

  it('选中标准符号 I4/mmm 自动带出群号 139 且晶系变为四方', async () => {
    render(<UploadTaskEditor taskId={'7'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    fireEvent.change(await screen.findByLabelText('空间群符号'), { target: { value: 'I4/mmm' } })
    fireEvent.click(await screen.findByRole('option', { name: 'I4/mmm' }))

    expect(screen.getByLabelText('空间群号')).toHaveValue(139)
    expect(screen.getByLabelText('空间群符号')).toHaveValue('I4/mmm')
    expect(screen.getByRole('combobox', { name: '晶系' })).toHaveTextContent('四方')
  })

  it('输入合法群号 227 自动带出标准符号 Fd-3m 且晶系变为立方', async () => {
    render(<UploadTaskEditor taskId={'8'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)

    // 群号反查符号依赖标准表，先打开下拉确认数据已加载
    const symbolInput = await screen.findByLabelText('空间群符号')
    fireEvent.keyDown(symbolInput, { key: 'ArrowDown' })
    await screen.findByRole('option', { name: 'Fd-3m' })
    fireEvent.keyDown(symbolInput, { key: 'Escape' })

    fireEvent.change(screen.getByLabelText('空间群号'), { target: { value: '227' } })

    expect(screen.getByLabelText('空间群符号')).toHaveValue('Fd-3m')
    expect(screen.getByRole('combobox', { name: '晶系' })).toHaveTextContent('立方')
  })
})

describe('保存/提交失败的后端错误提示', () => {
  it('保存失败时展示后端 detail.message 并附 code', async () => {
    const apiError = new Error('第 1 个材料状态的压强区间 min 不能大于 max') as ApiError
    apiError.status = 400
    apiError.code = 'invalid_pressure_range'
    apiError.detail = { code: 'invalid_pressure_range', message: '第 1 个材料状态的压强区间 min 不能大于 max' }
    mockedApi.put.mockRejectedValueOnce(apiError)

    render(<UploadTaskEditor taskId={'5'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)
    fireEvent.click(await screen.findByRole('button', { name: '立即保存' }))

    expect(await screen.findByText(
      '保存失败：第 1 个材料状态的压强区间 min 不能大于 max（invalid_pressure_range）',
    )).toBeInTheDocument()
  })

  it('提交失败且响应无 detail 时回退通用文案', async () => {
    const apiError = new Error('Internal Server Error') as ApiError
    apiError.status = 500
    mockedApi.post.mockRejectedValueOnce(apiError)

    render(<UploadTaskEditor taskId={'f'.repeat(32)} onSubmitted={vi.fn()} draftOverride={makeDraft([makeState()])} />)
    fireEvent.click(await screen.findByRole('button', { name: '提交审核' }))

    expect(await screen.findByText('提交审核失败')).toBeInTheDocument()
  })
})
