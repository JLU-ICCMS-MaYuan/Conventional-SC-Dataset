import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import AdminPage from '../../frontend/src/pages/AdminPage'
import { api } from '../../frontend/src/lib/api'

// 角色由每个用例通过 currentUser 切换，用于验证 superOnly 卡片的可见性差异。
let currentUser: Record<string, unknown> = {
  id: 7, username: 'reviewer', role: 'admin', is_admin: true, is_superadmin: false,
}

vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({ user: currentUser, replaceUser: vi.fn() }),
}))

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), download: vi.fn() },
}))

vi.mock('../../frontend/src/components/ChartGroupEditor', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/NewsManager', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/SuperAdminGovernance', () => ({ default: () => null }))
vi.mock('../../frontend/src/components/UsernameField', () => ({ default: () => null }))

const mockedApi = vi.mocked(api)

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [], total: 12 }
    if (path.startsWith('/api/superadmin/users')) return [{ id: 1 }, { id: 2 }, { id: 3 }]
    if (path.startsWith('/api/superadmin/admin-applications')) return []
    if (path.startsWith('/api/chart-groups')) return []
    if (path.startsWith('/api/rag/llm/default-config')) return {
      data: { provider_name: 'OpenAI', base_url: 'https://bot.ccnccn.cn/v1', model: 'gpt-5.6-sol', api_key_configured: true, source: 'environment' },
    }
    return {}
  })
})

afterEach(() => {
  cleanup()
  vi.clearAllMocks()
  currentUser = { id: 7, username: 'reviewer', role: 'admin', is_admin: true, is_superadmin: false }
})

describe('工作台卡片式导航', () => {
  it('移除顶部 Tabs，普通管理员只看到论文审核与当前角色', async () => {
    render(<MemoryRouter><AdminPage /></MemoryRouter>)

    // FR-001：不再有 Tabs 导航
    expect(screen.queryAllByRole('tab')).toHaveLength(0)

    // FR-003 / SC-004：论文审核是可按按钮角色定位的入口
    expect(await screen.findByRole('button', { name: '论文审核' })).toBeVisible()
    expect(screen.getByText('当前角色')).toBeVisible()

    // 超管专属卡片不应出现
    expect(screen.queryByRole('button', { name: '用户与权限' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '待审批管理员' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '图表管理' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '快讯管理' })).not.toBeInTheDocument()
  })

  it('超级管理员看到全部 5 个可点击入口，且均具备按钮语义', async () => {
    currentUser = { id: 1, username: 'superadmin_mayuan', role: 'superadmin', is_admin: true, is_superadmin: true }
    render(<MemoryRouter><AdminPage mode="superadmin" /></MemoryRouter>)

    for (const label of ['用户与权限', '论文审核', '待审批管理员', '图表管理', '快讯管理']) {
      // SC-004：CardActionArea 提供 role=button；若退回成带 onClick 的 Card，这里会失败
      expect(await screen.findByRole('button', { name: label })).toBeVisible()
    }
    // 当前角色是身份展示，不做成可点击入口
    expect(screen.queryByRole('button', { name: '当前角色' })).not.toBeInTheDocument()
    expect(await screen.findByText('默认 AI 模型')).toBeVisible()
    expect(screen.getByDisplayValue('OpenAI')).toBeVisible()
  })

  it('默认模型配置只对超级管理员展示并经专用接口保存', async () => {
    currentUser = { id: 1, username: 'superadmin_mayuan', role: 'superadmin', is_admin: true, is_superadmin: true }
    const user = userEvent.setup()
    render(<MemoryRouter><AdminPage mode="superadmin" /></MemoryRouter>)

    const provider = await screen.findByDisplayValue('OpenAI')
    await user.clear(provider)
    await user.type(provider, 'OpenAI Gateway')
    await user.click(screen.getByRole('button', { name: '保存默认模型' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledWith('/api/rag/llm/default-config', expect.objectContaining({
      provider_name: 'OpenAI Gateway', model: 'gpt-5.6-sol',
    })))
  })

  it('点击论文审核卡片进入论文列表', async () => {
    const user = userEvent.setup()
    render(<MemoryRouter><AdminPage /></MemoryRouter>)

    await user.click(await screen.findByRole('button', { name: '论文审核' }))

    // 进入审核视图后出现列表工具栏
    expect(await screen.findByPlaceholderText('搜索标题/DOI/期刊…')).toBeVisible()
  })

  it('统计未加载完时显示占位符而非 0', async () => {
    // 让统计请求悬挂，模拟加载中
    mockedApi.get.mockImplementation(() => new Promise(() => {}))
    render(<MemoryRouter><AdminPage /></MemoryRouter>)

    // FR-007：加载中不得渲染 0，否则会被误读为真实值为零
    await waitFor(() => expect(screen.getByText('论文审核')).toBeVisible())
    expect(screen.queryByText('0')).not.toBeInTheDocument()
  })
})
