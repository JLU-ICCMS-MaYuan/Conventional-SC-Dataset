import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Typography } from '@mui/material'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp'
import { api } from '../lib/api'
import { UploadTaskState, unwrapData } from '../lib/paperProcessing'
import { useLanguage } from '../context/LanguageContext'


// 倒计时归零时的显示文案由 zh 字典 upload.cleanupPending 提供；源码中的「等待清理」
// 字面量是前端契约测试 tests/01_decentralized_uploading/test_issue24_persistence_and_ui.py
// 的检索锚点，改动需同步该测试。
function countdownParts(
  cleanupAt: number | null | undefined,
  now: number,
): { hours: number; minutes: number; seconds: number; pending: boolean } | null {
  if (!cleanupAt) return null
  const seconds = Math.max(0, cleanupAt - Math.floor(now / 1000))
  if (seconds === 0) return { hours: 0, minutes: 0, seconds: 0, pending: true }
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  return { hours, minutes, seconds: rest, pending: false }
}

// 任务状态 → upload.status.<value> 字典键（UploadTaskStatus 的可显示子集）
const STATUS_KEYS = [
  'uploading', 'queued', 'extracting', 'reading', 'summarizing', 'ready',
  'submitting', 'failed', 'duplicate', 'cancelling', 'cancelled',
] as const

interface Props {
  refreshKey?: number
  activeTaskId?: string | null
  onToggle: (task: UploadTaskState) => void
}

const UploadTaskCenter: React.FC<Props> = ({ refreshKey, activeTaskId, onToggle }) => {
  const { t } = useLanguage()
  const [tasks, setTasks] = useState<UploadTaskState[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [now, setNow] = useState(Date.now())

  const load = async () => {
    setLoading(true)
    try {
      const response = await api.get<{ ok: boolean; data: UploadTaskState[] }>('/api/upload-tasks')
      setTasks(unwrapData(response))
      setError('')
    } catch (reason: any) {
      setError(reason.message || t('upload.recordsLoadFailed'))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void load() }, [refreshKey])
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [])

  const activeCount = useMemo(() => tasks.filter(task => task.status !== 'submitted').length, [tasks])

  const cancel = async (event: React.MouseEvent, taskId: string) => {
    event.stopPropagation()
    if (!window.confirm(t('upload.cancelTaskConfirm'))) return
    await api.post(`/api/upload-tasks/${taskId}/cancel`)
    await load()
  }

  const remove = async (event: React.MouseEvent, taskId: string) => {
    event.stopPropagation()
    await api.del(`/api/upload-tasks/${taskId}`)
    await load()
  }

  return (
    <Box sx={{ mb: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
        <Typography variant="h6" fontWeight={700}>{t('upload.recordsTitle')} <Chip size="small" label={`${activeCount}/100`} /></Typography>
        <Button size="small" onClick={() => void load()} disabled={loading}>{t('common.refresh')}</Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {loading && tasks.length === 0 && <CircularProgress size={22} />}
      {tasks.length === 0 && !loading && <Typography color="text.secondary">{t('upload.noActiveTasks')}</Typography>}
      <Box sx={{ display: 'grid', gap: 1 }}>
        {tasks.map(task => {
          const remaining = countdownParts(task.cleanup_at, now)
          const selected = task.task_id === activeTaskId
          const running = ['uploading', 'queued', 'extracting', 'reading', 'summarizing', 'submitting', 'cancelling']
            .includes(task.status || '')
          const statusText = task.status && (STATUS_KEYS as readonly string[]).includes(task.status)
            ? t('upload.status.' + task.status)
            : task.stage || ''
          return (
            <Card key={task.task_id} variant="outlined" sx={{ borderColor: selected ? 'primary.main' : 'divider', bgcolor: selected ? 'action.selected' : 'background.paper' }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: { xs: 'wrap', sm: 'nowrap' } }}>
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography fontWeight={700} noWrap>{task.filename || task.files?.[0]?.original_filename || task.task_id}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {statusText}
                    {task.total_chunks > 0 ? t('upload.chunkCount', { done: task.completed_chunks, total: task.total_chunks }) : ''}
                  </Typography>
                  {remaining && <Typography variant="caption" color={remaining.pending ? 'error' : 'warning.main'} sx={{ ml: 1 }}>
                    {remaining.pending
                      ? t('upload.cleanupPending')
                      : remaining.hours > 0
                        ? t('upload.cleanupHours', { hours: remaining.hours, minutes: remaining.minutes })
                        : t('upload.cleanupMinutes', { minutes: remaining.minutes, seconds: remaining.seconds })}
                  </Typography>}
                </Box>
                <Button
                  size="small"
                  variant={selected ? 'contained' : 'text'}
                  startIcon={selected ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                  aria-label={t('upload.toggleDetailAria', {
                    action: selected ? t('upload.collapse') : t('upload.view'),
                    filename: task.filename || task.files?.[0]?.original_filename || task.task_id,
                  })}
                  onClick={() => onToggle(task)}
                >{selected ? t('upload.collapseDetail') : t('upload.viewDetail')}</Button>
                {running
                  ? <Button size="small" color="warning" onClick={event => void cancel(event, task.task_id)}>{t('upload.cancel')}</Button>
                  : ['failed', 'duplicate', 'cancelled'].includes(task.status || '')
                    ? <Button size="small" color="error" onClick={event => void remove(event, task.task_id)}>{t('upload.clean')}</Button>
                    : null}
              </CardContent>
            </Card>
          )
        })}
      </Box>
    </Box>
  )
}

export default UploadTaskCenter
