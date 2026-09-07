/**
 * Issue #76 阶段 6（T027）：待审核论文在编辑弹窗原地编辑科学数据，两段保存（契约 C4）。
 *
 * - 可编辑模式：修改材料状态字段（化学式）、Tc、物性。
 * - 保存按 C4 顺序调用：先 PUT /api/admin/papers/:id（论文级），再
 *   PUT /api/rag/papers/:id/scientific-draft（科学数据），
 *   且科学数据 body 的 material_states 含修改后的值（契约 C1 形态）。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../../frontend/src/pages/AdminPage'
import AdminPaperEditPage from '../../frontend/src/pages/AdminPaperEditPage'
import { api } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({
    user: { id: 7, username: 'reviewer', role: 'admin', is_admin: true, is_superadmin: false },
    replaceUser: vi.fn(),
  }),
}))

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), download: vi.fn() },
}))

vi.mock('../../frontend/src/components/ChartGroupEditor', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/NewsManager', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/SuperAdminGovernance', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/UsernameField', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/sci-edit', title: 'Scientific data paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
}

const detailWithStates = {
  ...paper,
  paper_type: 'experimental',
  material_families: [{ id: 8, name: '单质超导体', name_en: 'Elemental superconductor' }],
  key_properties: [],
  material_states: [{
    id: 11,
    superconductor: { id: 22, chemical_formula: 'Sn' },
    structure_families: [],
    element_count: 1,
    material_dimensionality: 'three_dimensional',
    superconductor_kind: 'conventional',
    crystal_system: 'tetragonal',
    state_kind: 'experimental',
    pressure_value_gpa: 0.001,
    property_modules: [{
      module_key: 'module-superconductive', module_code: 'superconductive_properties',
      definition_key: 'module.superconductive_properties', definition_version: 1, display_order: 0,
      records: [{
        record_key: 'record-tc', module_code: 'superconductive_properties', record_type: 'predicted_tc',
        property_code: 'tc', definition_key: 'record.superconductive_properties.predicted_tc.mcmillan',
        definition_version: 1, name_raw: 'critical temperature', value_kind: 'number',
        value_raw: '3.78', value_number: 3.78, unit_raw: 'K', method_code: 'mcmillan',
        is_representative: true,
        payload: { calculation_conditions: {}, parameters: { lambda_ep: 1.2, omega_log: 150, mu_star: 0.1 } },
      }, {
        record_key: 'record-current', module_code: 'superconductive_properties', record_type: 'property',
        property_code: 'custom', definition_key: 'record.superconductive_properties.custom',
        definition_version: 1, name_raw: 'threshold current', value_kind: 'number',
        value_raw: '0.28', value_number: 0.28, unit_raw: 'A', payload: {},
      }],
    }],
    structures: [],
  }],
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
    if (path === '/api/admin/papers/88') return detailWithStates
    if (path.startsWith('/api/chart-groups')) return []
    if (path === '/api/rag/space-groups') return { space_groups: [] }
    if (path === '/api/classification-catalogs') {
      return {
        material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
        structure_families: [{ id: 10, name: '笼状结构', aliases: ['clathrate'] }],
        material_dimensionalities: [{ value: 'three_dimensional', name: '三维' }, { value: 'unknown', name: '未知' }],
      }
    }
    return {}
  })
  mockedApi.put.mockResolvedValue({ ok: true, data: { revision_bumped: false } })
  mockedApi.post.mockResolvedValue({ message: '已审核' })
})

afterEach(() => { cleanup(); vi.clearAllMocks() })

/**
 * Issue #78：编辑弹窗迁移为独立页（/admin/papers/:id/edit）后，科学数据编辑
 * 通过「列表「编辑」→ 独立页面」的页面语义驱动；两段保存断言与契约保持不变。
 */
function renderAdminRoutes() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Routes>
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/admin/papers/:id/edit" element={<AdminPaperEditPage />} />
      </Routes>
    </MemoryRouter>,
  )
}

async function openEditDialog() {
  const user = userEvent.setup()
  renderAdminRoutes()
  await user.click(await screen.findByRole('button', { name: '论文审核' }))
  await user.click(await screen.findByRole('button', { name: '编辑' }))
  expect(await screen.findByText('编辑论文')).toBeVisible()
  return user
}

describe('T027：待审核论文科学数据原地编辑', () => {
  it('编辑弹窗内可修改材料状态字段/Tc/物性', async () => {
    await openEditDialog()

    // 可编辑模式：输入框可修改（readOnly 下不会出现可编辑输入）
    const formula = screen.getByLabelText('化学式')
    expect(formula).toHaveValue('Sn')
    expect(within(screen.getByTestId('property-record-record-tc')).getByLabelText('数值')).toHaveValue(3.78)
    expect(screen.getByDisplayValue('threshold current')).toBeVisible()
  })

  it('保存按 C4 顺序调用论文级与科学数据接口，科学数据 body 含修改后的值', async () => {
    const user = await openEditDialog()

    // 修改化学式 / Tc / 物性原始值
    const formula = screen.getByLabelText('化学式')
    await user.clear(formula)
    await user.type(formula, 'H3S')
    const tcValue = within(screen.getByTestId('property-record-record-tc')).getByLabelText('数值')
    await user.clear(tcValue)
    await user.type(tcValue, '250')
    const rawValue = within(screen.getByTestId('property-record-record-current')).getByLabelText('原始值')
    await user.clear(rawValue)
    await user.type(rawValue, '0.35')

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    // C4 顺序：论文级（Go）先，科学数据（Python）后
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    const [path1] = mockedApi.put.mock.calls[0]
    expect(path1).toBe('/api/admin/papers/88')
    const [path2, body2] = mockedApi.put.mock.calls[1]
    expect(path2).toBe('/api/rag/papers/88/scientific-draft')

    // C1 请求体形态：paper_type + material_states（含修改后的值）+ structure_candidates
    expect(body2).toMatchObject({ paper_type: 'experimental' })
    expect(body2).toHaveProperty('structure_candidates')
    expect(Array.isArray(body2.material_states)).toBe(true)
    expect(body2.material_states[0]).toMatchObject({ material: 'H3S' })
    expect(body2.material_states[0].property_modules[0].records[0]).toMatchObject({ value_number: 250 })
    expect(body2.material_states[0].property_modules[0].records[1]).toMatchObject({ value_raw: '0.35' })
  })

  it('论文级保存失败时终止，不调用科学数据接口', async () => {
    mockedApi.put.mockRejectedValueOnce(new Error('论文级字段校验失败'))
    const user = await openEditDialog()

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    expect(mockedApi.put.mock.calls[0][0]).toBe('/api/admin/papers/88')
    // 弹窗不关闭，提示失败
    expect(await screen.findByText(/论文级字段校验失败/)).toBeVisible()
  })

  it('切换为实验测量后，科学数据保存请求不携带计算上下文', async () => {
    const user = await openEditDialog()

    expect(screen.getByLabelText('电声耦合强度 λ')).toHaveValue(1.2)
    const tcRecord = screen.getByTestId('property-record-record-tc')
    await user.click(within(tcRecord.parentElement as HTMLElement).getByRole('combobox', { name: '记录定义' }))
    await user.click(await screen.findByRole('option', { name: /测量 Tc · resistivity/ }))
    expect(screen.queryByLabelText('电声耦合强度 λ')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('对数声子频率 ωlog (K)')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('库仑屏蔽常数 μ*')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    const [, scientificPayload] = mockedApi.put.mock.calls[1]
    const result = scientificPayload.material_states[0].property_modules[0].records[0]
    expect(result).toMatchObject({ method_code: 'resistivity', record_type: 'measured_tc' })
    expect(result.payload).toEqual({ experimental_conditions: {} })
  }, 30000)
})

describe('T013：管理端编辑弹窗结构候选集成（Issue #77）', () => {
  it('编辑弹窗渲染未分配候选区（共用 MaterialStatesEditor），无候选时不误渲染', async () => {
    const user = await openEditDialog()

    // 管理端编辑的是已提交论文：草稿级 unassigned 候选已随提交清理，
    // 正常不携带未分配候选——未分配区不应误渲染
    expect(document.querySelector('[data-testid="unassigned-candidates"]')).toBeNull()

    // 保存链路仍正常（C1 body 含 structure_candidates 键，契约不破坏）
    await user.click(screen.getByRole('button', { name: '保存修改' }))
    await waitFor(() => expect(mockedApi.put.mock.calls.filter(c => c[0] === '/api/rag/papers/88/scientific-draft')).toHaveLength(1))
  })
})
