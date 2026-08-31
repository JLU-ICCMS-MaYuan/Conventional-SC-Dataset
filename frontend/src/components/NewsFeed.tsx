import React, { useEffect, useState } from 'react'
import { Alert, Box, Button, Chip, Drawer, FormControl, IconButton, InputLabel, Link, NativeSelect, Paper, Skeleton, Stack, Typography } from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import { api } from '../lib/api'

type Kind = '' | 'news' | 'preprint' | 'journal_article'
const kinds: Record<Exclude<Kind, ''>, string> = { news: '新闻', preprint: '预印本', journal_article: '期刊论文' }
const kindColors: Record<Exclude<Kind, ''>, { bg: string; color: string }> = {
  news: { bg: '#e3f2fd', color: '#1976d2' },
  preprint: { bg: '#f3e5f5', color: '#7b1fa2' },
  journal_article: { bg: '#e8f5e9', color: '#388e3c' }
}
const sourceNames: Record<string, string> = { arxiv: 'arXiv', crossref: 'Crossref', physorg: 'Phys.org' }
interface FeedItem {
  id: string; title: string; kind: Exclude<Kind, ''>; source: string; url: string
  summary: string; summary_source: string; authors: string[]; journal: string; doi: string
  published_at: string; date_precision: string; last_seen_at: string; version: number
  links: { source: string; url: string }[]
}
interface SourceState {
  source: string; status: string; last_success_at: string; last_started_at: string; error_code: string
}
interface FeedResponse { items: FeedItem[]; total: number; page: number; page_size: number; sources: SourceState[] }

export function safeNewsLink(value: string): string | undefined {
  try {
    const url = new URL(value)
    if ((url.protocol === 'https:' || url.protocol === 'http:') && !url.username && !url.password) return value
  } catch { /* 非法外链作为纯文本显示 */ }
  return undefined
}

function dateLabel(value: string, precision = 'day') {
  if (!value) return '日期未提供'
  if (precision === 'year') return value.slice(0, 4) + ' 年'
  if (precision === 'month') return value.slice(0, 7) + '（仅提供月份）'
  return value.slice(0, 10)
}

function timestamp(value: string) {
  if (!value) return '暂无成功记录'
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? '时间未知' : parsed.toLocaleString('zh-CN', { hour12: false })
}

function sourceStatus(state: SourceState) {
  if (state.status === 'failed') return '采集失败，将自动重试'
  if (state.status === 'never') return '尚未采集'
  if (state.status === 'running') {
    return Date.now() - Date.parse(state.last_started_at) > 1000 * 1000 ? '上次采集未完成，等待恢复' : '正在采集'
  }
  if (state.last_success_at && Date.now() - Date.parse(state.last_success_at) > 48 * 3600 * 1000) return '超过 48 小时未更新'
  return '已更新'
}

function FeedLoading() {
  return <Box role="status" aria-live="polite" sx={{ py: 3 }}>
    <Typography variant="body2">正在加载资讯…</Typography>
    {[0, 1, 2].map(i => <Box key={i} sx={{ mt: 2 }}>
      <Skeleton animation={false} width="70%" height={28} />
      <Skeleton animation={false} width="95%" />
      <Skeleton animation={false} width="45%" />
    </Box>)}
  </Box>
}

export default function NewsFeed() {
  const [query, setQuery] = useState<{ kind: Kind; page: number }>({ kind: '', page: 1 })
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<FeedResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [selectedItem, setSelectedItem] = useState<FeedItem | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    const params = new URLSearchParams({ page: String(query.page), page_size: '20' })
    if (query.kind) params.set('kind', query.kind)
    api.get<FeedResponse>('/api/news/feed?' + params, { signal: controller.signal })
      .then(result => {
        if (!Array.isArray(result.items) || !Array.isArray(result.sources) || typeof result.total !== 'number') throw new Error('invalid feed response')
        if (!controller.signal.aborted) setData(result)
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [query, revision])

  const pages = data ? Math.min(10000, Math.max(1, Math.ceil(data.total / 20))) : 1
  return <Box component="section" aria-labelledby="news-feed-heading" sx={{ mb: 6 }}>
    <Stack direction={{ xs: 'column', sm: 'row' }} justifyContent="space-between" alignItems={{ xs: 'stretch', sm: 'center' }} gap={2} sx={{ mb: 2 }}>
      <Box>
        <Typography id="news-feed-heading" component="h2" variant="h2">超导快讯与最新论文</Typography>
        <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>官方来源每日采集 · 按发表时间排序</Typography>
      </Box>
      <FormControl variant="standard" sx={{ minWidth: 160 }}>
        <InputLabel htmlFor="news-kind" shrink>资讯类型</InputLabel>
        <NativeSelect value={query.kind} onChange={event => setQuery({ kind: event.target.value as Kind, page: 1 })} inputProps={{ id: 'news-kind' }}>
          <option value="">全部资讯</option>
          <option value="news">新闻</option>
          <option value="preprint">预印本</option>
          <option value="journal_article">期刊论文</option>
        </NativeSelect>
      </FormControl>
    </Stack>
    <Typography variant="body2" sx={{ mb: 2, color: 'text.primary' }}>
      自动采集，未经本站审核
    </Typography>
    <Paper variant="outlined" sx={{ px: { xs: 2, sm: 3 }, borderRadius: 2, boxShadow: 'none' }}>
      {loading ? <FeedLoading /> : error ? <Alert severity="error" sx={{ my: 2 }} action={<Button color="inherit" onClick={() => setRevision(v => v + 1)}>重试</Button>}>
        资讯读取失败，请重试。此状态不代表没有新闻。
      </Alert> : data?.items.length === 0 ? <Box sx={{ py: 5 }} role="status">
        <Typography fontWeight={600}>当前筛选下暂无资讯</Typography>
        <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>可切换资讯类型，或查看下方来源是否已成功采集。</Typography>
      </Box> : <Box component="ul" sx={{ listStyle: 'none', m: 0, p: 0 }}>
        {data?.items.map(item => <Box
          component="li"
          key={item.id}
          onClick={() => setSelectedItem(item)}
          sx={{
            py: 2.5,
            borderBottom: '1px solid',
            borderColor: 'divider',
            '&:last-child': { borderBottom: 0 },
            cursor: 'pointer',
            '&:hover': { bgcolor: 'action.hover' },
            transition: 'background-color 0.2s',
            px: 1,
            mx: -1,
            borderRadius: 1
          }}>
          <Stack direction="row" useFlexGap flexWrap="wrap" alignItems="center" gap={1} sx={{ mb: 1 }}>
            <Chip
              size="small"
              label={kinds[item.kind]}
              sx={{
                bgcolor: kindColors[item.kind].bg,
                color: kindColors[item.kind].color,
                fontWeight: 500,
                border: 'none'
              }}
            />
            <Typography variant="body2" color="text.secondary">{sourceNames[item.source] || item.source}</Typography>
            <Typography variant="body2" color="text.secondary">发表：{dateLabel(item.published_at, item.date_precision)}</Typography>
            {item.kind === 'preprint' && item.version > 0 && <Typography variant="body2" color="text.secondary">v{item.version}</Typography>}
          </Stack>
          <Typography component="h3" variant="h3" sx={{ lineHeight: 1.5, maxWidth: '80ch', fontWeight: 600 }}>
            {item.title}
          </Typography>
          {(item.authors.length > 0 || item.journal) && <Typography variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>
            {item.authors.slice(0, 4).join('、')}{item.authors.length > 4 ? ' 等' : ''}{item.journal ? ' · ' + item.journal : ''}
          </Typography>}
        </Box>)}
      </Box>}
    </Paper>
    {!loading && !error && data && data.total > 0 && <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} sx={{ mt: 2 }}>
      <Typography variant="body2" aria-live="polite">共 {data.total} 条 · 第 {query.page} / {pages} 页</Typography>
      <Stack direction="row" gap={1}>
        <Button variant="outlined" disabled={query.page <= 1} onClick={() => setQuery(q => ({ ...q, page: q.page - 1 }))}>上一页</Button>
        <Button variant="outlined" disabled={query.page >= pages} onClick={() => setQuery(q => ({ ...q, page: q.page + 1 }))}>下一页</Button>
      </Stack>
    </Stack>}
    {data && <Box component="details" sx={{ mt: 2, color: 'text.secondary', fontSize: 13 }}>
      <Box component="summary" sx={{ cursor: 'pointer', py: 1 }}>来源更新状态
        {data.sources.some(s => s.status === 'failed' || s.status === 'never' || sourceStatus(s).includes('未')) ? ' · 有来源需要关注' : ''}
      </Box>
      <Stack gap={1} sx={{ pt: 1 }}>
        {data.sources.map(state => <Box key={state.source}>
          <Typography variant="body2">{sourceNames[state.source]}：{sourceStatus(state)}{state.error_code ? '（' + state.error_code + '）' : ''}</Typography>
          <Typography variant="body2">最后成功：{timestamp(state.last_success_at)}</Typography>
        </Box>)}
        <Typography variant="body2">Phys.org 仅覆盖当前订阅窗口；停机期间已移除的历史新闻可能无法补回。</Typography>
      </Stack>
    </Box>}

    {/* 右侧抽屉详情 */}
    <Drawer
      anchor="right"
      open={selectedItem !== null}
      onClose={() => setSelectedItem(null)}
      sx={{
        '& .MuiDrawer-paper': {
          width: { xs: '100%', sm: '600px', md: '700px' },
          maxWidth: '100vw'
        }
      }}
    >
      {selectedItem && <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ p: 2, borderBottom: '1px solid', borderColor: 'divider', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Chip
            size="small"
            label={kinds[selectedItem.kind]}
            sx={{
              bgcolor: kindColors[selectedItem.kind].bg,
              color: kindColors[selectedItem.kind].color,
              fontWeight: 500,
              border: 'none'
            }}
          />
          <IconButton onClick={() => setSelectedItem(null)} size="small">
            <CloseIcon />
          </IconButton>
        </Box>
        <Box sx={{ flex: 1, overflowY: 'auto', p: 3 }}>
          <Typography component="h2" variant="h4" sx={{ lineHeight: 1.4, mb: 2, fontWeight: 600 }}>
            {selectedItem.title}
          </Typography>

          {(selectedItem.authors.length > 0 || selectedItem.journal) && <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            <strong>作者：</strong>{selectedItem.authors.slice(0, 10).join('、')}{selectedItem.authors.length > 10 ? ' 等' : ''}
            {selectedItem.journal && <><br /><strong>期刊：</strong>{selectedItem.journal}</>}
          </Typography>}

          <Stack direction="row" useFlexGap flexWrap="wrap" gap={1.5} sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary"><strong>来源：</strong>{sourceNames[selectedItem.source] || selectedItem.source}</Typography>
            <Typography variant="body2" color="text.secondary"><strong>发表：</strong>{dateLabel(selectedItem.published_at, selectedItem.date_precision)}</Typography>
            {selectedItem.kind === 'preprint' && selectedItem.version > 0 && <Typography variant="body2" color="text.secondary"><strong>版本：</strong>v{selectedItem.version}</Typography>}
            <Typography variant="body2" color="text.secondary"><strong>采集：</strong>{dateLabel(selectedItem.last_seen_at)}</Typography>
          </Stack>

          {selectedItem.summary && <>
            <Typography variant="body1" fontWeight={600} sx={{ mb: 1.5 }}>摘要</Typography>
            <Typography variant="body2" sx={{ lineHeight: 1.8, whiteSpace: 'pre-line', mb: 3, color: 'text.primary' }}>
              {selectedItem.summary}
            </Typography>
            {selectedItem.summary_source && <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary', fontStyle: 'italic' }}>
              摘要来源：{sourceNames[selectedItem.summary_source]}
            </Typography>}
          </>}

          {selectedItem.doi && <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            <strong>DOI：</strong>{selectedItem.doi}
          </Typography>}

          {selectedItem.links.filter(link => safeNewsLink(link.url)).length > 0 && <>
            <Typography variant="body1" fontWeight={600} sx={{ mb: 1.5 }}>原文链接</Typography>
            <Stack gap={1} sx={{ mb: 3 }}>
              {selectedItem.links.filter(link => safeNewsLink(link.url)).map(link =>
                <Link key={link.source} href={safeNewsLink(link.url)} target="_blank" rel="noopener noreferrer" variant="body2" sx={{ display: 'block' }}>
                  {sourceNames[link.source] || link.source} ↗
                </Link>)}
            </Stack>
          </>}
        </Box>
      </Box>}
    </Drawer>
  </Box>
}

interface ManualItem { id: number; title: string; summary: string; event_date: string; link: string }

export function ManualNews() {
  const [items, setItems] = useState<ManualItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [revision, setRevision] = useState(0)
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setError(false)
    api.get<ManualItem[]>('/api/news', { signal: controller.signal })
      .then(result => {
        if (!Array.isArray(result)) throw new Error('invalid news response')
        if (!controller.signal.aborted) setItems(result)
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [revision])
  return <Box component="section" aria-labelledby="manual-news-heading" sx={{ mb: 6 }}>
    <Typography id="manual-news-heading" component="h2" variant="h2" sx={{ mb: 2 }}>人工快讯</Typography>
    {loading ? <Typography role="status" variant="body2">正在加载人工快讯…</Typography> : error ?
      <Alert severity="error" action={<Button color="inherit" onClick={() => setRevision(v => v + 1)}>重试人工快讯</Button>}>人工快讯读取失败</Alert> :
      items.length === 0 ? <Typography variant="body2" color="text.secondary">暂无人工发布的快讯。</Typography> :
      <Stack gap={2}>{items.map(item => <Box key={item.id} sx={{ borderBottom: '1px solid', borderColor: 'divider', pb: 2, overflowWrap: 'anywhere' }}>
        <Typography variant="body2" color="text.secondary">{item.event_date}</Typography>
        <Typography component="h3" variant="h3" sx={{ mt: 1 }}>
          {safeNewsLink(item.link) ? <Link href={safeNewsLink(item.link)} target="_blank" rel="noopener noreferrer">{item.title}</Link> : item.title}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1, lineHeight: 1.8 }}>{item.summary}</Typography>
      </Box>)}</Stack>}
  </Box>
}
