import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import AdminPaperEditPage from '../../frontend/src/pages/AdminPaperEditPage'
import { api } from '../../frontend/src/lib/api'

const auth = vi.hoisted(() => ({ role: 'admin' }))
vi.mock('../../frontend/src/context/AuthContext', () => ({
  useAuth: () => ({ user: { id: 7, role: auth.role } }),
}))
vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn(), put: vi.fn(), post: vi.fn() },
}))

const mockedApi = vi.mocked(api)
let stored: Record<string, unknown>
const author = () => screen.getByRole('combobox', { name: '作者' })
const keywords = () => screen.getByRole('textbox', { name: '关键词 (keywords_tags)' })
const methods = () => screen.getByRole('textbox', { name: '研究方法 (methodology)' })
const save = () => screen.getByRole('button', { name: '保存修改' })

function renderPage() {
  return render(<MemoryRouter initialEntries={['/admin/papers/88/edit']}>
    <Routes><Route path="/admin/papers/:id/edit" element={<AdminPaperEditPage />} /></Routes>
  </MemoryRouter>)
}

beforeEach(() => {
  auth.role = 'admin'
  stored = {
    id: 88, title: 'Mercury', year: 1911, review_status: 'approved',
    authors: '["H. Kamerlingh Onnes","Doe, Jane"]',
    keywords_tags: '["superconductivity","[FeSe]"]',
    methodology: '["Resistance, cooling","Compare \\"zero\\" resistance"]',
    material_states: [], key_properties: [],
  }
  mockedApi.get.mockImplementation(async path => {
    if (path === '/api/admin/papers/88') return { ...stored }
    if (path === '/api/classification-catalogs') return { material_families: [] }
    return {}
  })
  mockedApi.put.mockImplementation(async (_path, body) => {
    stored = { ...stored, ...body }
    return { message: '已更新' }
  })
})
afterEach(() => { cleanup(); vi.clearAllMocks() })

describe('Issue #95：管理端论文列表字段', () => {
  it.each(['admin', 'superadmin'])('%s 显示标签和每行文本，未编辑保存保留原值', async role => {
    auth.role = role
    const user = userEvent.setup()
    const original = { ...stored }
    renderPage()
    expect(await screen.findByText('H. Kamerlingh Onnes')).toBeVisible()
    expect(screen.getByText('Doe, Jane')).toBeVisible()
    expect(author()).toHaveValue('')
    expect(screen.queryByText('JSON 数组格式')).not.toBeInTheDocument()
    expect(keywords()).toHaveValue('superconductivity\n[FeSe]')
    expect(methods()).toHaveValue('Resistance, cooling\nCompare "zero" resistance')
    await user.click(save())
    expect(mockedApi.put).toHaveBeenCalledWith('/api/admin/papers/88', expect.objectContaining({
      authors: original.authors, keywords_tags: original.keywords_tags, methodology: original.methodology,
    }))
  })

  it.each([
    { value: ['A', 'B'], text: 'A\nB', authors: ['A', 'B'] },
    { value: 'Doe, Jane', text: 'Doe, Jane', authors: ['Doe, Jane'] },
    { value: null, text: '', authors: [] },
    { value: '', text: '', authors: [] },
    { value: '[]', text: '', authors: [] },
    { value: '123', text: '123', authors: ['123'] },
  ])('读取 $value，未编辑原值保持兼容', async ({ value, text, authors }) => {
    stored = { ...stored, authors: value, keywords_tags: value, methodology: value }
    renderPage()
    await screen.findByRole('combobox', { name: '作者' })
    for (const name of authors) {
      expect(within(author().closest('.MuiAutocomplete-root')!).getByText(name)).toBeVisible()
    }
    expect(keywords()).toHaveValue(text)
    expect(methods()).toHaveValue(text)
    await userEvent.click(save())
    const encoded = Array.isArray(value) ? JSON.stringify(value) : value
    expect(mockedApi.put).toHaveBeenCalledWith('/api/admin/papers/88', expect.objectContaining({
      authors: encoded, keywords_tags: encoded, methodology: encoded,
    }))
  })

  it('增删作者、按行编辑、直接保存未确认姓名，并重新加载', async () => {
    const user = userEvent.setup()
    const view = renderPage()
    const oldAuthor = await screen.findByText('H. Kamerlingh Onnes')
    // 通过实际 Chip 删除控件操作，不替换字段组件。
    await user.click(within(oldAuthor.parentElement!).getByTestId('CancelIcon'))
    await user.type(author(), '张三{Enter}')
    await user.type(author(), '张三{Enter}')
    await user.clear(methods())
    await user.type(methods(), 'Resistance, cooling{Enter}Compare (zero)')
    await user.clear(keywords())
    await user.type(keywords(), 'mercury{Enter}superconductivity')
    await user.type(author(), 'Smith, John')
    await user.click(save())
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(1))
    expect(JSON.parse(String(stored.authors))).toEqual(['Doe, Jane', '张三', 'Smith, John'])
    expect(JSON.parse(String(stored.methodology))).toEqual(['Resistance, cooling', 'Compare (zero)'])
    expect(JSON.parse(String(stored.keywords_tags))).toEqual(['mercury', 'superconductivity'])
    view.unmount()
    renderPage()
    expect(await screen.findByText('Smith, John')).toBeVisible()
    expect(screen.queryByText('H. Kamerlingh Onnes')).not.toBeInTheDocument()
    expect(methods()).toHaveValue('Resistance, cooling\nCompare (zero)')
    expect(keywords()).toHaveValue('mercury\nsuperconductivity')
  })

  it('中文输入法确认候选时不提前创建作者标签', async () => {
    renderPage()
    await screen.findByRole('combobox', { name: '作者' })
    fireEvent.change(author(), { target: { value: '张三' } })
    fireEvent.keyDown(author(), { key: 'Enter', keyCode: 13, isComposing: true })
    expect(author()).toHaveValue('张三')
    expect(screen.queryByText('张三')).not.toBeInTheDocument()
    fireEvent.keyDown(author(), { key: 'Enter', keyCode: 13, isComposing: false })
    expect(author()).toHaveValue('')
    expect(screen.getByText('张三')).toBeVisible()
  })

  it('清空列表后保存与重载均为空', async () => {
    const user = userEvent.setup()
    const view = renderPage()
    const first = await screen.findByText('H. Kamerlingh Onnes')
    await user.click(within(first.parentElement!).getByTestId('CancelIcon'))
    await user.click(within(screen.getByText('Doe, Jane').parentElement!).getByTestId('CancelIcon'))
    await user.clear(methods())
    await user.clear(keywords())
    await user.click(save())
    expect(stored).toMatchObject({ authors: '[]', methodology: '[]', keywords_tags: '[]' })
    view.unmount()
    renderPage()
    await screen.findByRole('combobox', { name: '作者' })
    expect(author()).toHaveValue('')
    expect(methods()).toHaveValue('')
    expect(keywords()).toHaveValue('')
    expect(screen.queryByText('Doe, Jane')).not.toBeInTheDocument()
  })

  it('不经失焦直接触发保存也包含姓名；失败保留输入以供重试', async () => {
    mockedApi.put.mockRejectedValueOnce(new Error('连接失败'))
    renderPage()
    await screen.findByRole('combobox', { name: '作者' })
    fireEvent.change(author(), { target: { value: 'New Author' } })
    fireEvent.change(methods(), { target: { value: 'New method, intact\nSecond' } })
    fireEvent.click(save())
    expect(await screen.findByText(/保存失败.*连接失败/)).toBeVisible()
    expect(methods()).toHaveValue('New method, intact\nSecond')
    fireEvent.click(save())
    await waitFor(() => expect(mockedApi.put).toHaveBeenCalledTimes(2))
    expect(JSON.parse(String(stored.authors))).toEqual(['H. Kamerlingh Onnes', 'Doe, Jane', 'New Author'])
    expect(JSON.parse(String(stored.methodology))).toEqual(['New method, intact', 'Second'])
  })
})
