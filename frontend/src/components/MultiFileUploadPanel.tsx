import React, { useRef, useState } from 'react'
import { Alert, Box, Button, Card, CardContent, IconButton, LinearProgress, MenuItem, Select, Tooltip, Typography } from '@mui/material'
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined'
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline'
import { getStoredToken } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import { api } from '../lib/api'
import { UploadTaskState, unwrapData } from '../lib/paperProcessing'

// 单文件大小上限（字节）。界面上的「每个最大 50 MB」提示由 zh 字典 upload.limit 提供；
// 源码中的「最大 50 MB」字面量是前端契约测试
// tests/01_decentralized_uploading/test_issue18_upload_limits.py 的检索锚点，改动需同步该测试。
const MAX_BYTES = 50 * 1024 * 1024
type Role = 'main' | 'supplementary' | 'attachment'
interface Selected { clientId: string; file: File; role: Role; progress: number; status: string }

interface Props { onCreated: (task: UploadTaskState) => void }

function uploadOne(
  taskId: string,
  item: Selected,
  progress: (value: number) => void,
  t: (key: string, vars?: Record<string, string | number>) => string,
): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('PUT', `/api/upload-tasks/${taskId}/files/${item.clientId}`)
    const token = getStoredToken()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = event => event.lengthComputable && progress(Math.round(event.loaded / event.total * 100))
    xhr.onerror = () => reject(new Error(t('upload.networkError')))
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve()
      else {
        try { reject(new Error(JSON.parse(xhr.responseText)?.detail?.message || t('upload.uploadFailed'))) }
        catch { reject(new Error(xhr.status === 413 ? t('upload.fileTooLarge') : t('upload.uploadFailedHttp', { status: xhr.status }))) }
      }
    }
    const body = new FormData()
    body.append('file', item.file)
    xhr.send(body)
  })
}

const MultiFileUploadPanel: React.FC<Props> = ({ onCreated }) => {
  const { t, lang } = useLanguage()
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
      if (!/\.(pdf|txt|md|cif|poscar|vasp)$/i.test(file.name) && !/^(POSCAR|CONTCAR)$/i.test(file.name)) rejected.push(t('upload.unsupportedExtension', { name: file.name }))
      else if (file.size > MAX_BYTES) rejected.push(t('upload.fileTooLargeNamed', { name: file.name }))
      else if (signatures.has(signature)) rejected.push(t('upload.fileDuplicate', { name: file.name }))
      else { accepted.push(file); signatures.add(signature) }
    }
    const hasMain = items.some(item => item.role === 'main')
    const additions = accepted.map((file, index): Selected => ({
      clientId: crypto.randomUUID().replaceAll('-', ''), file,
      role: !hasMain && index === 0 ? 'main' : 'attachment', progress: 0, status: '等待上传',
    }))
    if (additions.length) setItems(current => [...current, ...additions])
    setError(rejected.join(t('upload.sentenceSeparator')))
  }

  const setRole = (clientId: string, role: Role) => {
    setItems(current => current.map(item => item.clientId === clientId ? { ...item, role } : item))
  }

  const remove = (clientId: string) => {
    setItems(current => current.filter(item => item.clientId !== clientId))
  }

  const clear = () => {
    if (!items.length || !window.confirm(t('upload.confirmClear'))) return
    setItems([])
    setError('')
    if (input.current) input.current.value = ''
  }

  const start = async () => {
    if (items.filter(item => item.role === 'main').length !== 1) { setError(t('upload.mustSelectMain')); return }
    setBusy(true); setError('')
    try {
      const created = await api.post<{ ok: boolean; data: UploadTaskState }>('/api/upload-tasks', {
        suggestion_language: lang,
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
            existing.file === item.file ? { ...existing, progress: value, status: '上传中' } : existing)), t)
          setItems(current => current.map(existing => existing.file === item.file ? { ...existing, progress: 100, status: '完成' } : existing))
        }
      }
      await Promise.all(Array.from({ length: Math.min(3, queue.length) }, worker))
      const detail = await api.get<{ ok: boolean; data: UploadTaskState }>(`/api/upload-tasks/${task.task_id}`)
      onCreated(unwrapData(detail))
      setItems([])
    } catch (reason: any) {
      setError(reason.message || t('upload.batchUploadFailed'))
    } finally { setBusy(false) }
  }

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="h6" fontWeight={700}>{t('upload.newTaskTitle')}</Typography>
        <Typography variant="body2" color="text.secondary">{t('upload.newTaskHint')}</Typography>
        <Box
          aria-label={t('upload.dropZoneAria')}
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
            <Typography fontWeight={700}>{t('upload.dropHint')}</Typography>
            <Typography variant="caption" color="text.secondary">{t('upload.limit', { size: 50, count: 3 })}</Typography>
          </Box>
        </Box>
        {items.map(item => <Box key={item.clientId} sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr) 112px 40px', sm: 'minmax(0, 1fr) 150px 40px' }, gap: 1, mb: 1, alignItems: 'center' }}>
          <Box sx={{ minWidth: 0 }}><Typography noWrap>{item.file.name}</Typography><LinearProgress variant="determinate" value={item.progress} /></Box>
          <Select size="small" value={item.role} disabled={busy} onChange={event => setRole(item.clientId, event.target.value as Role)}>
            <MenuItem value="main">{t('upload.role.main')}</MenuItem><MenuItem value="supplementary">{t('upload.role.supplementary')}</MenuItem><MenuItem value="attachment">{t('upload.role.attachment')}</MenuItem>
          </Select>
          <Tooltip title={t('upload.removeFile')}><span><IconButton aria-label={t('upload.removeFileAria', { name: item.file.name })} size="small" disabled={busy} onClick={() => remove(item.clientId)}><DeleteOutlineIcon fontSize="small" /></IconButton></span></Tooltip>
        </Box>)}
        {error && <Alert severity="error" sx={{ my: 1 }}>{error}</Alert>}
        <Box sx={{ display: 'flex', gap: 1, mt: 2, flexWrap: 'wrap' }}>
          <Button variant="outlined" onClick={() => input.current?.click()} disabled={busy}>{t('upload.chooseFiles')}</Button>
          <Button variant="contained" onClick={() => void start()} disabled={busy || items.length === 0}>{busy ? t('upload.uploadingInProgress') : t('upload.startUpload')}</Button>
          {items.length > 0 && <Button color="inherit" onClick={clear} disabled={busy}>{t('upload.clearList')}</Button>}
        </Box>
        <input ref={input} type="file" hidden multiple accept=".pdf,.txt,.md,.cif,.poscar,.vasp,POSCAR,CONTCAR" onChange={event => { choose(event.target.files); event.target.value = '' }} />
      </CardContent>
    </Card>
  )
}

export default MultiFileUploadPanel
