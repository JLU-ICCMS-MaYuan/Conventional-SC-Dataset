import React, { useCallback, useEffect, useState } from 'react'
import { Alert, Box, Button, Chip, Drawer, IconButton, Link, Paper, Skeleton, Stack, Typography } from '@mui/material'
import { Close as CloseIcon } from '@mui/icons-material'
import { api } from '../lib/api'
import { useLanguage } from '../context/LanguageContext'
import type { Lang } from '../i18n'

type Kind = 'news' | 'preprint' | 'journal_article'
const PAGE_SIZE = 5
const kindColors: Record<Kind, { bg: string; color: string }> = {
  news: { bg: '#e3f2fd', color: '#1976d2' },
  preprint: { bg: '#f3e5f5', color: '#7b1fa2' },
  journal_article: { bg: '#e8f5e9', color: '#388e3c' }
}
const sourceNames: Record<string, string> = { arxiv: 'arXiv', crossref: 'Crossref', openalex: 'OpenAlex', physorg: 'Phys.org', google_news: 'Google News', aps: 'APS', acs: 'ACS', nature: 'Nature', science: 'Science', nsr: 'NSR', cpl: 'CPL', cpb: 'CPB', materials_today: 'Materials Today' }
type TFunc = (key: string, vars?: Record<string, string | number>) => string
interface FeedItem {
  id: string; title: string; kind: Exclude<Kind, ''>; source: string; url: string
  summary: string; summary_source: string; authors: string[]; journal: string; doi: string
  published_at: string; date_precision: string; last_seen_at: string; version: number
  content_type: string; display_kind: Kind; discovery_source: string; original_source: string; relevance_evidence: string
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

function dateLabel(t: TFunc, value: string, precision = 'day') {
  if (!value) return t('news.dateNotProvided')
  if (precision === 'year') return t('news.yearOnly', { year: value.slice(0, 4) })
  if (precision === 'month') return t('news.monthOnly', { month: value.slice(0, 7) })
  return value.slice(0, 10)
}

function timestamp(t: TFunc, lang: Lang, value: string) {
  if (!value) return t('news.noSuccessRecord')
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? t('news.timeUnknown') : parsed.toLocaleString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour12: false })
}

/** 来源是否需要用户关注：失败、从未采集、卡住或长时间未更新。 */
function sourceNeedsAttention(state: SourceState) {
  if (state.status === 'failed' || state.status === 'never') return true
  if (state.status === 'running') return Date.now() - Date.parse(state.last_started_at) > 1000 * 1000
  if (state.last_success_at && Date.now() - Date.parse(state.last_success_at) > 48 * 3600 * 1000) return true
  return false
}

function sourceStatus(t: TFunc, state: SourceState) {
  if (state.status === 'failed') return t('news.sourceFailed')
  if (state.status === 'never') return t('news.sourceNever')
  if (state.status === 'running') {
    return Date.now() - Date.parse(state.last_started_at) > 1000 * 1000 ? t('news.sourceStalled') : t('news.sourceRunning')
  }
  if (state.last_success_at && Date.now() - Date.parse(state.last_success_at) > 48 * 3600 * 1000) return t('news.sourceStale', { hours: 48 })
  return t('news.sourceUpdated')
}

function FeedLoading({ label }: { label: string }) {
  return <Box role="status" aria-live="polite" sx={{ py: 3 }}>
    <Typography variant="body2">{label}</Typography>
    {[0, 1, 2].map(i => <Box key={i} sx={{ mt: 2 }}>
      <Skeleton animation={false} width="70%" height={28} />
      <Skeleton animation={false} width="95%" />
      <Skeleton animation={false} width="45%" />
    </Box>)}
  </Box>
}

interface FeedColumnProps {
  kind: Kind
  label: string
  onSelect: (item: FeedItem) => void
  onSources: (sources: SourceState[]) => void
}

function FeedColumn({ kind, label, onSelect, onSources }: FeedColumnProps) {
  const { t, lang } = useLanguage()
  const [page, setPage] = useState(1)
  const [revision, setRevision] = useState(0)
  const [data, setData] = useState<FeedResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const kinds: Record<Exclude<Kind, ''>, string> = {
    news: t('news.kindNews'),
    preprint: t('news.kindPreprint'),
    journal_article: t('news.kindJournalArticle'),
  }

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    setError(false)
    const params = new URLSearchParams({ kind, page: String(page), page_size: String(PAGE_SIZE) })
    api.get<FeedResponse>('/api/news/feed?' + params, { signal: controller.signal })
      .then(result => {
        if (!Array.isArray(result.items) || !Array.isArray(result.sources) || typeof result.total !== 'number') throw new Error('invalid feed response')
        if (!controller.signal.aborted) {
          setData(result)
          onSources(result.sources)
        }
      })
      .catch(() => { if (!controller.signal.aborted) setError(true) })
      .finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [kind, onSources, page, revision])

  const pages = data ? Math.min(10000, Math.max(1, Math.ceil(data.total / PAGE_SIZE))) : 1
  return <Paper component="section" aria-label={label} variant="outlined" sx={{ minWidth: 0, height: '100%', display: 'flex', flexDirection: 'column', px: { xs: 2, md: 2.5 }, borderRadius: 2, boxShadow: 'none' }}>
    <Typography component="h3" variant="h3" sx={{ flexShrink: 0, pt: 2, pb: 1.5, borderBottom: '1px solid', borderColor: 'divider' }}>{label}</Typography>
    <Box sx={{ height: 430, display: 'flex', flexDirection: 'column' }}>
      {loading ? <FeedLoading label={t('news.loadingFeed')} /> : error ? <Alert severity="error" sx={{ my: 2 }} action={<Button color="inherit" onClick={() => setRevision(v => v + 1)}>{t('common.retry')}</Button>}>
        {t('news.feedLoadFailed')}
      </Alert> : data?.items.length === 0 ? <Box sx={{ py: 5 }} role="status">
        <Typography fontWeight={600}>{t('news.feedEmpty')}</Typography>
        <Typography variant="body2" sx={{ mt: 1, color: 'text.secondary' }}>{t('news.feedEmptyHint')}</Typography>
      </Box> : <Box component="ul" sx={{ flex: 1, minHeight: 0, display: 'grid', gridTemplateRows: 'repeat(5, minmax(0, 1fr))', listStyle: 'none', m: 0, p: 0 }}>
        {data?.items.map(item => <Box
          component="li"
          key={item.id}
          onClick={() => onSelect(item)}
          sx={{
            minHeight: 0,
            py: 1.25,
            borderBottom: '1px solid',
            borderColor: 'divider',
            '&:last-child': { borderBottom: 0 },
            cursor: 'pointer',
            '&:hover': { bgcolor: 'action.hover' },
            transition: 'background-color 0.2s',
            px: 1,
            mx: -1,
            borderRadius: 1,
            overflow: 'hidden',
          }}>
          <Stack direction="row" useFlexGap flexWrap="wrap" alignItems="center" gap={0.75} sx={{ mb: 0.5 }}>
            <Chip
              size="small"
              label={item.content_type === 'research_report' ? t('news.kindResearchReport') : kinds[item.kind]}
              sx={{
                bgcolor: kindColors[item.kind].bg,
                color: kindColors[item.kind].color,
                fontWeight: 500,
                border: 'none'
              }}
            />
            <Typography variant="body2" color="text.secondary">{sourceNames[item.original_source] || sourceNames[item.source] || item.source}</Typography>
            <Typography variant="body2" color="text.secondary">{t('news.publishedAt', { date: dateLabel(t, item.published_at, item.date_precision) })}</Typography>
            {item.kind === 'preprint' && item.version > 0 && <Typography variant="body2" color="text.secondary">v{item.version}</Typography>}
          </Stack>
          <Typography component="h4" variant="body2" sx={{ lineHeight: 1.4, fontWeight: 700, display: '-webkit-box', WebkitBoxOrient: 'vertical', WebkitLineClamp: 2, overflow: 'hidden' }}>
            {item.title}
          </Typography>
          {(item.authors.length > 0 || item.journal) && <Typography variant="caption" sx={{ mt: 0.25, color: 'text.secondary', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {item.authors.slice(0, 4).join(lang === 'zh' ? '、' : ', ')}{item.authors.length > 4 ? t('news.etAl') : ''}{item.journal ? ' · ' + item.journal : ''}
          </Typography>}
        </Box>)}
      </Box>}
    </Box>
    {!loading && !error && data && data.total > 0 && <Stack direction="row" justifyContent="space-between" alignItems="center" flexWrap="wrap" gap={1} sx={{ flexShrink: 0, minHeight: 72, py: 1.5 }}>
      <Typography variant="body2" aria-live="polite">{t('news.pageInfo', { total: data.total, page, pages })}</Typography>
      <Stack direction="row" gap={1}>
        <Button variant="outlined" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>{t('news.prevPage')}</Button>
        <Button variant="outlined" disabled={page >= pages} onClick={() => setPage(value => value + 1)}>{t('news.nextPage')}</Button>
      </Stack>
    </Stack>}
  </Paper>
}

export default function NewsFeed() {
  const { t, lang } = useLanguage()
  const [selectedItem, setSelectedItem] = useState<FeedItem | null>(null)
  const [sources, setSources] = useState<SourceState[]>([])
  const handleSources = useCallback((nextSources: SourceState[]) => setSources(nextSources), [])
  const columns: { kind: Kind; label: string }[] = [
    { kind: 'news', label: t('news.feedNewsColumn') },
    { kind: 'preprint', label: t('news.feedPreprintsColumn') },
    { kind: 'journal_article', label: t('news.feedArticlesColumn') },
  ]
  const kinds: Record<Kind, string> = {
    news: t('news.kindNews'),
    preprint: t('news.kindPreprint'),
    journal_article: t('news.kindJournalArticle'),
  }

  return <Box component="section" aria-labelledby="news-feed-heading" sx={{ mb: 6 }}>
    <Box sx={{ mb: 2 }}>
      <Typography id="news-feed-heading" component="h2" variant="h2">{t('news.feedTitle')}</Typography>
      <Typography variant="body2" sx={{ mt: 0.5, color: 'text.secondary' }}>{t('news.feedSubtitle')}</Typography>
      <Typography variant="body2" sx={{ mt: 1, color: 'text.primary' }}>{t('news.autoCollected')}</Typography>
    </Box>
    <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: 'repeat(3, minmax(0, 1fr))' }, gap: 2 }}>
      {columns.map(column => <FeedColumn key={column.kind} {...column} onSelect={setSelectedItem} onSources={handleSources} />)}
    </Box>
    {sources.length > 0 && <Box component="details" sx={{ mt: 2, color: 'text.secondary', fontSize: 13 }}>
      <Box component="summary" sx={{ cursor: 'pointer', py: 1 }}>{t('news.sourceStatusTitle')}
        {sources.some(sourceNeedsAttention) ? t('news.sourcesNeedAttention') : ''}
      </Box>
      <Stack gap={1} sx={{ pt: 1 }}>
        {sources.map(state => <Box key={state.source}>
          <Typography variant="body2">{t('news.sourceItem', { name: sourceNames[state.source] || state.source, status: sourceStatus(t, state) })}{state.error_code ? t('news.errorCode', { code: state.error_code }) : ''}</Typography>
          <Typography variant="body2">{t('news.lastSuccess', { time: timestamp(t, lang, state.last_success_at) })}</Typography>
        </Box>)}
        <Typography variant="body2">{t('news.physorgNote')}</Typography>
      </Stack>
    </Box>}

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
            label={selectedItem.content_type === 'research_report' ? t('news.kindResearchReport') : kinds[selectedItem.kind]}
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
            <strong>{t('news.authorLabel')}</strong>{selectedItem.authors.slice(0, 10).join(lang === 'zh' ? '、' : ', ')}{selectedItem.authors.length > 10 ? t('news.etAl') : ''}
            {selectedItem.journal && <><br /><strong>{t('news.journalLabel')}</strong>{selectedItem.journal}</>}
          </Typography>}

          <Stack direction="row" useFlexGap flexWrap="wrap" gap={1.5} sx={{ mb: 3 }}>
            <Typography variant="body2" color="text.secondary"><strong>{t('news.sourceLabel')}</strong>{sourceNames[selectedItem.discovery_source] || sourceNames[selectedItem.source] || selectedItem.source}</Typography>
            {selectedItem.original_source && <Typography variant="body2" color="text.secondary"><strong>{t('news.originalSourceLabel')}</strong>{sourceNames[selectedItem.original_source] || selectedItem.original_source}</Typography>}
            {selectedItem.relevance_evidence && <Typography variant="body2" color="text.secondary"><strong>{t('news.relevanceLabel')}</strong>{selectedItem.relevance_evidence}</Typography>}
            <Typography variant="body2" color="text.secondary"><strong>{t('news.publishedLabel')}</strong>{dateLabel(t, selectedItem.published_at, selectedItem.date_precision)}</Typography>
            {selectedItem.kind === 'preprint' && selectedItem.version > 0 && <Typography variant="body2" color="text.secondary"><strong>{t('news.versionLabel')}</strong>v{selectedItem.version}</Typography>}
            <Typography variant="body2" color="text.secondary"><strong>{t('news.collectedLabel')}</strong>{dateLabel(t, selectedItem.last_seen_at)}</Typography>
          </Stack>

          {selectedItem.summary && <>
            <Typography variant="body1" fontWeight={600} sx={{ mb: 1.5 }}>{t('news.summaryLabel')}</Typography>
            <Typography variant="body2" sx={{ lineHeight: 1.8, whiteSpace: 'pre-line', mb: 3, color: 'text.primary' }}>
              {selectedItem.summary}
            </Typography>
            {selectedItem.summary_source && <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary', fontStyle: 'italic' }}>
              {t('news.summarySourceLabel')}{sourceNames[selectedItem.summary_source]}
            </Typography>}
          </>}

          {selectedItem.doi && <Typography variant="body2" sx={{ mb: 2, color: 'text.secondary' }}>
            <strong>{t('news.doiLabel')}</strong>{selectedItem.doi}
          </Typography>}

          {selectedItem.links.filter(link => safeNewsLink(link.url)).length > 0 && <>
            <Typography variant="body1" fontWeight={600} sx={{ mb: 1.5 }}>{t('news.originalLinks')}</Typography>
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
  const { t } = useLanguage()
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
    <Typography id="manual-news-heading" component="h2" variant="h2" sx={{ mb: 2 }}>{t('news.manualTitle')}</Typography>
    {loading ? <Typography role="status" variant="body2">{t('news.loadingManual')}</Typography> : error ?
      <Alert severity="error" action={<Button color="inherit" onClick={() => setRevision(v => v + 1)}>{t('news.retryManual')}</Button>}>{t('news.manualLoadFailed')}</Alert> :
      items.length === 0 ? <Typography variant="body2" color="text.secondary">{t('news.manualEmpty')}</Typography> :
      <Stack gap={2}>{items.map(item => <Box key={item.id} sx={{ borderBottom: '1px solid', borderColor: 'divider', pb: 2, overflowWrap: 'anywhere' }}>
        <Typography variant="body2" color="text.secondary">{item.event_date}</Typography>
        <Typography component="h3" variant="h3" sx={{ mt: 1 }}>
          {safeNewsLink(item.link) ? <Link href={safeNewsLink(item.link)} target="_blank" rel="noopener noreferrer">{item.title}</Link> : item.title}
        </Typography>
        <Typography variant="body2" sx={{ mt: 1, lineHeight: 1.8 }}>{item.summary}</Typography>
      </Box>)}</Stack>}
  </Box>
}
