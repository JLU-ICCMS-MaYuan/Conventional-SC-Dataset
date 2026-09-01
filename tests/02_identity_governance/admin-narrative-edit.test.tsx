/**
 * Feature #74：管理员编辑英文叙述字段（US5）
 * Spec: docs/specs/74-site-wide-i18n/spec.md（FR-018、FR-019、SC-006、SC-007）
 *
 * - 六个叙述字段（summary、keywords_tags、methodology、key_finding、
 *   research_motivation、knowledge_graph_title）在编辑弹窗中以单栏英文输入呈现。
 * - 修改任意字段保存后持久生效（PUT body 含新值）。
 * - knowledge_graph_title 不再被白名单静默丢弃。
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

const mockedApi = vi.mocked(api)

const paper = {
  id: 88, doi: '10.1000/narrative-edit', title: 'Narrative paper', authors: [], journal: 'Test',
  year: 2026, review_status: 'pending', review_comment: null, reviewer_name: null,
  uploader_name: 'author', created_at: '2026-08-31', record_count: 0,
  show_in_chart: true, compound_symbols: null, article_types: [],
  summary: 'English summary.', keywords_tags: ['hydride'],
  methodology: ['particle swarm optimization'], key_finding: 'Tc reaches 250 K.',
  research_motivation: 'Search for room-temperature superconductors.',
  knowledge_graph_title: 'Discovery of Superconductivity in Mercury',
}

beforeEach(() => {
  mockedApi.get.mockImplementation(async (path: string) => {
    if (path.startsWith('/api/admin/papers/all')) return { items: [paper], total: 1 }
    if (path === '/api/admin/papers/88') return { ...paper, key_properties: [], material_states: [] }
    if (path.startsWith('/api/chart-groups')) return []
    return {}
  })
  mockedApi.put.mockResolvedValue({ message: '已更新' })
  mockedApi.post.mockResolvedValue({ message: '已审核' })
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

describe('T043：六个叙述字段单栏编辑（FR-018）', () => {
  it('编辑弹窗以单栏输入呈现六个叙述字段', async () => {
    await openEditDialog()

    // 六个字段均为单个输入区（单栏），标签随界面语言
    expect(screen.getByRole('textbox', { name: 'LLM 摘要 (summary)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '关键词 (keywords_tags)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '研究方法 (methodology)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '核心发现 (key_finding)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '研究驱动力 (research_motivation)' })).toBeVisible()
    expect(screen.getByRole('textbox', { name: '知识图谱标题 (knowledge_graph_title)' })).toBeVisible()

    // 内容为英文数据，原样回填
    expect(screen.getByRole('textbox', { name: 'LLM 摘要 (summary)' })).toHaveValue('English summary.')
    expect(screen.getByRole('textbox', { name: '知识图谱标题 (knowledge_graph_title)' })).toHaveValue(
      'Discovery of Superconductivity in Mercury',
    )
  })

  it('修改叙述字段保存后 PUT body 携带新值（SC-006）', async () => {
    const user = await openEditDialog()

    const summary = screen.getByRole('textbox', { name: 'LLM 摘要 (summary)' })
    await user.clear(summary)
    await user.type(summary, 'Revised English summary.')
    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const [path, body] = mockedApi.put.mock.calls[0]
    expect(path).toBe('/api/admin/papers/88')
    expect(body).toMatchObject({ summary: 'Revised English summary.' })
  })

  it('knowledge_graph_title 编辑不再被静默丢弃（SC-007）', async () => {
    const user = await openEditDialog()

    const kgTitle = screen.getByRole('textbox', { name: '知识图谱标题 (knowledge_graph_title)' })
    await user.clear(kgTitle)
    await user.type(kgTitle, 'Room-Temperature Superconductivity Prospects')
    await user.click(screen.getByRole('button', { name: '保存修改' }))

    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    const [path, body] = mockedApi.put.mock.calls[0]
    expect(path).toBe('/api/admin/papers/88')
    expect(body).toMatchObject({ knowledge_graph_title: 'Room-Temperature Superconductivity Prospects' })
  })
})
