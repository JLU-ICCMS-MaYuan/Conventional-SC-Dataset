import '@testing-library/jest-dom/vitest'
import React from 'react'
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { LanguageProvider } from '../../frontend/src/context/LanguageContext'
import NewsPage from '../../frontend/src/pages/NewsPage'
import { api } from '../../frontend/src/lib/api'

type Kind = 'news' | 'preprint' | 'journal_article'

const kinds: Kind[] = ['news', 'preprint', 'journal_article']
const kindTitles: Record<Kind, string> = {
  news: 'News',
  preprint: 'Preprints',
  journal_article: 'Articles',
}

function feedItem(kind: Kind, page: number, index: number) {
  return {
    id: `${kind}-${page}-${index}`,
    title: `${kindTitles[kind]} ${page}-${index}`,
    kind,
    source: kind === 'news' ? 'physorg' : kind === 'preprint' ? 'arxiv' : 'crossref',
    url: `https://example.com/${kind}/${page}/${index}`,
    summary: `Summary for ${kind} ${page}-${index}`,
    summary_source: 'physorg',
    authors: ['Test Author'],
    journal: kind === 'journal_article' ? 'Test Journal' : '',
    doi: '',
    published_at: '2026-09-03T00:00:00Z',
    date_precision: 'day',
    last_seen_at: '2026-09-03T00:00:00Z',
    version: kind === 'preprint' ? 1 : 0,
    links: [{ source: 'source', url: `https://example.com/${kind}/${page}/${index}` }],
  }
}

const getMock = vi.mocked(api.get)

vi.mock('../../frontend/src/lib/api', () => ({
  api: { get: vi.fn() },
}))

function installFeedMock({ failedKind }: { failedKind?: Kind } = {}) {
  getMock.mockImplementation((url: string) => {
    if (url === '/api/news') return Promise.resolve([])
    const parsed = new URL(url, 'http://localhost')
    if (parsed.pathname !== '/api/news/feed') return Promise.reject(new Error(`Unexpected request: ${url}`))
    const kind = parsed.searchParams.get('kind') as Kind
    const page = Number(parsed.searchParams.get('page'))
    if (failedKind === kind) return Promise.reject(new Error('request failed'))
    return Promise.resolve({
      items: Array.from({ length: 5 }, (_, index) => feedItem(kind, page, index + 1)),
      total: 10,
      page,
      page_size: Number(parsed.searchParams.get('page_size')),
      sources: [],
    })
  })
}

function CurrentLocation() {
  const location = useLocation()
  return <output data-testid="location">{location.pathname}</output>
}

function renderNews(lang: 'zh' | 'en' = 'en') {
  localStorage.setItem('sc-wiki.language', lang)
  return render(
    <MemoryRouter initialEntries={['/news']}>
      <LanguageProvider>
        <Routes>
          <Route path="/news" element={<NewsPage />} />
          <Route path="/search" element={<CurrentLocation />} />
        </Routes>
      </LanguageProvider>
    </MemoryRouter>,
  )
}

afterEach(() => {
  cleanup()
  localStorage.clear()
  vi.clearAllMocks()
})

describe('Issue #83 News 页面品牌与三列资讯流', () => {
  it('显示双语品牌，删除重复入口，并将探索按钮跳转到 /search', async () => {
    installFeedMock()
    const user = userEvent.setup()
    renderNews('en')

    expect(await screen.findByRole('heading', { name: 'Superconduct Wiki', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('Key Laboratory of Material Simulation Methods & Software of Ministry of Education, Jilin University, China')).toBeInTheDocument()
    expect(screen.getByText(/AI-driven, decentralized research infrastructure/i)).toBeInTheDocument()
    expect(screen.queryByText('Element Search')).not.toBeInTheDocument()
    expect(screen.queryByText('AI Q&A')).not.toBeInTheDocument()
    expect(screen.queryByText('Tc Prediction')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'AI Literature Assistant' })).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Start Exploring' }))
    expect(screen.getByTestId('location')).toHaveTextContent('/search')

    renderNews('zh')
    expect(await screen.findByRole('heading', { name: '超导维基', level: 1 })).toBeInTheDocument()
    expect(screen.getByText('吉林大学 物质模拟方法与软件教育部重点实验室')).toBeInTheDocument()
  })

  it('按类型分别加载 5 条，并且一个栏目的翻页不改变其他栏目', async () => {
    installFeedMock()
    const user = userEvent.setup()
    renderNews()

    for (const kind of kinds) {
      expect(await screen.findByText(`${kindTitles[kind]} 1-5`)).toBeInTheDocument()
    }
    await waitFor(() => expect(getMock).toHaveBeenCalledTimes(4))
    for (const kind of kinds) {
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining(`kind=${kind}`), expect.anything())
      expect(getMock).toHaveBeenCalledWith(expect.stringContaining('page_size=5'), expect.anything())
    }

    const newsColumn = screen.getByRole('region', { name: 'News' })
    await user.click(within(newsColumn).getByRole('button', { name: 'Next' }))
    expect(await within(newsColumn).findByText('News 2-5')).toBeInTheDocument()
    expect(screen.getByText('Preprints 1-5')).toBeInTheDocument()
    expect(screen.getByText('Articles 1-5')).toBeInTheDocument()
  })

  it('隔离栏目失败状态，并保留条目详情抽屉', async () => {
    installFeedMock({ failedKind: 'preprint' })
    renderNews()

    expect(await screen.findByText('Failed to load the feed. Please retry. This does not mean there is no news.')).toBeInTheDocument()
    expect(await screen.findByText('News 1-1')).toBeInTheDocument()
    expect(screen.getByText('Articles 1-1')).toBeInTheDocument()

    fireEvent.click(screen.getByText('News 1-1'))
    expect(await screen.findByText('Summary for news 1-1')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /source/i })).toHaveAttribute('rel', 'noopener noreferrer')
  })
})
