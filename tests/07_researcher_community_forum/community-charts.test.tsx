/**
 * Feature: 社区图表恢复背景分区与材料家族组合筛选
 *
 * 两个回归同时发生在社区页：
 *
 * 1. 图表接口查的 superconductor_records 表在条件化模型迁移（20260821_0008）里已删除，
 *    GORM 未检查错误，接口恒返回 []，前端又用 `length === 0` 早退成 Alert，
 *    于是连坐标系和品质因子分区都消失了。空数据必须仍渲染坐标系与背景。
 *
 * 2. 分类维度早先硬编码 7 类超导类型，而新模型的分类是 material_families 目录，
 *    且允许用户自建家族（如「单质超导体」），硬编码永远覆盖不到。
 *    图例与多选下拉都必须跟随目录，默认全选。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { MemoryRouter } from 'react-router-dom'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ThemeProvider } from '@mui/material'

import SharePage from '../../frontend/src/pages/share'
import theme from '../../frontend/src/theme'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn().mockResolvedValue({}) },
}))

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({ user: null }),
}))

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer" />,
}))

// jsdom 不实现 ResizeObserver，recharts 的 ResponsiveContainer 需要它。
globalThis.ResizeObserver ??= class {
  observe() {}
  unobserve() {}
  disconnect() {}
} as unknown as typeof ResizeObserver

// ResponsiveContainer 用 getBoundingClientRect 取初始尺寸，jsdom 恒返回 0，
// 于是 recharts 判定容器无尺寸而完全不出图，坐标轴与分区都断言不到。
const ORIGINAL_RECT = Element.prototype.getBoundingClientRect
beforeAll(() => {
  Element.prototype.getBoundingClientRect = function () {
    return { width: 800, height: 390, top: 0, left: 0, bottom: 390, right: 800, x: 0, y: 0, toJSON: () => ({}) } as DOMRect
  }
})
afterAll(() => { Element.prototype.getBoundingClientRect = ORIGINAL_RECT })

const mockedApi = vi.mocked(api)

// 与本地库一致：7 个内置家族 + 用户自建的「单质超导体」
const MATERIAL_FAMILIES = [
  { id: 1, name: '氢基超导体', aliases: [] },
  { id: 2, name: '铜基超导体', aliases: [] },
  { id: 3, name: '铁基超导体', aliases: [] },
  { id: 4, name: '镍基超导体', aliases: [] },
  { id: 5, name: '无机硼碳氮基超导体', aliases: [] },
  { id: 6, name: '有机超导体', aliases: [] },
  { id: 7, name: '重费米子超导体', aliases: [] },
  { id: 8, name: '单质超导体', aliases: [] },
]

const CATALOGS = {
  material_families: MATERIAL_FAMILIES,
  structure_families: [],
  material_dimensionalities: [],
}

const CONTRIBUTIONS = {
  participant_count: 1,
  upload_leaderboard: [],
  review_leaderboard: [],
  generated_at: '2026-09-01T00:00:00Z',
}

// papers id=9 的 Hg 数据：1911 年、4.2 K、约 0 GPa、家族「单质超导体」
const HG_POINT = {
  x: 0.000101, y: 4.2, formula: 'Hg',
  family_id: 8, family_name: '单质超导体',
  type: 'experimental', doi: '', year: 1911, paper_id: 9,
}

const HG_YEAR_POINT = { ...HG_POINT, x: 1911, pressure_gpa: 0.000101 }

const routeApi = (overrides: Record<string, unknown> = {}) => {
  mockedApi.get.mockImplementation((url: string) => {
    if (url.startsWith('/api/classification-catalogs')) return Promise.resolve(CATALOGS)
    if (url.startsWith('/api/community/contributions')) return Promise.resolve(CONTRIBUTIONS)
    if (url.startsWith('/api/chart-groups')) return Promise.resolve([])
    if (url.startsWith('/api/papers/stats/tc-pressure')) {
      return Promise.resolve(overrides.pressure ?? [])
    }
    if (url.startsWith('/api/papers/stats/tc-year')) {
      return Promise.resolve(overrides.year ?? [])
    }
    return Promise.resolve([])
  })
}

const renderShare = () =>
  render(
    <ThemeProvider theme={theme}>
      <MemoryRouter><SharePage /></MemoryRouter>
    </ThemeProvider>,
  )

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  routeApi()
})

afterEach(() => cleanup())

describe('无数据点时仍显示坐标系与品质因子背景', () => {
  it('两张图都渲染出坐标轴，而不是用 Alert 顶掉图表', async () => {
    renderShare()

    await waitFor(() => {
      expect(document.querySelectorAll('.recharts-xAxis').length).toBe(2)
    })
    expect(document.querySelectorAll('.recharts-yAxis').length).toBe(2)
    // 旧实现在空数据时渲染的提示语不应再出现
    expect(screen.queryByText(/请切换字段/)).not.toBeInTheDocument()
  })

  it('压力图画出品质因子色带与 S 等值线标注', async () => {
    renderShare()

    // 6 个区间：<0.2 / 0.2–0.5 / 0.5–1 / 1–2 / 2–3 / >3
    await waitFor(() => {
      expect(document.querySelectorAll('polygon').length).toBeGreaterThanOrEqual(6)
    })
    for (const level of ['S=0.2', 'S=0.5', 'S=1', 'S=2', 'S=3']) {
      expect(screen.getByText(level)).toBeInTheDocument()
    }
  })

  it('两张图都画出 77 K 与 300 K 参考线', async () => {
    renderShare()

    await waitFor(() => {
      expect(screen.getAllByText('液氮 77 K')).toHaveLength(2)
    })
    expect(screen.getAllByText('室温 300 K')).toHaveLength(2)
  })

  it('图内提示无数据点，而非隐藏整张图', async () => {
    renderShare()

    await waitFor(() => {
      expect(screen.getAllByText('当前 Tc 字段暂无可公开数据点')).toHaveLength(2)
    })
  })
})

describe('材料家族分类维度跟随目录', () => {
  it('图例列出全部内置家族、用户自建家族与「其他」', async () => {
    renderShare()

    await waitFor(() => {
      expect(screen.getAllByText('氢基超导体').length).toBeGreaterThan(0)
    })
    // 用户自建家族必须出现：硬编码的 7 类覆盖不到它
    expect(screen.getAllByText('单质超导体').length).toBeGreaterThan(0)
    // 未分类兜底档位
    expect(screen.getAllByText('其他').length).toBeGreaterThan(0)
  })

  it('组合下拉默认显示「全部」', async () => {
    renderShare()

    await waitFor(() => {
      expect(screen.getAllByText('全部')).toHaveLength(2)
    })
  })

  it('多选下拉可把多个家族组合显示在一张图里', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const user = userEvent.setup()
    await user.click(screen.getAllByRole('combobox', { name: '材料家族' })[0])

    const options = await screen.findByRole('listbox')
    // 默认全选
    within(options).getAllByRole('option').forEach(option => {
      expect(option).toHaveAttribute('aria-selected', 'true')
    })

    // 取消一个家族后不再是「全部」，其余家族仍组合在同一张图里
    await user.click(within(options).getByRole('option', { name: /氢基超导体/ }))
    await waitFor(() => {
      expect(screen.getAllByText('全部')).toHaveLength(1)
    })

    const stillSelected = within(options).getAllByRole('option')
      .filter(option => option.getAttribute('aria-selected') === 'true')
      .map(option => option.textContent)
    // 其余 7 个家族仍同时选中，即多个家族组合显示在一张图里
    expect(stillSelected).toHaveLength(MATERIAL_FAMILIES.length)
    expect(stillSelected.some(text => text?.includes('单质超导体'))).toBe(true)
    expect(stillSelected.some(text => text?.includes('氢基超导体'))).toBe(false)
  })
})

// ── B 组：布局对齐与视觉改版（Issue #72 B1–B6）──

// 两图错位的根因是控件显示文本长度影响布局高度：家族多选文本变长后撑高控件，
// 把下方图表整体下推。这里直接测「绘图区顶边」，而不是测某个 CSS 属性 ——
// 后者换个实现方式就失效，前者才是用户实际看到的错位。
const plotAreaTops = (): number[] =>
  Array.from(document.querySelectorAll('.recharts-cartesian-grid'))
    .map(grid => {
      const horizontal = grid.querySelector('.recharts-cartesian-grid-horizontal line')
      return Number(horizontal?.getAttribute('y') ?? NaN)
    })

// MUI 的 sx 走 emotion，宽度落在生成的 class 上而不是内联 style，
// 所以必须读 getComputedStyle 而不是 element.style。
const selectorWidths = (): string[] =>
  Array.from(document.querySelectorAll('[role="combobox"]'))
    .filter(node => node.getAttribute('aria-labelledby')?.includes('families'))
    .map(node => {
      const control = node.closest('.MuiFormControl-root') as HTMLElement | null
      return control ? getComputedStyle(control).width : ''
    })

const openFirstFamilySelect = async (user: ReturnType<typeof userEvent.setup>) => {
  await user.click(screen.getAllByRole('combobox', { name: '材料家族' })[0])
  return screen.findByRole('listbox')
}

describe('两图在任意家族选择状态下保持对齐（US4）', () => {
  it('取消部分家族后两图绘图区顶边仍等高', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const before = plotAreaTops()
    expect(before).toHaveLength(2)
    expect(before[0]).toBe(before[1])

    // 逐步取消，覆盖「文本变长 → 折叠摘要」的整个过程
    const user = userEvent.setup()
    const options = await openFirstFamilySelect(user)
    for (const name of [/氢基超导体/, /铜基超导体/, /铁基超导体/]) {
      await user.click(within(options).getByRole('option', { name }))
      const tops = plotAreaTops()
      expect(tops[0]).toBe(tops[1])
    }
    await user.keyboard('{Escape}')

    // 与初始状态相比也不应有纵向漂移
    expect(plotAreaTops()).toEqual(before)
  })

  it('两图纵轴上界统一为 500 K', async () => {
    renderShare()

    await waitFor(() => {
      expect(document.querySelectorAll('.recharts-yAxis').length).toBe(2)
    })
    const upperBounds = Array.from(document.querySelectorAll('.recharts-yAxis'))
      .map(axis => Array.from(axis.querySelectorAll('.recharts-cartesian-axis-tick-value'))
        .map(t => Number(t.textContent))
        .filter(Number.isFinite)
        .reduce((max, v) => Math.max(max, v), 0))

    expect(upperBounds).toEqual([500, 500])
  })
})

describe('材料家族选择框固定宽度（US5）', () => {
  it('宽度不随选中项数量变化，且两图一致', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const widths = selectorWidths()
    expect(widths).toHaveLength(2)
    expect(widths[0]).toBe(widths[1])
    expect(widths[0]).not.toBe('')

    const user = userEvent.setup()
    const options = await openFirstFamilySelect(user)
    await user.click(within(options).getByRole('option', { name: /氢基超导体/ }))
    await user.click(within(options).getByRole('option', { name: /铜基超导体/ }))
    await user.keyboard('{Escape}')

    // 选中数变了，宽度不能跟着变
    expect(selectorWidths()).toEqual(widths)
  })

  it('选中项文本过长时折叠为「已选 N 项」', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const user = userEvent.setup()
    const options = await openFirstFamilySelect(user)
    // 取消 2 项后剩 7 项，名称拼接远超控件宽度
    await user.click(within(options).getByRole('option', { name: /氢基超导体/ }))
    await user.click(within(options).getByRole('option', { name: /铜基超导体/ }))
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.getByText(/已选 7 项/)).toBeInTheDocument()
    })
  })

  it('全部取消后显示「未选择」', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const user = userEvent.setup()
    const options = await openFirstFamilySelect(user)
    // 逐个取消全部选项（含未分类的「其他」档位）。用 aria-selected 判定而非名称匹配，
    // 因为家族名之间存在子串关系（如「超导体」），正则匹配会命中多个。
    for (const option of within(options).getAllByRole('option')) {
      if (option.getAttribute('aria-selected') === 'true') {
        await user.click(option)
      }
    }
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.getByText('未选择')).toBeInTheDocument()
    })
  })
})

describe('社区页移除组合选择器（US6）', () => {
  it('页面不含「组合」下拉与编辑/复制/导出/新建按钮', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    expect(screen.queryByRole('combobox', { name: '组合' })).not.toBeInTheDocument()
    expect(screen.queryByText('(无组合)')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /新建/ })).not.toBeInTheDocument()
    for (const title of ['编辑', '复制', '导出']) {
      expect(screen.queryByRole('button', { name: title })).not.toBeInTheDocument()
    }
  })

  it('不再请求 /api/chart-groups', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const requested = mockedApi.get.mock.calls.map(call => String(call[0]))
    expect(requested.some(url => url.startsWith('/api/chart-groups'))).toBe(false)
  })
})

describe('背景填充与英文标签（US6）', () => {
  it('年份图用 linearGradient 渐变填充，并有温度图例', async () => {
    renderShare()

    await waitFor(() => {
      expect(document.querySelectorAll('#tc-temperature-gradient').length).toBe(1)
    })
    // 渐变必须真的被矩形引用，只声明 defs 不算画出来
    const filled = Array.from(document.querySelectorAll('rect'))
      .some(rect => rect.getAttribute('fill') === 'url(#tc-temperature-gradient)')
    expect(filled).toBe(true)

    expect(screen.getByTestId('temperature-legend-bar')).toBeInTheDocument()
    expect(screen.getByText(/背景为 Tc 高低/)).toBeInTheDocument()
  })

  it('压力图的品质因子图例说明暖色代表高 S', async () => {
    renderShare()

    await waitFor(() => {
      expect(screen.getByText(/品质因子 S（暖色 = 高）/)).toBeInTheDocument()
    })
  })

  it('Tc 字段选项与纵轴提示均为英文', async () => {
    renderShare()
    await waitFor(() => expect(screen.getAllByText('全部')).toHaveLength(2))

    const user = userEvent.setup()
    await user.click(screen.getAllByRole('combobox', { name: 'Tc 字段' })[0])
    const options = await screen.findByRole('listbox')

    const labels = within(options).getAllByRole('option').map(o => o.textContent ?? '')
    expect(labels).toEqual([
      'Experimental Tc',
      'Anisotropic Eliashberg Tc',
      'Isotropic Eliashberg Tc',
      'Allen-Dynes Tc',
      'McMillan Tc',
    ])
    // 不得残留中日韩字符
    for (const label of labels) {
      expect(label).not.toMatch(/[一-鿿]/)
    }

    await user.keyboard('{Escape}')
    expect(screen.getAllByText(/^Y axis: Experimental Tc$/)).toHaveLength(2)
  })
})

describe('已审核数据能上图', () => {
  it('Hg 数据点在两张图上各渲染一个散点', async () => {
    routeApi({ pressure: [HG_POINT], year: [HG_YEAR_POINT] })
    renderShare()

    await waitFor(() => {
      expect(document.querySelectorAll('.recharts-scatter-symbol').length).toBeGreaterThanOrEqual(2)
    })
    expect(screen.queryByText('当前 Tc 字段暂无可公开数据点')).not.toBeInTheDocument()
  })

  it('取消该点所属家族后散点消失，坐标系与背景仍在', async () => {
    routeApi({ pressure: [HG_POINT], year: [HG_YEAR_POINT] })
    renderShare()
    await waitFor(() => {
      expect(document.querySelectorAll('.recharts-scatter-symbol').length).toBeGreaterThanOrEqual(2)
    })

    const user = userEvent.setup()
    await user.click(screen.getAllByRole('combobox', { name: '材料家族' })[0])
    const options = await screen.findByRole('listbox')
    await user.click(within(options).getByRole('option', { name: /单质超导体/ }))
    await user.keyboard('{Escape}')

    await waitFor(() => {
      expect(screen.getAllByText('当前 Tc 字段暂无可公开数据点')).toHaveLength(1)
    })
    expect(document.querySelectorAll('.recharts-xAxis').length).toBe(2)
    expect(document.querySelectorAll('polygon').length).toBeGreaterThanOrEqual(6)
  })
})
