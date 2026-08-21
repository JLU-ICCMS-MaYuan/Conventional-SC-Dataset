import React, { useEffect, useState } from 'react'
import { Accordion, AccordionDetails, AccordionSummary, Alert, Box, Chip, Typography } from '@mui/material'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { api } from '../lib/api'
import { unwrapData } from '../lib/paperProcessing'

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
  chunks: ChunkDetail[]
  summary: { status: string; completed: number; total: number }
  next_poll_ms: number | null
}

const UploadParsingDetail: React.FC<{ taskId: string }> = ({ taskId }) => {
  const [detail, setDetail] = useState<ParsingDetail | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let stopped = false
    let timer: number | undefined
    const poll = async () => {
      try {
        const response = await api.get<{ ok: boolean; data: ParsingDetail }>(`/api/upload-tasks/${taskId}/parsing`)
        if (stopped) return
        const value = unwrapData(response)
        setDetail(value); setError('')
        if (value.next_poll_ms) timer = window.setTimeout(poll, value.next_poll_ms)
      } catch (reason: any) {
        if (!stopped) { setError(reason.message || '解析详情加载失败'); timer = window.setTimeout(poll, 2000) }
      }
    }
    void poll()
    return () => { stopped = true; if (timer) window.clearTimeout(timer) }
  }, [taskId])

  if (error) return <Alert severity="warning" sx={{ mt: 2 }}>{error}</Alert>
  if (!detail || detail.chunks.length === 0) return null
  return <Box sx={{ mt: 2 }}>
    <Typography variant="subtitle2" fontWeight={700}>实时解析详情 · {detail.summary.completed}/{detail.summary.total}</Typography>
    {detail.chunks.map(chunk => <Accordion key={chunk.chunk_id} disableGutters elevation={0}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0 }}>
          <Chip size="small" label={chunk.status} color={chunk.status === 'failed' ? 'error' : chunk.status === 'completed' ? 'success' : 'default'} />
          <Typography variant="body2" noWrap>{chunk.filename} · {chunk.section || '正文'}</Typography>
          {chunk.page_start && <Typography variant="caption" color="text.secondary">第 {chunk.page_start}{chunk.page_end && chunk.page_end !== chunk.page_start ? `–${chunk.page_end}` : ''} 页</Typography>}
        </Box>
      </AccordionSummary>
      <AccordionDetails>
        {chunk.error && <Alert severity="error">{chunk.error}</Alert>}
        {chunk.result && <pre style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere', margin: 0 }}>{JSON.stringify(chunk.result, null, 2)}</pre>}
      </AccordionDetails>
    </Accordion>)}
  </Box>
}

export default UploadParsingDetail
