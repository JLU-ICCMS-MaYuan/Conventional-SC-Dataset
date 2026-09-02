/**
 * Issue #76 阶段 5（T018/T019）：管理员在编辑弹窗查看完整超导性质。
 *
 * - detail（GET /api/admin/papers/:id）携带 material_states（含 tc_results/properties/structures），
 *   打开编辑弹窗后共享组件 MaterialStatesEditor 渲染材料状态卡片，Tc/物性/结构区可见。
 * - 无材料状态时显示空态且不报错。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../../frontend/src/pages/AdminPage'
import AdminPaperEditPage from '../../frontend/src/pages/AdminPaperEditPage'
import { LanguageProvider } from '../../frontend/src/context/LanguageContext'
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
// 结构候选面板以占位替换：只验证「结构区可见」，避免 jsdom 中 3dmol 动态加载
vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel">structure-candidate-panel</div>,
}))

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/sci-view', title: 'Scientific data paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
}

// Go 详情行形态（GET /api/admin/papers/:id 直接序列化模型）：
// 化学式在 superconductor.chemical_formula，结构家族是链接行，Tc/物性/结构已预加载。
const detailWithStates = {
  ...paper,
  paper_type: 'experimental',
  key_properties: [],
  material_states: [{
    id: 11,
    superconductor: { id: 22, chemical_formula: 'Sn' },
    material_family: { id: 8, name: '单质超导体', name_en: 'Elemental superconductor' },
    structure_families: [{ id: 10, is_primary: false, structure_family: { id: 10, name: '笼状结构' } }],
    element_count: 1,
    material_dimensionality: 'three_dimensional',
    superconductor_kind: 'conventional',
    crystal_system: 'tetragonal',
    state_kind: 'experimental',
    pressure_value_gpa: 0.001,
    reported_space_group_symbol: null,
    reported_space_group_number: null,
    tc_results: [{
      id: 31, result_kind: 'experimental', tc_method: 'experimental',
      tc_value_k: 3.78, value_raw: '3.78', unit_raw: 'K', is_representative: true,
    }],
    properties: [{ id: 41, material: 'Sn', name_raw: 'threshold current', value_raw: '0.28', unit: 'A' }],
    structures: [{ id: 51, structure_format: 'cif', structure_text: 'data_Sn', source_locator: 'supp.pdf' }],
  }],
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
    if (path === '/api/admin/papers/88') return detailWithStates
    if (path.startsWith('/api/chart-groups')) return []
    if (path === '/api/rag/space-groups') return { space_groups: [] }
    // 分类目录：MaterialStatesEditor 的分类下拉与结构家族 Autocomplete 需要
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
})

afterEach(() => { cleanup(); vi.clearAllMocks() })

/**
 * Issue #78：编辑弹窗迁移为独立页（/admin/papers/:id/edit）后，科学数据查看
 * 通过「列表「编辑」→ 独立页面」的页面语义驱动；断言与契约保持不变。
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

describe('T018：管理员查看完整超导性质', () => {
  it('编辑弹窗渲染材料状态卡片，Tc/物性/结构区可见且回填数据', async () => {
    await openEditDialog()

    // 材料状态卡片：标题与化学式（Go 的 superconductor.chemical_formula 被转换回填）
    expect(screen.getByText('材料状态 #1')).toBeVisible()
    expect(screen.getByLabelText('化学式')).toHaveValue('Sn')

    // Tc 区：标题与数值回填（conventional 类型渲染完整字段组；type=number 值为数字）
    expect(screen.getByText('临界温度 Tc')).toBeVisible()
    expect(screen.getByLabelText('Tc 数值 (K)')).toHaveValue(3.78)

    // 物性区：标题与原始值回填
    expect(screen.getByText('其他普通物性')).toBeVisible()
    expect(screen.getByDisplayValue('threshold current')).toBeVisible()
    expect(screen.getByDisplayValue('0.28')).toBeVisible()

    // 结构区可见（既有结构模型已并入候选面板）
    expect(screen.getByTestId('structure-candidate-panel')).toBeInTheDocument()
  })

  it('无材料状态时显示空态且不报错', async () => {
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
      if (path === '/api/admin/papers/88') return { ...paper, key_properties: [], material_states: [] }
      if (path.startsWith('/api/chart-groups')) return []
      if (path === '/api/classification-catalogs') {
        return {
          material_families: [], structure_families: [],
          material_dimensionalities: [{ value: 'three_dimensional', name: '三维' }, { value: 'unknown', name: '未知' }],
        }
      }
      return {}
    })

    await openEditDialog()

    expect(screen.getByText(/AI 没有提取到材料状态/)).toBeVisible()
    // 页面仍完整可用：论文级字段与保存按钮保留
    expect(screen.getByRole('textbox', { name: '标题' })).toBeVisible()
    expect(screen.getByRole('button', { name: '保存修改' })).toBeVisible()
  })
})
