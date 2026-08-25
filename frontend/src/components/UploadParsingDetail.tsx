import React, { useEffect, useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip,
  LinearProgress, Tab, Tabs, Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RefreshIcon from '@mui/icons-material/Refresh'
import { api } from '../lib/api'
import { UploadDraft, unwrapData } from '../lib/paperProcessing'
import UploadTaskEditor from './UploadTaskEditor'

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
  processing_error?: string | null
  failed_stage?: string | null
  files?: Array<{
    file_id: string
    role: string
    original_filename: string
    extraction_status?: string
    error?: string | null
  }>
  chunks: ChunkDetail[]
  partial_draft?: UploadDraft | null
  summary: { status: string; completed: number; total: number }
  next_poll_ms: number | null
}

const FAILED_STAGE_LABEL: Record<string, string> = {
  extracting: '提取论文正文',
  reading: 'AI 分段阅读',
  summarizing: 'AI 汇总草稿',
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
  const [actionPending, setActionPending] = useState(false)

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

  const runAction = async (path: 'retry' | 'manual') => {
    setActionPending(true)
    try {
      await api.post(`/api/rag/upload-tasks/${taskId}/${path}`)
      setReload(value => value + 1)
    } catch (reason: any) {
      setError(reason.message || '操作失败')
    } finally {
      setActionPending(false)
    }
  }

  const statusNote = (value: ParsingDetail): string => {
    switch (value.status) {
      case 'summarizing':
        return 'AI 正在汇总全文草稿，表单内容实时更新；生成完成后即可校对。'
      case 'reading':
        return `AI 分段阅读中 ${value.summary.completed}/${value.summary.total}，字段随分段完成逐步点亮。`
      case 'extracting':
        return '正在提取论文正文，完成后逐段解析。'
      case 'queued':
        return '排队等待解析…'
      default:
        return 'AI 正在生成草稿，内容与最终校对表单一致。'
    }
  }

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
          {detail.status === 'failed' && (
            <Alert
              severity="error"
              sx={{ mb: 1.5 }}
              action={
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button color="inherit" size="small" disabled={actionPending} onClick={() => void runAction('retry')}>
                    重新解析
                  </Button>
                  <Button color="inherit" size="small" disabled={actionPending} onClick={() => void runAction('manual')}>
                    手动填写
                  </Button>
                </Box>
              }
            >
              解析失败{detail.failed_stage ? `（${FAILED_STAGE_LABEL[detail.failed_stage] || detail.failed_stage}阶段）` : ''}
              ：{detail.processing_error || '未知错误'}。可重新解析（已完成的分段会复用缓存），或改为手动填写。
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
              ) : detail.status === 'failed' ? (
                <Typography variant="body2" color="text.secondary">
                  本次解析未完成，请重新解析或改为手动填写。
                </Typography>
              ) : (
                <UploadTaskEditor
                  taskId={taskId}
                  onSubmitted={onSubmitted}
                  readOnly
                  draftOverride={detail.partial_draft ?? null}
                  statusNote={statusNote(detail)}
                />
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
