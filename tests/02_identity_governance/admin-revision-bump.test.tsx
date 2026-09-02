/**
 * Issue #76 阶段 8（T044/T045）：编辑已通过论文时的升版重审。
 *
 * - 打开编辑弹窗时若论文 review_status === 'approved'，显示升版警告
 *   （保存科学数据将递增版本号并退回待审核、期间不对外公开）。
 * - 保存成功且 C1 响应 revision_bumped === true 时，提示论文已退回待审核。
 */

import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
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
vi.mock('../../frontend/src/components/StructureCandidatePanel', () => ({
  default: () => <div data-testid="structure-candidate-panel" />,
}))

const mockedApi = vi.mocked(api)

const approvedPaper = {
  id: 88, doi: '10.1000/revision-bump', title: 'Approved paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'approved', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
}

const detailWithState = {
  ...approvedPaper,
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
    tc_results: [{
      id: 31, result_kind: 'experimental', tc_method: 'experimental',
      tc_value_k: 3.78, value_raw: '3.78', unit_raw: 'K', is_representative: true,
    }],
    properties: [],
    structures: [],
  }],
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [approvedPaper], total: 1 }
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
  // C1（科学数据段）返回 revision_bumped: true，论文级保存返回普通成功
  mockedApi.put.mockImplementation(async (path: string) => {
    if (path.includes('/scientific-draft')) {
      return { ok: true, data: { paper_id: 88, content_revision: 2, review_status: 'pending', revision_bumped: true, material_state_count: 1 } }
    }
    return { message: '已更新' }
  })
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

describe('T044/T045：已通过论文的升版重审', () => {
  it('打开已通过论文的编辑弹窗时显示升版警告', async () => {
    await openEditDialog()

    expect(screen.getByText(/该论文已通过审核/)).toBeVisible()
    expect(screen.getByText(/递增版本号并退回待审核/)).toBeVisible()
  })

  it('保存成功且 revision_bumped 为 true 时提示已退回待审核', async () => {
    const user = await openEditDialog()

    await user.click(screen.getByRole('button', { name: '保存修改' }))

    // 两步保存都执行（论文级 + 科学数据）
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    expect(mockedApi.put.mock.calls[1][0]).toBe('/api/rag/papers/88/scientific-draft')
    // 退回待审核提示（T045）
    expect(await screen.findByText(/已保存并退回待审核/)).toBeVisible()
  })
})
