/**
 * Issue #76 阶段 7（T032）：管理员为论文补传结构附件（契约 C2）。
 *
 * - 结构上传回调走论文端点 POST /api/rag/papers/:id/structure-candidates（multipart），
 *   成功后候选出现在对应材料状态下的候选/预览区（不落库）。
 * - 删除（不采用）结构附件后保存，C1 请求 body 的 structure_candidates 不含该候选。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../../frontend/src/pages/AdminPage'
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
// 结构面板保留真实上传交互；3D 预览以占位替换，避免 jsdom 中 3dmol 动态加载
vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer-3d" />,
}))

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/structure-upload', title: 'Structure upload paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
}

const detailWithState = {
  ...paper,
  paper_type: 'experimental',
  key_properties: [],
  material_states: [{
    id: 11,
    superconductor: { id: 22, chemical_formula: 'Sn' },
    material_family: { id: 8, name: '单质超导体' },
    structure_families: [],
    element_count: 1,
    material_dimensionality: 'three_dimensional',
    superconductor_kind: 'conventional',
    crystal_system: 'unknown',
    state_kind: 'experimental',
    pressure_value_gpa: null,
    tc_results: [],
    properties: [],
    structures: [],
  }],
}

// C2 端点返回的候选：只含校验与表示，不含 material_state_ref/confirmation（由前端补充）
const candidateResponse = {
  ok: true,
  data: {
    candidate_id: 'cand_ab12cd34',
    material_state_index: 0,
    status: 'valid',
    structure_format: 'cif',
    validation: { ase_valid: true, atom_count: 4, elements: ['Sn'] },
    representations: {
      conventional: { cif: { text: 'data_Sn', available: true } },
      primitive: { cif: { text: 'data_Sn', available: true } },
    },
  },
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
    if (path === '/api/admin/papers/88') return detailWithState
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
  mockedApi.post.mockResolvedValue(candidateResponse)
  mockedApi.put.mockResolvedValue({ ok: true, data: { revision_bumped: false } })
})

afterEach(() => { cleanup(); vi.clearAllMocks() })

async function openEditDialog() {
  const user = userEvent.setup()
  render(<AdminPage />)
  await user.click(await screen.findByRole('button', { name: '论文审核' }))
  await user.click(await screen.findByRole('button', { name: '编辑' }))
  expect(await screen.findByText('编辑论文')).toBeVisible()
  return user
}

describe('T032：论文结构补传（契约 C2）', () => {
  it('上传结构附件调用论文结构端点（multipart），候选出现在材料状态下', async () => {
    await openEditDialog()

    // 触发结构上传（真实 StructureCandidatePanel 的文件输入）
    const file = new File(['data_Sn\n'], 'sn.cif', { type: 'text/plain' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input).not.toBeNull()
    fireEvent.change(input, { target: { files: [file] } })

    // C2：POST 论文结构端点，multipart 含材料状态下标与文件
    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    const [path, body] = mockedApi.post.mock.calls[0]
    expect(path).toBe('/api/rag/papers/88/structure-candidates')
    expect(body).toBeInstanceOf(FormData)
    const formData = body as FormData
    expect(formData.get('material_state_index')).toBe('0')
    expect((formData.get('file') as File).name).toBe('sn.cif')

    // 候选显示在对应材料状态下：文件名与原子数可见，3D 预览占位出现
    // （atomCount 与元素在同一 Typography 内拼接，用正则匹配）
    expect(await screen.findByText('sn.cif')).toBeVisible()
    expect(screen.getByText(/4 个原子/)).toBeVisible()
    expect(screen.getByTestId('structure-viewer-3d')).toBeInTheDocument()
  })

  it('删除（不采用）结构附件后保存，C1 body 不含该候选', async () => {
    const user = await openEditDialog()

    const file = new File(['data_Sn\n'], 'sn.cif', { type: 'text/plain' })
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    fireEvent.change(input, { target: { files: [file] } })
    await screen.findByText('sn.cif')

    // 不采用（排除）该候选
    await user.click(screen.getByRole('button', { name: '不采用' }))
    expect(await screen.findByText('已不采用')).toBeVisible()

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    // C4 顺序两步都调用；C1 body 只提交已确认候选，被删除的候选不在其中
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    const [path2, body2] = mockedApi.put.mock.calls[1]
    expect(path2).toBe('/api/rag/papers/88/scientific-draft')
    const candidates = body2.structure_candidates as Array<{ candidate_id: string }>
    expect(candidates.some(candidate => candidate.candidate_id === 'cand_ab12cd34')).toBe(false)
  })
})
