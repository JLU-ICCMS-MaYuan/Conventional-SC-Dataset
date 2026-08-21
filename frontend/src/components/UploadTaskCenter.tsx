import React, { useEffect, useMemo, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Typography } from '@mui/material'
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown'
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp'
import { api } from '../lib/api'
import { UploadTaskState, unwrapData } from '../lib/paperProcessing'


function countdown(cleanupAt: number | null | undefined, now: number): string | null {
  if (!cleanupAt) return null
  const seconds = Math.max(0, cleanupAt - Math.floor(now / 1000))
  if (seconds === 0) return '等待清理'
  const hours = Math.floor(seconds / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  const rest = seconds % 60
  return hours > 0 ? `${hours}小时${minutes}分后删除` : `${minutes}分${rest}秒后删除`
}

const statusLabel: Record<string, string> = {
  uploading: '上传中', queued: '等待解析', extracting: '提取正文', reading: '分段阅读',
  summarizing: '全文汇总', ready: '等待校对', submitting: '提交中', failed: '解析失败',
  duplicate: '发现重复', cancelling: '正在取消', cancelled: '已取消',
}

interface Props {
  refreshKey?: number
  activeTaskId?: string | null
  onToggle: (task: UploadTaskState) => void
}

const UploadTaskCenter: React.FC<Props> = ({ refreshKey, activeTaskId, onToggle }) => {
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
      setError(reason.message || '上传解析记录加载失败')
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
    if (!window.confirm('确定取消这个任务吗？当前 LLM 请求可能需要等待完成或超时。')) return
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
        <Typography variant="h6" fontWeight={700}>上传解析记录 <Chip size="small" label={`${activeCount}/100`} /></Typography>
        <Button size="small" onClick={() => void load()} disabled={loading}>刷新</Button>
      </Box>
      {error && <Alert severity="error" sx={{ mb: 1 }}>{error}</Alert>}
      {loading && tasks.length === 0 && <CircularProgress size={22} />}
      {tasks.length === 0 && !loading && <Typography color="text.secondary">暂无活动任务</Typography>}
      <Box sx={{ display: 'grid', gap: 1 }}>
        {tasks.map(task => {
          const remaining = countdown(task.cleanup_at, now)
          const selected = task.task_id === activeTaskId
          const running = ['uploading', 'queued', 'extracting', 'reading', 'summarizing', 'submitting', 'cancelling']
            .includes(task.status || '')
          return (
            <Card key={task.task_id} variant="outlined" sx={{ borderColor: selected ? 'primary.main' : 'divider', bgcolor: selected ? 'action.selected' : 'background.paper' }}>
              <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 }, display: 'flex', gap: 1.5, alignItems: 'center', flexWrap: { xs: 'wrap', sm: 'nowrap' } }}>
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography fontWeight={700} noWrap>{task.filename || task.files?.[0]?.original_filename || task.task_id}</Typography>
                  <Typography variant="caption" color="text.secondary">
                    {statusLabel[task.status || ''] || task.stage}
                    {task.total_chunks > 0 ? ` · ${task.completed_chunks}/${task.total_chunks} 段` : ''}
                  </Typography>
                  {remaining && <Typography variant="caption" color={remaining === '等待清理' ? 'error' : 'warning.main'} sx={{ ml: 1 }}>{remaining}</Typography>}
                </Box>
                <Button
                  size="small"
                  variant={selected ? 'contained' : 'text'}
                  startIcon={selected ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                  aria-label={`${selected ? '收起' : '查看'} ${task.filename || task.files?.[0]?.original_filename || task.task_id} 的解析详情`}
                  onClick={() => onToggle(task)}
                >{selected ? '收起解析' : '查看解析'}</Button>
                {running
                  ? <Button size="small" color="warning" onClick={event => void cancel(event, task.task_id)}>取消</Button>
                  : ['failed', 'duplicate', 'cancelled'].includes(task.status || '')
                    ? <Button size="small" color="error" onClick={event => void remove(event, task.task_id)}>清理</Button>
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
