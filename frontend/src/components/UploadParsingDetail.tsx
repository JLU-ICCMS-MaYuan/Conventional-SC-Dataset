import React, { useEffect, useState } from 'react'
import {
  Accordion, AccordionDetails, AccordionSummary, Alert, Box, Button, Chip,
  LinearProgress, Tab, Tabs, Typography,
} from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import RefreshIcon from '@mui/icons-material/Refresh'
import { api } from '../lib/api'
import { PROCESSING_STAGES, UploadDraft, unwrapData } from '../lib/paperProcessing'
import { useLanguage } from '../context/LanguageContext'
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

interface Props {
  taskId: string
  onSubmitted?: (paperId: number) => void
}

const UploadParsingDetail: React.FC<Props> = ({ taskId, onSubmitted = () => undefined }) => {
  const { t } = useLanguage()
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
          setError(reason.message || t('upload.detailLoadFailed'))
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
      setError(reason.message || t('upload.operationFailed'))
    } finally {
      setActionPending(false)
    }
  }

  // 处理阶段标签统一走 upload.step.<stage.key>，与处理流程组件保持一致
  const failedStageLabel = (key: string | null | undefined): string => {
    const stage = key ? PROCESSING_STAGES.find(item => item.key === key) : undefined
    return stage ? t('upload.step.' + stage.key) : (key || '')
  }

  const statusNote = (value: ParsingDetail): string => {
    switch (value.status) {
      case 'summarizing':
        return t('upload.summarizingNote')
      case 'reading':
        return t('upload.readingNote', { completed: value.summary.completed, total: value.summary.total })
      case 'extracting':
        return t('upload.extractingNote')
      case 'queued':
        return t('upload.queuedNote')
      default:
        return t('upload.defaultNote')
    }
  }

  return (
    <Box sx={{ mt: 2 }}>
      {error && (
        <Alert severity="warning" sx={{ mb: 1.5 }} action={
          <Button color="inherit" size="small" startIcon={<RefreshIcon />} onClick={() => setReload(value => value + 1)}>
            {t('common.retry')}
          </Button>
        }>{error}</Alert>
      )}
      {!detail && !error && <LinearProgress aria-label={t('upload.loadingDetailAria')} />}
      {detail && (
        <>
          {detail.status === 'failed' && (
            <Alert
              severity="error"
              sx={{ mb: 1.5 }}
              action={
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <Button color="inherit" size="small" disabled={actionPending} onClick={() => void runAction('retry')}>
                    {t('upload.retryParse')}
                  </Button>
                  <Button color="inherit" size="small" disabled={actionPending} onClick={() => void runAction('manual')}>
                    {t('upload.manualFill')}
                  </Button>
                </Box>
              }
            >
              {t('upload.parseFailed', {
                stage: detail.failed_stage
                  ? t('upload.stageSuffix', { label: failedStageLabel(detail.failed_stage) })
                  : '',
                error: detail.processing_error || t('upload.unknownError'),
              })}
            </Alert>
          )}
          <Tabs
            value={tab}
            onChange={(_, value) => setTab(value)}
            aria-label={t('upload.parsingDetailAria')}
            sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
          >
            <Tab label={t('upload.tabAiForm')} />
            <Tab label={t('upload.tabChunks')} />
          </Tabs>

          {tab === 0 && (
            <Box role="tabpanel" aria-label={t('upload.tabAiForm')}>
              {detail.status === 'ready' ? (
                <UploadTaskEditor taskId={taskId} onSubmitted={onSubmitted} />
              ) : detail.status === 'failed' ? (
                <Typography variant="body2" color="text.secondary">
                  {t('upload.parseIncomplete')}
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
            <Box role="tabpanel" aria-label={t('upload.tabChunks')}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                {t('upload.chunkProgressTitle', { completed: detail.summary.completed, total: detail.summary.total })}
              </Typography>
              {detail.chunks.length === 0 && (
                <Typography variant="body2" color="text.secondary">{t('upload.noChunksYet')}</Typography>
              )}
              {detail.chunks.map(chunk => (
                <Accordion key={chunk.chunk_id} disableGutters elevation={0} sx={{ borderBottom: 1, borderColor: 'divider' }}>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0, flexWrap: 'wrap' }}>
                      <Chip size="small" label={chunk.status} color={chunk.status === 'failed' ? 'error' : chunk.status === 'completed' ? 'success' : 'default'} />
                      <Typography variant="body2">{chunk.filename} · {chunk.section || t('upload.bodyText')}</Typography>
                      {chunk.page_start && <Typography variant="caption" color="text.secondary">{t('upload.pageRange', {
                        start: chunk.page_start,
                        end: chunk.page_end && chunk.page_end !== chunk.page_start ? `-${chunk.page_end}` : '',
                      })}</Typography>}
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
