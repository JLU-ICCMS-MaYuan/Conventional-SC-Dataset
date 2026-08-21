import React, { useRef, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, IconButton, LinearProgress, MenuItem, Select, Tooltip, Typography } from '@mui/material'
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
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
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState('')

  const choose = (files: FileList | File[] | null) => {
    if (!files) return
    const signatures = new Set(items.map(item => `${item.file.name}:${item.file.size}:${item.file.lastModified}`))
    const rejected: string[] = []
    const accepted: File[] = []
    for (const file of Array.from(files)) {
      const signature = `${file.name}:${file.size}:${file.lastModified}`
      if (!/\.(pdf|txt|md)$/i.test(file.name)) rejected.push(`${file.name}：仅支持 PDF、TXT、MD`)
      else if (file.size > MAX_BYTES) rejected.push(`${file.name}：超过 50 MB`)
      else if (signatures.has(signature)) rejected.push(`${file.name}：已在当前列表中`)
      else { accepted.push(file); signatures.add(signature) }
    }
    const hasMain = items.some(item => item.role === 'main')
    const additions = accepted.map((file, index): Selected => ({
      clientId: crypto.randomUUID().replaceAll('-', ''), file,
      role: !hasMain && index === 0 ? 'main' : 'attachment', progress: 0, status: '等待上传',
    }))
    if (additions.length) setItems(current => [...current, ...additions])
    setError(rejected.join('；'))
  }

  const setRole = (clientId: string, role: Role) => {
    setItems(current => current.map(item => item.clientId === clientId ? { ...item, role } : item))
  }

  const remove = (clientId: string) => {
    setItems(current => current.filter(item => item.clientId !== clientId))
  }

  const clear = () => {
    if (!items.length || !window.confirm('清空尚未上传的本地文件列表？后台任务不会受到影响。')) return
    setItems([])
    setError('')
    if (input.current) input.current.value = ''
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
        <Typography variant="body2" color="text.secondary">一个正文，可添加补充材料或附件；每组文件共同填写一张论文表单。</Typography>
        <Box
          aria-label="拖拽或选择论文文件"
          onClick={() => !busy && input.current?.click()}
          onDragOver={event => { event.preventDefault(); if (!busy) setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={event => {
            event.preventDefault()
            setDragOver(false)
            if (!busy) choose(event.dataTransfer.files)
          }}
          sx={{
            mt: 2, mb: items.length ? 2 : 0, minHeight: items.length ? 88 : 116,
            border: '2px dashed', borderColor: dragOver ? 'primary.main' : 'divider', borderRadius: 2,
            bgcolor: dragOver ? 'primary.50' : 'background.default', cursor: busy ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5,
            transition: 'border-color 160ms ease-out, background-color 160ms ease-out',
          }}
        >
          <CloudUploadOutlinedIcon color="primary" />
          <Box>
            <Typography fontWeight={700}>拖拽文件到这里，或点击选择</Typography>
            <Typography variant="caption" color="text.secondary">PDF、TXT、MD · 每个最大 50 MB · 同时上传最多 3 个</Typography>
          </Box>
        </Box>
        {items.map(item => <Box key={item.clientId} sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr) 112px 40px', sm: 'minmax(0, 1fr) 150px 40px' }, gap: 1, mb: 1, alignItems: 'center' }}>
          <Box sx={{ minWidth: 0 }}><Typography noWrap>{item.file.name}</Typography><LinearProgress variant="determinate" value={item.progress} /></Box>
          <Select size="small" value={item.role} disabled={busy} onChange={event => setRole(item.clientId, event.target.value as Role)}>
            <MenuItem value="main">正文</MenuItem><MenuItem value="supplementary">补充材料</MenuItem><MenuItem value="attachment">附件</MenuItem>
          </Select>
          <Tooltip title="移除文件"><span><IconButton aria-label={`移除 ${item.file.name}`} size="small" disabled={busy} onClick={() => remove(item.clientId)}><DeleteOutlineIcon fontSize="small" /></IconButton></span></Tooltip>
        </Box>)}
        {error && <Alert severity="error" sx={{ my: 1 }}>{error}</Alert>}
        <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
          <Button variant="outlined" onClick={() => input.current?.click()} disabled={busy}>选择文件</Button>
          <Button variant="contained" onClick={() => void start()} disabled={busy || items.length === 0}>{busy ? '上传中…' : '开始上传并解析'}</Button>
          {items.length > 0 && <Button color="inherit" onClick={clear} disabled={busy}>清空</Button>}
        </Box>
        <input ref={input} type="file" hidden multiple accept=".pdf,.txt,.md" onChange={event => { choose(event.target.files); event.target.value = '' }} />
      </CardContent>
    </Card>
  )
}

export default MultiFileUploadPanel
