import '@testing-library/jest-dom/vitest'
import React from 'react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import PaperDetailPage from '../../frontend/src/pages/PaperDetailPage'
import NotFoundPage from '../../frontend/src/pages/NotFoundPage'
import MyPapersList from '../../frontend/src/components/MyPapersList'
import { api } from '../../frontend/src/lib/api'
import type { ApiError } from '../../frontend/src/lib/api'

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn() },
}))

vi.mock('../../frontend/src/components/StructureViewer3D', () => ({
  default: () => <div data-testid="structure-viewer" />,
}))

const mockedApi = vi.mocked(api)

const makePaper = (overrides: Record<string, unknown> = {}) => ({
  id: 4,
  title: 'Potential high-Tc superconducting lanthanum and yttrium hydrides at high pressure',
  doi: '10.1073/pnas.1704505114',
  journal: 'PNAS',
  year: 2017,
  authors: ['Hanyu Liu'],
  abstract: 'temperature Tc calculated for LaH10 is 274-286 K at 210 GPa.',
  review_status: 'pending',
  key_properties: [],
  material_states: [],
  ...overrides,
})

// 渲染 /papers/:id 路由，并提供 /upload 目标以观察返回导航
const renderAt = (path: string) =>
  render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/papers/:id" element={<PaperDetailPage />} />
        <Route path="/upload" element={<div data-testid="upload-page">上传页</div>} />
      </Routes>
    </MemoryRouter>,
  )

const apiError = (status: number, message: string): ApiError => {
  const error = new Error(message) as ApiError
  error.status = status
  return error
}

beforeEach(() => {
  vi.clearAllMocks()
})

afterEach(() => {
  cleanup()
})

describe('论文详情路由 /papers/:id', () => {
  it('按 URL 中的论文编号渲染只读详情', async () => {
    mockedApi.get.mockResolvedValue(makePaper())

    renderAt('/papers/4')

    expect(await screen.findByText('论文详情')).toBeInTheDocument()
    expect(screen.getByText('只读模式')).toBeInTheDocument()
    expect(mockedApi.get).toHaveBeenCalledWith('/api/papers/4')
    // 组件现在是只读展示（标签+值分离），改用文本断言
    await waitFor(() => {
      expect(screen.getByText('DOI')).toBeInTheDocument()
      expect(screen.getByText('10.1073/pnas.1704505114')).toBeInTheDocument()
    })
    expect(screen.getByText('期刊')).toBeInTheDocument()
    expect(screen.getByText('PNAS')).toBeInTheDocument()
    expect(screen.getByText('年份')).toBeInTheDocument()
    expect(screen.getByText('2017')).toBeInTheDocument()
    expect(screen.getByText(/Potential high-Tc superconducting lanthanum/)).toBeInTheDocument()
  })

  it('不同 URL 编号加载不同论文，页面内容仅由地址决定', async () => {
    mockedApi.get.mockResolvedValue(makePaper({ id: 7, doi: '10.9999/other', journal: 'Nature' }))

    renderAt('/papers/7')

    await waitFor(() => expect(mockedApi.get).toHaveBeenCalledWith('/api/papers/7'))
    await waitFor(() => {
      expect(screen.getByText('10.9999/other')).toBeInTheDocument()
    })
    expect(screen.getByText('Nature')).toBeInTheDocument()
  })

  it('点击返回上传列表导航到 /upload', async () => {
    mockedApi.get.mockResolvedValue(makePaper())

    renderAt('/papers/4')

    fireEvent.click(await screen.findByRole('button', { name: '返回上传列表' }))

    expect(await screen.findByTestId('upload-page')).toBeInTheDocument()
  })
})

describe('论文详情路由的失败分流', () => {
  it('403 显示无权提示且不渲染论文内容', async () => {
    mockedApi.get.mockRejectedValue(apiError(403, '无权查看该论文'))

    renderAt('/papers/4')

    expect(await screen.findByText('无权查看该论文')).toBeInTheDocument()
    expect(screen.queryByText('论文详情')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('DOI')).not.toBeInTheDocument()
    expect(screen.queryByText(/Potential high-Tc/)).not.toBeInTheDocument()
  })

  it('404 显示论文不存在且不渲染论文内容', async () => {
    mockedApi.get.mockRejectedValue(apiError(404, '论文不存在'))

    renderAt('/papers/999999')

    expect(await screen.findByText('论文不存在')).toBeInTheDocument()
    expect(screen.queryByText('论文详情')).not.toBeInTheDocument()
  })

  it('非数字编号本地拦截，不发起请求', async () => {
    renderAt('/papers/abc')

    expect(await screen.findByText('论文编号无效')).toBeInTheDocument()
    expect(mockedApi.get).not.toHaveBeenCalled()
    expect(screen.queryByText('论文详情')).not.toBeInTheDocument()
  })

  it('其他异常显示加载失败，可区分于无权与不存在', async () => {
    mockedApi.get.mockRejectedValue(new Error('Failed to fetch'))

    renderAt('/papers/4')

    expect(await screen.findByText('加载论文失败')).toBeInTheDocument()
    expect(screen.queryByText('无权查看该论文')).not.toBeInTheDocument()
    expect(screen.queryByText('论文不存在')).not.toBeInTheDocument()
    expect(screen.queryByText('论文详情')).not.toBeInTheDocument()
  })

  it('失败页仍提供返回上传列表的操作', async () => {
    mockedApi.get.mockRejectedValue(apiError(403, '无权查看该论文'))

    renderAt('/papers/4')

    fireEvent.click(await screen.findByRole('button', { name: '返回上传列表' }))

    expect(await screen.findByTestId('upload-page')).toBeInTheDocument()
  })
})

describe('详情页前往「我的论文」的入口', () => {
  it('点击「我的论文」导航到用户中心', async () => {
    mockedApi.get.mockResolvedValue(makePaper())

    render(
      <MemoryRouter initialEntries={['/papers/4']}>
        <Routes>
          <Route path="/papers/:id" element={<PaperDetailPage />} />
          <Route path="/account" element={<div data-testid="account-page">用户中心</div>} />
        </Routes>
      </MemoryRouter>,
    )

    fireEvent.click(await screen.findByRole('button', { name: '我的论文' }))

    expect(await screen.findByTestId('account-page')).toBeInTheDocument()
  })
})

describe('我的论文列表', () => {
  const renderList = () =>
    render(
      <MemoryRouter initialEntries={['/account']}>
        <Routes>
          <Route path="/account" element={<MyPapersList />} />
          <Route path="/papers/:id" element={<div data-testid="detail-page">论文详情页</div>} />
        </Routes>
      </MemoryRouter>,
    )

  it('渲染已提交论文并可点击进入详情', async () => {
    mockedApi.get.mockResolvedValue({
      items: [{ id: 4, title: 'LaH10 高压超导', journal: 'PNAS', year: 2017, review_status: 'pending' }],
    })

    renderList()

    expect(await screen.findByText('LaH10 高压超导')).toBeInTheDocument()
    expect(screen.getByText('待审核')).toBeInTheDocument()
    expect(mockedApi.get).toHaveBeenCalledWith('/api/papers/my-uploads')

    fireEvent.click(screen.getByText('LaH10 高压超导'))
    expect(await screen.findByTestId('detail-page')).toBeInTheDocument()
  })

  it('没有已提交论文时显示空状态', async () => {
    mockedApi.get.mockResolvedValue({ items: [] })

    renderList()

    expect(await screen.findByText(/还没有提交过论文/)).toBeInTheDocument()
  })

  it('加载失败时显示错误与重试', async () => {
    mockedApi.get.mockRejectedValue(new Error('boom'))

    renderList()

    expect(await screen.findByText('boom')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument()
  })
})

// GET /api/papers/:id 透传数据库里的 JSON 文本列（keywords_tags / methodology / authors），
// 所以这些字段到前端可能是 JSON 字符串而不是数组。此前详情页对其直接 .map()，
// 真实提交的论文一打开就整树崩溃、整页白屏（连顶栏与侧栏都不渲染）。
describe('详情页对 JSON 文本列字段的容错', () => {
  const jsonStringPaper = makePaper({
    id: 9,
    title: 'Further experiments with liquid helium',
    authors: '["H. Kamerlingh Onnes"]',
    keywords_tags: '["超导", "汞", "液氦"]',
    methodology: '["电阻测量", "低温实验"]',
  })

  it('keywords_tags 为 JSON 字符串时正常渲染详情而非白屏', async () => {
    mockedApi.get.mockResolvedValue(jsonStringPaper)

    renderAt('/papers/9')

    expect(await screen.findByText('论文详情')).toBeInTheDocument()
    expect(screen.getByText('超导')).toBeInTheDocument()
    expect(screen.getByText('汞')).toBeInTheDocument()
    expect(screen.getByText('液氦')).toBeInTheDocument()
  })

  it('methodology 为 JSON 字符串时逐项可读展示', async () => {
    mockedApi.get.mockResolvedValue(jsonStringPaper)

    renderAt('/papers/9')

    expect(await screen.findByText('• 电阻测量')).toBeInTheDocument()
    expect(screen.getByText('• 低温实验')).toBeInTheDocument()
  })

  it('authors 为 JSON 字符串时展示人名而非 JSON 原文', async () => {
    mockedApi.get.mockResolvedValue(jsonStringPaper)

    renderAt('/papers/9')

    expect(await screen.findByText('H. Kamerlingh Onnes')).toBeInTheDocument()
    const bodyText = document.body.textContent || ''
    expect(bodyText).not.toContain('["')
    expect(bodyText).not.toContain('"]')
  })
})

describe('未匹配地址的兜底页', () => {
  it('相对路径误拼的地址显示「页面不存在」而非白屏', async () => {
    render(
      <MemoryRouter initialEntries={['/upload/papers/999999']}>
        <Routes>
          <Route path="/papers/:id" element={<PaperDetailPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </MemoryRouter>,
    )

    expect(await screen.findByText('页面不存在')).toBeInTheDocument()
    expect(screen.getByText(/\/upload\/papers\/999999/)).toBeInTheDocument()
    expect(mockedApi.get).not.toHaveBeenCalled()
  })
})
