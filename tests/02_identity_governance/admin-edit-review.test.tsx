import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
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

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/edit-review', title: 'Editable paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
    if (path === '/api/admin/papers/88') return { ...paper, key_properties: [], material_states: [] }
    if (path.startsWith('/api/chart-groups')) return []
    return {}
  })
  mockedApi.post.mockResolvedValue({ message: '已审核' })
})

afterEach(() => { cleanup(); vi.clearAllMocks() })

/**
 * Issue #78：编辑弹窗迁移为独立页（/admin/papers/:id/edit）后，编辑页内审核
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

describe('编辑页内审核', () => {
  it('编辑弹窗顶部提供审核结果与审核意见控件', async () => {
    await openEditDialog()

    expect(screen.getByRole('combobox', { name: '审核结果' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '审核意见' })).toBeVisible()
    expect(screen.getByRole('button', { name: '提交审核' })).toBeVisible()
    // 仍保留全部字段编辑能力
    expect(screen.getByRole('textbox', { name: '标题' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: 'DOI' })).toBeVisible()
  })

  it('提交拒绝时按既有契约调用审核接口', async () => {
    const user = await openEditDialog()

    await user.type(screen.getByRole('textbox', { name: '审核意见' }), '缺少关键实验数据')
    await user.click(screen.getByRole('button', { name: '提交审核' }))

    await waitFor(() => expect(mockedApi.post).toHaveBeenCalledTimes(1))
    const [path, body] = mockedApi.post.mock.calls[0]
    expect(path).toBe('/api/admin/papers/88/review')
    expect(body).toMatchObject({ status: 'pending', comment: '缺少关键实验数据' })
    expect(body).toHaveProperty('review_request_id')
  })

  it('审核结果只提供拒绝与退回，不提供批准', async () => {
    const user = await openEditDialog()

    await user.click(screen.getByRole('combobox', { name: '审核结果' }))
    // 批准需逐个确认材料分类，编辑页没有该区域，放开只会得到必然 409 的按钮
    expect(await screen.findByRole('option', { name: '❌ 拒绝' })).toBeVisible()
    expect(screen.getByRole('option', { name: '退回待审核' })).toBeVisible()
    expect(screen.queryByRole('option', { name: /通过/ })).not.toBeInTheDocument()
  })
})

describe('T012：物性行化学式标签（#75-1 FR-002）', () => {
  const paperWithKp = {
    ...paper,
    key_properties: [{
      id: 1, material: 'LaH10', name: 'critical_temperature', name_raw: 'Tc',
      value_min: 250, value_max: null, unit: 'K', is_primary: true,
    }],
    material_states: [],
  }

  beforeEach(() => {
    mockedApi.get.mockImplementation(async (path: string) => {
      if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
      if (path === '/api/admin/papers/88') return paperWithKp
      if (path.startsWith('/api/chart-groups')) return []
      return {}
    })
  })

  it('物性行输入框标签为「化学式 (material)」', async () => {
    const user = userEvent.setup()
    renderAdminRoutes()
    await user.click(await screen.findByRole('button', { name: '论文审核' }))
    await user.click(await screen.findByRole('button', { name: '编辑' }))
    expect(await screen.findByLabelText('化学式 (material)')).toBeVisible()
    expect(screen.getByLabelText('化学式 (material)')).toHaveValue('LaH10')
  })

  it('英文界面标签为 Chemical formula (material)', async () => {
    localStorage.setItem('sc-wiki.language', 'en')
    const user = userEvent.setup()
    render(
      <LanguageProvider>
        <MemoryRouter initialEntries={['/admin']}>
          <Routes>
            <Route path="/admin" element={<AdminPage />} />
            <Route path="/admin/papers/:id/edit" element={<AdminPaperEditPage />} />
          </Routes>
        </MemoryRouter>
      </LanguageProvider>,
    )
    await user.click(await screen.findByRole('button', { name: 'Paper Review' }))
    await user.click(await screen.findByRole('button', { name: 'Edit' }))
    expect(await screen.findByLabelText('Chemical formula (material)')).toBeVisible()
  })
})
