import React from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom/vitest'
import { MemoryRouter } from 'react-router-dom'
import NewsFeed from '../../frontend/src/components/NewsFeed'
import NewsPage from '../../frontend/src/pages/NewsPage'

const row = {
 id: 'a', title: 'Superconducting test article', kind: 'preprint', source: 'arxiv',
 url: 'https://arxiv.org/abs/2608.12345', links: [{ source: 'arxiv', url: 'https://arxiv.org/abs/2608.12345' }],
 authors: ['Test Author'], summary: 'Test abstract', summary_source: 'arxiv',
 published_at: '2026-08-30T00:00:00Z', date_precision: 'day', journal: '', doi: '',
 first_seen_at: '2026-08-31T00:00:00Z', last_seen_at: '2026-08-31T00:00:00Z', version: 2,
}
const body = { items: [row], total: 21, page: 1, page_size: 20,
 sources: [{ source: 'arxiv', status: 'success', last_success_at: '2026-08-31T00:00:00Z' }] }
function response(value: unknown, status = 200) {
 return new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
}
afterEach(() => { cleanup(); vi.unstubAllGlobals() })

it('shows provenance and makes pagination/filter requests', async () => {
 const fetcher = vi.fn().mockImplementation(() => Promise.resolve(response(body)))
 vi.stubGlobal('fetch', fetcher)
 render(<NewsFeed />)
 expect(screen.getAllByRole('status')).toHaveLength(3)
 expect(screen.getAllByRole('status')[0]).toHaveTextContent('正在加载')
 await screen.findAllByText(row.title)
 expect(screen.getByText('自动采集，未经本站审核')).toBeInTheDocument()
 fireEvent.click(screen.getAllByRole('button', { name: '下一页' })[0])
 await waitFor(() => expect(fetcher).toHaveBeenCalledWith(
  expect.stringMatching(/kind=news.*page=2/), expect.anything(),
 ))
 for (const kind of ['news', 'preprint', 'journal_article']) {
  expect(fetcher).toHaveBeenCalledWith(expect.stringContaining(`kind=${kind}`), expect.anything())
 }
 fireEvent.click((await screen.findAllByText(row.title))[0])
 expect(await screen.findByRole('link', { name: 'arXiv ↗' })).toHaveAttribute('rel', 'noopener noreferrer')
})

it('distinguishes failures from empty results and retries', async () => {
 const fetcher = vi.fn().mockResolvedValueOnce(response({ error: 'failed' }, 500))
   .mockResolvedValueOnce(response({ error: 'failed' }, 500))
   .mockResolvedValueOnce(response({ error: 'failed' }, 500))
   .mockResolvedValue(response({ ...body, items: [], total: 0, sources: [] }))
 vi.stubGlobal('fetch', fetcher)
 render(<NewsFeed />)
 expect((await screen.findAllByRole('alert'))[0]).toHaveTextContent('读取失败')
 expect(screen.queryByText('当前筛选下暂无资讯')).not.toBeInTheDocument()
 fireEvent.click(screen.getAllByRole('button', { name: '重试' })[0])
 expect(await screen.findByText('当前筛选下暂无资讯')).toBeInTheDocument()
})

it('shows collection failure independently of cached items and blocks unsafe links', async () => {
 vi.stubGlobal('fetch', vi.fn().mockResolvedValue(response({ ...body,
  items: [{ ...row, url: 'javascript:alert(1)', links: [] }],
  sources: [{ source: 'physorg', status: 'failed', last_success_at: '', error_code: 'rate_limited' }],
 })))
 render(<NewsFeed />)
 expect(await screen.findByText(/采集失败/)).toBeInTheDocument()
 expect(screen.getByText(row.title)).toBeInTheDocument()
 expect(screen.queryByRole('link', { name: row.title })).not.toBeInTheDocument()
})

it('preserves manual news and Nobel milestones', async () => {
 vi.stubGlobal('fetch', vi.fn().mockImplementation((url: string) => Promise.resolve(
  response(url === '/api/news' ? [{ id: 1, title: '人工快讯样本', summary: '人工维护', event_date: '2026-08-31', link: '' }] : body),
 )))
 render(<MemoryRouter><NewsPage /></MemoryRouter>)
 expect(await screen.findByText('人工快讯样本')).toBeInTheDocument()
 expect(screen.getByText('诺贝尔奖里程碑')).toBeInTheDocument()
 expect(screen.getByText('Heike Kamerlingh Onnes')).toBeInTheDocument()
})
