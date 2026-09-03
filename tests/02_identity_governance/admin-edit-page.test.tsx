/**
 * Issue #78：管理端论文编辑独立页（路由 /admin/papers/:id/edit）。
 *
 * - 渲染：论文级字段（含 knowledge_graph_title 输入框）、材料状态区、审核区可见。
 * - 结构表示（FR-004/FR-005/FR-007）：详情加载后对已落库结构调用表示端点，
 *   候选获得完整 representations，晶胞/格式切换后预览有内容；端点失败时
 *   降级为落库惯用胞 CIF，编辑与保存不受影响。
 * - 两段保存（FR-008/FR-009）：先 PUT /api/admin/papers/:id 后
 *   PUT /api/rag/papers/:id/scientific-draft；approved 论文显示升版警告，
 *   保存成功且 revision_bumped=true 时提示退回待审核。
 * - 非管理员路由保护由 RoleRoute 测试覆盖，本文件不重复。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPaperEditPage from '../../frontend/src/pages/AdminPaperEditPage'
import { api } from '../../frontend/src/lib/api'

let currentUser = {
  id: 7,
  username: 'reviewer',
  role: 'admin' as const,
  is_admin: true,
  is_superadmin: false,
}

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({ user: currentUser, replaceUser: vi.fn() }),
}))

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), download: vi.fn() },
}))
// 结构 3D 预览以占位替换（jsdom 无法加载 3dmol），并把表示文本暴露到 DOM 便于断言
vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: ({ data, format }: { data: string; format: string }) => (
    <div data-testid="structure-viewer-3d" data-content={data} data-format={format} />
  ),
}))

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/edit-page', title: 'Edit page paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
  knowledge_graph_title: 'Discovery of Superconductivity in Mercury',
}

// Go 详情行形态：material_states 含已落库结构（structures）
const detailWithStructures = {
  ...paper,
  paper_type: 'experimental',
  superconductor_kind: 'conventional',
  material_families: [{ id: 8, name: '单质超导体', name_en: 'Elemental superconductor' }],
  key_properties: [],
  material_states: [{
    id: 11,
    superconductor: { id: 22, chemical_formula: 'Sn' },
    structure_families: [],
    element_count: 1,
    material_dimensionality: 'three_dimensional',
    crystal_system: 'tetragonal',
    state_kind: 'experimental',
    pressure_value_gpa: 0.001,
    tc_results: [{
      id: 31, result_kind: 'experimental', tc_method: 'experimental',
      tc_value_k: 3.78, value_raw: '3.78', unit_raw: 'K', is_representative: true,
    }],
    properties: [],
    structures: [{
      id: 1, structure_format: 'cif', structure_text: 'data_Sn',
      atom_count: 4, source_locator: 'sn.cif',
    }],
  }],
}

// 表示端点（GET /api/rag/papers/88/structures/1/representations）返回完整表示
const representationsResponse = {
  ok: true,
  data: {
    structure_id: 1,
    structure_format: 'cif',
    representations: {
      conventional: {
        cif: { text: 'data_conventional_cif', available: true },
        poscar: { text: 'data_conventional_poscar', available: true },
      },
      primitive: {
        cif: { text: 'data_primitive_cif', available: true },
        poscar: { text: 'data_primitive_poscar', available: true },
      },
    },
    validation: { structure_format: 'cif', atom_count: 4 },
  },
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path === '/api/admin/papers/88') return detailWithStructures
    if (path === '/api/rag/papers/88/structures/1/representations') return representationsResponse
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

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  currentUser = { id: 7, username: 'reviewer', role: 'admin', is_admin: true, is_superadmin: false }
})

const renderPage = () => render(
  <MemoryRouter initialEntries={['/admin/papers/88/edit']}>
    <Routes>
      <Route path="/admin/papers/:id/edit" element={<AdminPaperEditPage />} />
      <Route path="/admin" element={<div>管理员工作台</div>} />
      <Route path="/superadmin" element={<div>超级管理员工作台</div>} />
    </Routes>
  </MemoryRouter>,
)

describe('Issue #78：管理端论文编辑独立页', () => {
  it('渲染论文级字段（含 knowledge_graph_title）、材料状态区与审核区', async () => {
    const user = userEvent.setup()
    renderPage()

    // 页面标题与返回按钮
    expect(await screen.findByText('编辑论文')).toBeVisible()
    expect(screen.getByRole('button', { name: '返回列表' })).toBeVisible()

    // 论文级字段：knowledge_graph_title 输入框随页面迁移保留（admin-narrative-edit 依赖）
    expect(await screen.findByRole('textbox', { name: '知识图谱标题 (knowledge_graph_title)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '知识图谱标题 (knowledge_graph_title)' }))
      .toHaveValue('Discovery of Superconductivity in Mercury')
    expect(screen.getByRole('textbox', { name: '标题' })).toBeVisible()
    expect(screen.getByRole('combobox', { name: '超导类型' })).toHaveTextContent('常规超导体（BCS超导体）')

    // 材料状态区（详情 material_states 渲染为 MaterialStatesEditor 卡片）
    expect(await screen.findByText('材料状态 #1')).toBeVisible()
    expect(screen.getByLabelText('化学式')).toHaveValue('Sn')

    // 审核区：通过/拒绝/退回 + 审核意见 + 提交审核
    expect(screen.getByRole('combobox', { name: '审核结果' })).toBeVisible()
    await user.click(screen.getByRole('combobox', { name: '审核结果' }))
    expect(await screen.findByRole('option', { name: '✅ 通过' })).toBeVisible()
    expect(screen.getByRole('option', { name: /退回待审核/ })).toBeVisible()
    await user.click(screen.getByRole('option', { name: /退回待审核/ }))
    expect(screen.getByRole('textbox', { name: '审核意见' })).toBeVisible()
    expect(screen.getByRole('button', { name: '提交审核' })).toBeVisible()
  })

  it('显示上传者与关联记录数，并为缺失上传者提供稳定占位', async () => {
    renderPage()

    expect(await screen.findByText('上传者: author')).toBeVisible()
    expect(screen.getByText('物性记录: 0')).toBeVisible()

    cleanup()
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path === '/api/admin/papers/88') return { ...detailWithStructures, uploader_name: null, record_count: 2 }
      if (path === '/api/rag/papers/88/structures/1/representations') return representationsResponse
      if (path === '/api/rag/space-groups') return { space_groups: [] }
      if (path === '/api/classification-catalogs') return { material_families: [], structure_families: [], material_dimensionalities: [] }
      return {}
    })
    renderPage()

    expect(await screen.findByText('上传者: -')).toBeVisible()
    expect(screen.getByText('物性记录: 2')).toBeVisible()
  })

  it('按需打开处理记录并显示未知上传者与每次审核意见，失败时可重试', async () => {
    const user = userEvent.setup()
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path === '/api/admin/papers/88') return detailWithStructures
      if (path === '/api/admin/papers/88/history') {
        return {
          paper_id: 88,
          events: [
            {
              id: 1, event_type: 'uploaded', paper_revision: 1,
              actor: { username: null, unknown: true }, occurred_at: '2026-09-03T09:00:00Z', review: null,
            },
            {
              id: 2, event_type: 'reviewed', paper_revision: 1,
              actor: { username: 'reviewer', unknown: false }, occurred_at: '2026-09-03T10:00:00Z',
              review: { status: 'approved', comment: '证据充分' },
            },
          ],
        }
      }
      if (path === '/api/rag/papers/88/structures/1/representations') return representationsResponse
      if (path === '/api/rag/space-groups') return { space_groups: [] }
      if (path === '/api/classification-catalogs') return { material_families: [], structure_families: [], material_dimensionalities: [] }
      return {}
    })
    renderPage()

    await user.click(await screen.findByRole('button', { name: '处理记录' }))
    await waitFor(() => expect(mockedApi.get).toHaveBeenCalledWith('/api/admin/papers/88/history'))
    const historyDialog = await screen.findByRole('dialog')
    await waitFor(() => expect(historyDialog).toHaveTextContent('历史导入，上传者未知'))
    expect(historyDialog).toHaveTextContent('审核')
    expect(historyDialog).toHaveTextContent('已通过 · 证据充分')

    await user.click(screen.getByRole('button', { name: '关闭' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    mockedApi.get.mockRejectedValueOnce(new Error('网络错误'))
    await user.click(screen.getByRole('button', { name: '处理记录' }))
    expect(await screen.findByText('处理记录加载失败: 网络错误')).toBeVisible()
    expect(screen.getByRole('button', { name: '重试' })).toBeVisible()
  })

  it('审核成功后按当前角色返回工作台，失败时留在编辑页', async () => {
    const user = userEvent.setup()
    currentUser = { ...currentUser, role: 'superadmin', is_superadmin: true }
    renderPage()

    await user.click(await screen.findByRole('button', { name: '提交审核' }))
    expect(await screen.findByText('超级管理员工作台')).toBeVisible()

    cleanup()
    currentUser = { ...currentUser, role: 'admin', is_superadmin: false }
    renderPage()

    await user.click(await screen.findByRole('button', { name: '提交审核' }))
    expect(await screen.findByText('管理员工作台')).toBeVisible()

    cleanup()
    mockedApi.post.mockRejectedValueOnce(new Error('网络错误'))
    renderPage()

    await user.click(await screen.findByRole('button', { name: '提交审核' }))
    expect(await screen.findByText('审核失败: 网络错误')).toBeVisible()
    expect(screen.queryByText('管理员工作台')).not.toBeInTheDocument()
  })

  it('已落库结构获得完整表示：切换晶胞/格式后预览有内容（FR-005）', async () => {
    const user = userEvent.setup()
    renderPage()

    // 表示端点被调用，候选并入完整 representations（内容区别于落库 CIF）
    await waitFor(() => expect(mockedApi.get).toHaveBeenCalledWith('/api/rag/papers/88/structures/1/representations'))
    const viewer = await screen.findByTestId('structure-viewer-3d')
    await waitFor(() => expect(viewer.getAttribute('data-content')).toBe('data_conventional_cif'))

    // 切换格式 → POSCAR
    await user.click(screen.getByRole('combobox', { name: '结构格式' }))
    await user.click(await screen.findByRole('option', { name: 'POSCAR' }))
    expect(screen.getByTestId('structure-viewer-3d').getAttribute('data-content')).toBe('data_conventional_poscar')

    // 切换晶胞 → 原胞
    await user.click(screen.getByRole('combobox', { name: '晶胞表示' }))
    await user.click(await screen.findByRole('option', { name: '原胞' }))
    expect(screen.getByTestId('structure-viewer-3d').getAttribute('data-content')).toBe('data_primitive_poscar')
    expect(screen.getByText('当前显示：原胞 · POSCAR')).toBeVisible()

    // 下载按钮在完整表示下可用（FR-006）
    expect(screen.getByRole('button', { name: '下载结构' })).toBeEnabled()
  })

  it('表示端点失败时降级为落库 CIF，页面仍可编辑保存（FR-007）', async () => {
    const user = userEvent.setup()
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path === '/api/rag/papers/88/structures/1/representations') throw new Error('representation service down')
      if (path === '/api/admin/papers/88') return detailWithStructures
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

    renderPage()

    // 降级提示出现，结构区仍显示落库惯用胞 CIF
    expect(await screen.findByText(/已降级为仅显示落库的 CIF/)).toBeVisible()
    const viewer = await screen.findByTestId('structure-viewer-3d')
    expect(viewer.getAttribute('data-content')).toBe('data_Sn')

    // 编辑保存链路不受影响（两段保存均执行）
    await user.click(screen.getByRole('button', { name: '保存修改' }))
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    expect(mockedApi.put.mock.calls[0][0]).toBe('/api/admin/papers/88')
    expect(mockedApi.put.mock.calls[1][0]).toBe('/api/rag/papers/88/scientific-draft')
    expect(mockedApi.put.mock.calls[0][1]).toHaveProperty('history_operation_id')
    expect(mockedApi.put.mock.calls[1][1]).toHaveProperty('history_operation_id', mockedApi.put.mock.calls[0][1].history_operation_id)
  })

  it('两段保存：先论文级后科学数据，科学数据 body 含修改后的值（FR-008）', async () => {
    const user = userEvent.setup()
    renderPage()

    const formula = await screen.findByLabelText('化学式')
    await user.clear(formula)
    await user.type(formula, 'H3S')

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    const [path1] = mockedApi.put.mock.calls[0]
    expect(path1).toBe('/api/admin/papers/88')
    const [path2, body2] = mockedApi.put.mock.calls[1]
    expect(path2).toBe('/api/rag/papers/88/scientific-draft')
    expect(body2).toMatchObject({ paper_type: 'experimental' })
    expect(body2.material_states[0]).toMatchObject({ material: 'H3S' })
    expect(body2).toMatchObject({ superconductor_kind: 'conventional' })
    expect(body2.material_states[0]).not.toHaveProperty('superconductor_kind')
  })

  it('审核通过时提交当前编辑器中的材料分类（无需先单独保存）', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('材料状态 #1')
    await user.click(screen.getByRole('combobox', { name: '审核结果' }))
    await user.click(await screen.findByRole('option', { name: '✅ 通过' }))
    await user.click(screen.getByRole('button', { name: '提交审核' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    expect(mockedApi.post.mock.calls[0][1]).toMatchObject({
      status: 'approved',
      superconductor_kind: 'conventional',
      material_families: [{ id: 8, name: '单质超导体' }],
      material_states: [{
        id: 11,
        material_dimensionality: 'three_dimensional',
      }],
    })
  })

  it('待审正式关联为空时从审核产物回填论文 family 与 More type labels', async () => {
    const user = userEvent.setup()
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path === '/api/admin/papers/88') {
        return {
          ...detailWithStructures,
          material_families: [],
          material_states: [{
            ...detailWithStructures.material_states[0],
            structure_families: [],
            structures: [],
          }],
        }
      }
      if (path === '/api/rag/papers/88/review-artifact') {
        return { data: { user_values: {
          paper: { material_families: [
            { id: null, name: '待建家族', status: 'pending' },
            { id: 1, name: '氢基超导体', status: 'confirmed' },
          ] },
          material_states: [{
            material_dimensionality: 'three_dimensional',
            structure_families: [{ id: 10, name: '笼状结构', status: 'confirmed', is_primary: false }],
          }],
        } } }
      }
      if (path === '/api/rag/space-groups') return { space_groups: [] }
      if (path === '/api/classification-catalogs') {
        return {
          material_families: [{ id: 1, name: '氢基超导体', aliases: ['hydride'] }],
          structure_families: [{ id: 10, name: '笼状结构', aliases: ['clathrate'] }],
          material_dimensionalities: [{ value: 'three_dimensional', name: '三维' }],
        }
      }
      return {}
    })

    renderPage()
    expect(await screen.findByText('待建家族')).toBeVisible()
    expect(screen.getByText('笼状结构')).toBeVisible()

    await user.click(screen.getByRole('combobox', { name: '审核结果' }))
    await user.click(await screen.findByRole('option', { name: '✅ 通过' }))
    await user.click(screen.getByRole('button', { name: '提交审核' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    expect(mockedApi.post.mock.calls[0][1]).toMatchObject({
      material_families: [
        { id: null, name: '待建家族' },
        { id: 1, name: '氢基超导体' },
      ],
      material_states: [{
        id: 11,
        structure_families: [{ id: 10, name: '笼状结构', is_primary: false }],
      }],
    })
  })

  it('approved 论文显示升版警告，保存成功且 revision_bumped 时提示退回待审核（FR-009）', async () => {
    const user = userEvent.setup()
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path === '/api/admin/papers/88') return { ...detailWithStructures, review_status: 'approved' }
      if (path === '/api/rag/papers/88/structures/1/representations') return representationsResponse
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
    // C1（科学数据段）返回 revision_bumped: true
    mockedApi.put.mockImplementation(async (path: string) => {
      if (path.includes('/scientific-draft')) {
        return { ok: true, data: { revision_bumped: true } }
      }
      return { message: '已更新' }
    })

    renderPage()

    // 升版警告（T044）
    expect(await screen.findByText(/该论文已通过审核/)).toBeVisible()
    expect(screen.getByText(/递增版本号并退回待审核/)).toBeVisible()

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    expect(mockedApi.put.mock.calls[1][0]).toBe('/api/rag/papers/88/scientific-draft')
    // 退回待审核提示（T045）
    expect(await screen.findByText(/已保存并退回待审核/)).toBeVisible()
  })
})
