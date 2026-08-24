import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip, Collapse,
  LinearProgress, Tab, Tabs, Typography, useMediaQuery,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RefreshIcon from '@mui/icons-material/Refresh'
import { api } from '../lib/api'
import { unwrapData } from '../lib/paperProcessing'
import UploadTaskEditor from './UploadTaskEditor'

interface PreviewSource {
  filename?: string
  file_role?: string
  section?: string
  page_start?: number | null
  page_end?: number | null
  quote?: string
}

interface PreviewCandidate {
  value: unknown
  sources: PreviewSource[]
}

interface PreviewField {
  path: string
  label: string
  state: 'filled' | 'waiting' | 'conflict' | 'pending_summary'
  candidates: PreviewCandidate[]
}

interface PreviewGroup {
  id: string
  label: string
  fields: PreviewField[]
}

interface ChunkDetail {
  chunk_id: string
  filename?: string
  file_role?: string
  section?: string
  page_start?: number | null
  page_end?: number | null
  status: string
  error?: string | null
  result?: Record<string, unknown>
}

interface ParsingDetail {
  status: string
  stage: string
  files?: Array<{
    file_id: string
    role: string
    original_filename: string
    extraction_status?: string
    error?: string | null
  }>
  chunks: ChunkDetail[]
  form_preview?: { status: string; read_only: boolean; groups: PreviewGroup[] }
  summary: { status: string; completed: number; total: number }
  next_poll_ms: number | null
}

const stateLabel: Record<PreviewField['state'], string> = {
  filled: '已填写',
  waiting: '等待解析',
  conflict: '有冲突',
  pending_summary: '候选尚未汇总',
}

const roleLabel: Record<string, string> = {
  main: '正文', supplementary: '补充材料', attachment: '附件',
}

const COLLAPSED_PREVIEW_HEIGHT = 176

function displayValue(value: unknown): string {
  if (value == null || value === '') return '等待解析'
  if (Array.isArray(value)) return value.map(displayValue).join('、')
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function sourceLabel(source: PreviewSource): string {
  const page = source.page_start
    ? `第 ${source.page_start}${source.page_end && source.page_end !== source.page_start ? `-${source.page_end}` : ''} 页`
    : ''
  return [source.filename, roleLabel[source.file_role || ''] || source.file_role, source.section, page]
    .filter(Boolean).join(' · ')
}

const PreviewFieldCard: React.FC<{ field: PreviewField }> = ({ field }) => {
  const contentId = useId()
  const contentRef = useRef<HTMLDivElement>(null)
  const overflowRef = useRef(false)
  const [isOverflowing, setIsOverflowing] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
  const hasCandidates = field.candidates.length > 0

  const measureOverflow = useCallback(() => {
    const nextOverflowing = hasCandidates
      && (contentRef.current?.scrollHeight || 0) > COLLAPSED_PREVIEW_HEIGHT
    if (nextOverflowing === overflowRef.current) return

    overflowRef.current = nextOverflowing
    setIsOverflowing(nextOverflowing)
    setExpanded(false)
  }, [hasCandidates])

  useLayoutEffect(() => {
    measureOverflow()
  }, [field.candidates, measureOverflow])

  useEffect(() => {
    const content = contentRef.current
    if (!content) return undefined

    window.addEventListener('resize', measureOverflow)
    let observer: ResizeObserver | undefined
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(measureOverflow)
      observer.observe(content)
    }

    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', measureOverflow)
    }
  }, [measureOverflow])

  return (
    <Box sx={{
      p: 1.5, border: 1,
      borderColor: field.state === 'conflict' ? 'warning.main' : field.state === 'pending_summary' ? 'info.main' : 'divider',
      borderRadius: 1,
      minWidth: 0,
    }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', mb: 0.75 }}>
        <Typography variant="body2" fontWeight={700}>{field.label}</Typography>
        <Chip
          size="small"
          label={stateLabel[field.state]}
          color={field.state === 'conflict' ? 'warning' : field.state === 'filled' ? 'success' : field.state === 'pending_summary' ? 'info' : 'default'}
          variant={field.state === 'waiting' ? 'outlined' : 'filled'}
        />
      </Box>
      <Collapse
        in={!isOverflowing || expanded}
        collapsedSize={isOverflowing ? COLLAPSED_PREVIEW_HEIGHT : 0}
        timeout={prefersReducedMotion ? 0 : 180}
      >
        <Box id={contentId} ref={contentRef}>
          {field.candidates.length === 0 && (
            <Typography variant="body2" color="text.secondary">
              {field.state === 'pending_summary' ? '当前分段尚无法判断，等待全文汇总' : '等待解析'}
            </Typography>
          )}
          {field.candidates.map((candidate, index) => (
            <Box key={index} sx={{ '& + &': { mt: 1, pt: 1, borderTop: 1, borderColor: 'divider' } }}>
              <Typography component="pre" variant="body2" sx={{ m: 0, whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', fontFamily: 'inherit' }}>
                {displayValue(candidate.value)}
              </Typography>
              {candidate.sources.map((source, sourceIndex) => (
                <Box key={sourceIndex} sx={{ mt: 0.5 }}>
                  <Typography variant="caption" color="text.secondary" display="block">{sourceLabel(source) || '来源待确认'}</Typography>
                  {source.quote && <Typography variant="caption" color="text.secondary" display="block">“{source.quote}”</Typography>}
                </Box>
              ))}
            </Box>
          ))}
        </Box>
      </Collapse>
      {isOverflowing && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 0.5 }}>
          <Button
            size="small"
            onClick={() => setExpanded(value => !value)}
            aria-expanded={expanded}
            aria-controls={contentId}
            aria-label={`${expanded ? '收起' : '展开'} ${field.label}`}
            endIcon={<ExpandMoreIcon sx={{
              transform: expanded ? 'rotate(180deg)' : 'none',
              transition: prefersReducedMotion ? 'none' : 'transform 180ms ease',
            }} />}
          >
            {expanded ? '收起' : '展开'}
          </Button>
        </Box>
      )}
    </Box>
  )
}

interface Props {
  taskId: string
  onSubmitted?: (paperId: number) => void
}

const UploadParsingDetail: React.FC<Props> = ({ taskId, onSubmitted = () => undefined }) => {
  const [detail, setDetail] = useState<ParsingDetail | null>(null)
  const [error, setError] = useState('')
  const [tab, setTab] = useState(0)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    let stopped = false
    let timer: number | undefined
    const poll = async () => {
      try {
        const response = await api.get<{ ok: boolean; data: ParsingDetail }>(`/api/upload-tasks/${taskId}/parsing`)
        if (stopped) return
        const value = unwrapData(response)
        setDetail(value)
        setError('')
        if (value.next_poll_ms) timer = window.setTimeout(poll, value.next_poll_ms)
      } catch (reason: any) {
        if (!stopped) {
          setError(reason.message || '解析详情加载失败')
          timer = window.setTimeout(poll, 2000)
        }
      }
    }
    void poll()
    return () => { stopped = true; if (timer) window.clearTimeout(timer) }
  }, [taskId, reload])

  const preview = detail?.form_preview
  const extracting = detail && detail.chunks.length === 0 && !['ready', 'failed', 'duplicate', 'cancelled'].includes(detail.status)

  return (
    <Box sx={{ mt: 2 }}>
      {error && (
        <Alert severity="warning" sx={{ mb: 1.5 }} action={
          <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={() => setReload(value => value + 1)}>
            重试
          </Button>
        }>{error}</Alert>
      )}
      {!detail && !error && <LinearProgress aria-label="正在加载解析详情" />}
      {detail && (
        <>
          {extracting && (
            <Alert severity="info" sx={{ mb: 1.5 }}>
              正在提取正文，完成后会在这里逐段显示解析结果。
            </Alert>
          )}
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            aria-label="上传任务解析详情"
            sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
          >
            <Tab label="AI 临时表单" />
            <Tab label="分段解析与证据" />
          </Tabs>

          {tab === 0 && (
            <Box role="tabpanel" aria-label="AI 临时表单">
              {detail.status === 'ready' ? (
                <UploadTaskEditor taskId={taskId} onSubmitted={onSubmitted} />
              ) : (
                <>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2, flexWrap: 'wrap' }}>
                    <Typography variant="subtitle2" fontWeight={700}>AI 已填写内容</Typography>
                    <Chip size="small" label="解析中，只读" />
                    <Typography variant="caption" color="text.secondary">
                      分类候选将在全文汇总后形成草稿；元数据冲突不会自动覆盖。
                    </Typography>
                  </Box>
                  {!preview?.groups.length && (
                    <Typography variant="body2" color="text.secondary">字段正在等待首批解析结果。</Typography>
                  )}
                  {preview?.groups.map(group => (
                <Box key={group.id} component="section" sx={{ mb: 2.5 }}>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>{group.label}</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1, alignItems: 'start' }}>
                    {group.fields.map(field => (
                      <PreviewFieldCard key={`${taskId}:${field.path}`} field={field} />
                    ))}
                  </Box>
                </Box>
                  ))}
                </>
              )}
            </Box>
          )}

          {tab === 1 && (
            <Box role="tabpanel" aria-label="分段解析与证据">
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                分段进度 · {detail.summary.completed}/{detail.summary.total}
              </Typography>
              {detail.chunks.length === 0 && (
                <Typography variant="body2" color="text.secondary">尚未生成分段，正在等待正文提取完成。</Typography>
              )}
              {detail.chunks.map(chunk => (
                <Accordion key={chunk.chunk_id} disableGutters elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0, flexWrap: 'wrap' }}>
                      <Chip size="small" label={chunk.status} color={chunk.status === 'failed' ? 'error' : chunk.status === 'completed' ? 'success' : 'default'} />
                      <Typography variant="body2">{chunk.filename} · {chunk.section || '正文'}</Typography>
                      {chunk.page_start && <Typography variant="caption" color="text.secondary">第 {chunk.page_start}{chunk.page_end && chunk.page_end !== chunk.page_start ? `-${chunk.page_end}` : ''} 页</Typography>}
                    </Box>
                  </AccordionSummary>
                  <AccordionDetails>
                    {chunk.error && <Alert severity="error">{chunk.error}</Alert>}
                    {chunk.result && <Typography component="pre" variant="body2" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', m: 0 }}>{JSON.stringify(chunk.result, null, 2)}</Typography>}
                  </AccordionDetails>
                </Accordion>
              ))}
            </Box>
          )}
        </>
      )}
    </Box>
  )
}

export default UploadParsingDetail
