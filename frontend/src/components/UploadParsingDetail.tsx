import React, { useEffect, useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip,
  LinearProgress, Tab, Tabs, Typography,
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
  state: 'filled' | 'waiting' | 'conflict'
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
}

const roleLabel: Record<string, string> = {
  main: '正文', supplementary: '补充材料', attachment: '附件',
}

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
                      解析结果会持续合并；冲突内容不会自动覆盖。
                    </Typography>
                  </Box>
                  {!preview?.groups.length && (
                    <Typography variant="body2" color="text.secondary">字段正在等待首批解析结果。</Typography>
                  )}
                  {preview?.groups.map(group => (
                <Box key={group.id} component="section" sx={{ mb: 2.5 }}>
                  <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>{group.label}</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 1 }}>
                    {group.fields.map(field => (
                      <Box key={field.path} sx={{ p: 1.5, border: 1, borderColor: field.state === 'conflict' ? 'warning.main' : 'divider', borderRadius: 1 }}>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', gap: 1, alignItems: 'center', mb: 0.75 }}>
                          <Typography variant="body2" fontWeight={700}>{field.label}</Typography>
                          <Chip
                            size="small"
                            label={stateLabel[field.state]}
                            color={field.state === 'conflict' ? 'warning' : field.state === 'filled' ? 'success' : 'default'}
                            variant={field.state === 'waiting' ? 'outlined' : 'filled'}
                          />
                        </Box>
                        {field.candidates.length === 0 && <Typography variant="body2" color="text.secondary">等待解析</Typography>}
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
