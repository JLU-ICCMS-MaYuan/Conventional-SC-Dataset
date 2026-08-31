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
  api: {
    get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), download: vi.fn(),
  },
}))

vi.mock('../../frontend/src/lib/classifications', async importOriginal => {
  const original = await importOriginal<typeof import('../../frontend/src/lib/classifications')>()
  const catalogs = {
    material_families: [
      { id: 1, name: '氢基超导体', aliases: ['hydride', '高压氢化物'] },
      { id: 7, name: '重费米子超导体', aliases: ['heavy fermion'] },
    ],
    structure_families: [{ id: 2, name: '笼状结构', aliases: ['clathrate'] }],
    material_dimensionalities: [
      { value: 'three_dimensional' as const, name: '三维' },
      { value: 'unknown' as const, name: '未知' },
    ],
  }
  return {
    ...original,
    loadClassificationCatalogs: vi.fn(async () => catalogs),
    refreshClassificationCatalogs: vi.fn(async () => catalogs),
  }
})

vi.mock('../../frontend/src/components/ChartGroupEditor', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/NewsManager', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/SuperAdminGovernance', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/UsernameField', () => ({ default: () => null }))

const mockedApi = vi.mocked(api)

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) {
      return {
        items: [{
          id: 51, doi: '10.1000/issue51', title: 'Hydride paper', authors: [], journal: 'Test',
          year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
          uploader_name: 'author', created_at: '2026-08-25', record_count: 1,
          show_in_chart: true, compound_symbols: 'LaH10', article_types: [],
        }],
        total: 1,
      } as never
    }
    if (path === '/api/admin/papers/51') {
      return {
        id: 51,
        material_states: [{
          id: 501,
          superconductor: { chemical_formula: 'LaH10' },
          material_family: null,
          material_family_id: null,
          element_count: 2,
          material_dimensionality: 'three_dimensional',
          structure_families: [],
        }],
      } as never
    }
    if (path === '/api/rag/papers/51/review-artifact') {
      return {
        data: {
          ai_values: {
            paper: { title: 'Hydride paper', classification_reason: '论文明确称为 hydride' },
            material_states: [{
              material: 'LaH10',
              material_family: { id: 1, name: '氢基超导体', status: 'confirmed' },
              structure_families: [],
              material_dimensionality: 'three_dimensional',
            }],
          },
          user_values: {
            paper: { title: 'Hydride paper' },
            material_states: [{
              material: 'LaH10',
              material_family: { id: 1, name: '氢基超导体', status: 'confirmed' },
              structure_families: [],
              material_dimensionality: 'three_dimensional',
            }],
          },
          evidence: {
            classification_scope: [
              { raw_name: 'LaH10', scope: 'current_paper' },
              { raw_name: 'H3S', scope: 'referenced_work' },
            ],
          },
        },
      } as never
    }
    if (path === '/api/rag/papers/51/candidate-attachments') return { data: [] } as never
    throw new Error(`unexpected GET ${path}`)
  })
  mockedApi.post.mockResolvedValue({ message: '审核完成' } as never)
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
})

describe('论文审核内材料分类确认', () => {
  it('移除独立治理入口，并以一次审核请求提交数据库选择和内部快照', async () => {
    const user = userEvent.setup()
    render(<AdminPage />)

    await user.click(screen.getByRole('button', { name: '论文审核' }))
    expect(await screen.findByText('Hydride paper')).toBeVisible()
    expect(screen.queryByRole('tab', { name: '分类建议' })).not.toBeInTheDocument()
    expect(screen.queryByRole('tab', { name: '分类目录' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: '审核' }))

    expect(await screen.findByText('确认材料状态分类')).toBeVisible()
    // Issue #62 起弹窗不再展示原文证据引文；classification_scope 仍随审核请求提交，
    // 由本用例末尾的 body 断言保护，因此这里不再断言引文的可见性。
    expect(screen.getByRole('combobox', { name: 'LaH10 的材料家族' })).toHaveValue('氢基超导体')

    fireEvent.mouseDown(screen.getByRole('combobox', { name: '审核结果' }))
    await user.click(await screen.findByRole('option', { name: '✅ 通过' }))
    await user.click(screen.getByRole('button', { name: '确认审核' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    const [path, body] = mockedApi.post.mock.calls[0]
    expect(path).toBe('/api/admin/papers/51/review')
    expect(body).toMatchObject({
      status: 'approved',
      material_states: [{
        id: 501,
        material_family: { id: 1, name: '氢基超导体' },
        material_dimensionality: 'three_dimensional',
      }],
      classification_context: {
        classification_scope: expect.arrayContaining([
          expect.objectContaining({ raw_name: 'H3S', scope: 'referenced_work' }),
        ]),
      },
    })
    expect(mockedApi.put).not.toHaveBeenCalled()
  })

  it('自由输入的新名称留在同一个审核请求中，不调用目录治理 API', async () => {
    const user = userEvent.setup()
    render(<AdminPage />)
    await user.click(screen.getByRole('button', { name: '论文审核' }))
    expect(await screen.findByText('Hydride paper')).toBeVisible()
    await user.click(screen.getByRole('button', { name: '审核' }))

    const familyInput = await screen.findByRole('combobox', { name: 'LaH10 的材料家族' })
    await user.clear(familyInput)
    await user.type(familyInput, '新型界面超导体')
    fireEvent.blur(familyInput)
    fireEvent.mouseDown(screen.getByRole('combobox', { name: '审核结果' }))
    await user.click(await screen.findByRole('option', { name: '✅ 通过' }))
    await user.click(screen.getByRole('button', { name: '确认审核' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    expect(mockedApi.post.mock.calls[0][1]).toMatchObject({
      material_states: [{ material_family: { id: null, name: '新型界面超导体' } }],
    })
    expect(String(mockedApi.post.mock.calls[0][0])).not.toContain('classification-catalogs')
  })
})
