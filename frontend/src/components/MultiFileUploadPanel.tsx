import React, { useRef, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, LinearProgress, MenuItem, Select, Typography } from '@mui/material'
import { getStoredToken } from '../context/AuthContext'
import { api } from '../lib/api'
import { UploadTaskState, unwrapData } from '../lib/paperProcessing'

const MAX_BYTES = 50 * 1024 * 1024
type Role = 'main' | 'supplementary' | 'attachment'
interface Selected { clientId: string; file: File; role: Role; progress: number; status: string }

interface Props { onCreated: (task: UploadTaskState) => void }

function uploadOne(taskId: string, item: Selected, progress: (value: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `/api/upload-tasks/${taskId}/files/${item.clientId}`)
    const token = getStoredToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = event => event.lengthComputable && progress(Math.round(event.loaded / event.total * 100))
    xhr.onerror = () => reject(new Error('网络错误，上传失败'))
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else {
        try { reject(new Error(JSON.parse(xhr.responseText)?.detail?.message || '上传失败')) }
        catch { reject(new Error(xhr.status === 413 ? '文件超过 50 MB 限制' : `上传失败（HTTP ${xhr.status}）`)) }
      }
    }
    const body = new FormData()
    body.append('file', item.file)
    xhr.send(body)
  })
}

const MultiFileUploadPanel: React.FC<Props> = ({ onCreated }) => {
  const input = useRef<HTMLInputElement>(null)
  const [items, setItems] = useState<Selected[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const choose = (files: FileList | null) => {
    if (!files) return
    const additions = Array.from(files).map((file, index): Selected => ({
      clientId: crypto.randomUUID().replaceAll('-', ''), file,
      role: items.length === 0 && index === 0 ? 'main' : 'attachment', progress: 0, status: '等待上传',
    }))
    const invalid = additions.find(item => !/\.(pdf|txt|md)$/i.test(item.file.name) || item.file.size > MAX_BYTES)
    if (invalid) { setError(`${invalid.file.name} 类型不支持或超过 50 MB`); return }
    setItems(current => [...current, ...additions])
    setError('')
  }

  const setRole = (clientId: string, role: Role) => {
    setItems(current => current.map(item => item.clientId === clientId ? { ...item, role } : item))
  }

  const start = async () => {
    if (items.filter(item => item.role === 'main').length !== 1) { setError('必须恰好选择一个正文'); return }
    setBusy(true); setError('')
    try {
      const created = await api.post<{ ok: boolean; data: UploadTaskState }>('/api/upload-tasks', {
        files: items.map(item => ({
          client_id: item.clientId, role: item.role, filename: item.file.name,
          size: item.file.size, media_type: item.file.type || null,
        })),
      })
      const task = unwrapData(created)
      const serverFiles = task.files || []
      const queue = items.map((item, index) => ({
        ...item,
        clientId: serverFiles[index]?.file_id || '',
      }))
      let cursor = 0
      const worker = async () => {
        while (cursor < queue.length) {
          const item = queue[cursor++]
          await uploadOne(task.task_id, item, value => setItems(current => current.map(existing =>
            existing.file === item.file ? { ...existing, progress: value, status: '上传中' } : existing)))
          setItems(current => current.map(existing => existing.file === item.file ? { ...existing, progress: 100, status: '完成' } : existing))
        }
      }
      await Promise.all(Array.from({ length: Math.min(3, queue.length) }, worker))
      const detail = await api.get<{ ok: boolean; data: UploadTaskState }>(`/api/upload-tasks/${task.task_id}`)
      onCreated(unwrapData(detail))
      setItems([])
    } catch (reason: any) {
      setError(reason.message || '批量上传失败')
    } finally { setBusy(false) }
  }

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" fontWeight={700}>新建论文上传任务</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>一个正文，可添加补充材料或附件；PDF/TXT/MD，每个最大 50 MB，同时上传最多 3 个。</Typography>
        {items.map(item => <Box key={item.clientId} sx={{ display: 'grid', gridTemplateColumns: '1fr 150px', gap: 1, mb: 1 }}>
          <Box><Typography noWrap>{item.file.name}</Typography><LinearProgress variant="determinate" value={item.progress} /></Box>
          <Select size="small" value={item.role} disabled={busy} onChange={event => setRole(item.clientId, event.target.value as Role)}>
            <MenuItem value="main">正文</MenuItem><MenuItem value="supplementary">补充材料</MenuItem><MenuItem value="attachment">附件</MenuItem>
          </Select>
        </Box>)}
        {error && <Alert severity="error" sx={{ my: 1 }}>{error}</Alert>}
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <Button variant="outlined" onClick={() => input.current?.click()} disabled={busy}>选择文件</Button>
          <Button variant="contained" onClick={() => void start()} disabled={busy || items.length === 0}>{busy ? '上传中…' : '开始上传并解析'}</Button>
        </Box>
        <input ref={input} type="file" hidden multiple accept=".pdf,.txt,.md" onChange={event => choose(event.target.files)} />
      </CardContent>
    </Card>
  )
}

export default MultiFileUploadPanel
