import React, { useState, useRef, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Paper, Chip, Alert, Snackbar, CircularProgress, LinearProgress,
  IconButton, Tooltip, Tabs, Tab,
} from '@mui/material'
import {
  CloudUpload, Check, PictureAsPdf, Description, Code,
  Refresh as RefreshIcon, ChevronRight as ChevronRightIcon,
  Replay as ReplayIcon, EditNote as EditNoteIcon,
} from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import AuthDialog from '../components/AuthDialog'
import PaperEditView from '../components/PaperEditView'
import UploadTaskEditor from '../components/UploadTaskEditor'
import UploadTaskCenter from '../components/UploadTaskCenter'
import MultiFileUploadPanel from '../components/MultiFileUploadPanel'
import UploadParsingDetail from '../components/UploadParsingDetail'
import { api } from '../lib/api'
import {
  PROCESSING_STAGES, UploadAcceptedResponse, UploadTaskState, unwrapData,
} from '../lib/paperProcessing'

/* ── Types ────────────────────────────────────── */

interface ParsedGroup {
  name: string
  description: string
  items: any[]
}

interface UploadRecord {
  id: number
  title: string | null
  doi: string | null
  journal: string | null
  year: number | null
  review_status: string
  source_file_path: string | null
  created_at: string
  key_properties: any[] | null
  record_count?: number
  processing_status?: string | null
  processing_error?: string | null
  paper_type?: string | null
  classification_reason?: string | null
}

/* ── Constants ────────────────────────────────── */

const ACCEPTED_TYPES = ['.json', '.pdf', '.txt', '.md']
const ACCEPTED_STR = ACCEPTED_TYPES.join(',')
const MAX_PAPER_UPLOAD_BYTES = 50 * 1024 * 1024
const FILE_TOO_LARGE_MESSAGE = '文件超过 50 MB 限制'

const STATUS_CONFIG: Record<string, { label: string; color: 'warning' | 'info' | 'success' | 'error' }> = {
  parsing:   { label: '解析中',   color: 'warning' },
  processing: { label: '处理中', color: 'warning' },
  succeeded: { label: '解析完成', color: 'success' },
  failed: { label: '解析失败', color: 'error' },
  pending:   { label: '待审核',   color: 'info' },
  approved:  { label: '审核完成', color: 'success' },
  rejected:  { label: '已拒绝',   color: 'error' },
  needs_revision: { label: '待审核（旧状态）', color: 'warning' },
}

function getDisplayStatus(record: UploadRecord): string {
  if (record.processing_status === 'failed') return 'failed'
  if (record.processing_status === 'processing') return 'processing'
  if (record.processing_status === 'succeeded') return 'succeeded'
  if (record.review_status === 'pending' &&
      (!record.key_properties || record.key_properties.length === 0)) {
    return 'parsing'
  }
  return record.review_status || 'pending'
}

/* ═══════════════════════════════════════════════ */
const UploadPage: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadXhr = useRef<XMLHttpRequest | null>(null)

  /* ── Stage ─────────────────────────────────── */
  const [stage, setStage] = useState<'list' | 'detail'>('list')
  const [detailPaperId, setDetailPaperId] = useState<number | null>(null)

  /* ── Auth dialog ───────────────────────────── */
  const [authOpen, setAuthOpen] = useState(false)

  /* ── Tab (paper / json) ────────────────────── */
  const [tab, setTab] = useState(0)

  /* ── File upload state ─────────────────────── */
  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [fileType, setFileType] = useState<'json' | 'paper' | ''>('')
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null)
  const [taskState, setTaskState] = useState<UploadTaskState | null>(null)
  const [taskLoading, setTaskLoading] = useState(false)
  const [taskPollTick, setTaskPollTick] = useState(0)
  const [taskCenterTick, setTaskCenterTick] = useState(0)

  /* ── JSON import state ─────────────────────── */
  const [parsed, setParsed] = useState<ParsedGroup | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [saving, setSaving] = useState(false)

  /* ── Upload history ────────────────────────── */
  const [uploads, setUploads] = useState<UploadRecord[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  /* ── Snackbar & error ──────────────────────── */
  const [snackbar, setSnackbar] = useState('')
  const [error, setError] = useState('')

  /* ── Helpers ───────────────────────────────── */
  const fileSuffix = (f: File) => f.name.toLowerCase()
  const isPaperFile = (f: File) =>
    fileSuffix(f).endsWith('.pdf') || fileSuffix(f).endsWith('.txt') || fileSuffix(f).endsWith('.md')
  const isJsonFile = (f: File) => fileSuffix(f).endsWith('.json')
  const formatSize = (s: number) =>
    s > 1024 * 1024 ? `${(s / 1024 / 1024).toFixed(1)} MB` : `${(s / 1024).toFixed(1)} KB`

  /* ── Load history ──────────────────────────── */
  const loadHistory = useCallback(async () => {
    if (!user) return
    setHistoryLoading(true)
    try {
      const res = await api.get<{ items: UploadRecord[]; total: number }>('/api/papers/my-uploads?limit=50')
      setUploads(res.items || [])
    } catch {
      // 端点可能尚未部署，静默失败
    } finally {
      setHistoryLoading(false)
    }
  }, [user])

  useEffect(() => { loadHistory() }, [loadHistory])

  const taskStorageKey = user ? `scwiki_active_upload_task:${user.id}` : null

  useEffect(() => {
    if (!taskStorageKey) { setActiveTaskId(null); setTaskState(null); return }
    setActiveTaskId(localStorage.getItem(taskStorageKey))
  }, [taskStorageKey])

  useEffect(() => {
    if (!activeTaskId || !taskStorageKey) return
    let timer: number | undefined
    let stopped = false
    const controller = new AbortController()

    const poll = async () => {
      setTaskLoading(true)
      try {
        const response = await api.get<{ ok: boolean; data: UploadTaskState }>(
          `/api/upload-tasks/${activeTaskId}`,
          { signal: controller.signal },
        )
        if (stopped) return
        const state = unwrapData(response)
        setTaskState(state)
        setError('')
        if (state.processing_status === 'processing') timer = window.setTimeout(poll, 2000)
      } catch (reason: any) {
        if (stopped || reason.name === 'AbortError') return
        if (reason.status === 401 || reason.status === 403 || reason.status === 404) {
          localStorage.removeItem(taskStorageKey)
          setActiveTaskId(null)
          setTaskState(null)
        } else {
          setError(reason.message || '处理进度查询失败，稍后将自动重试')
          timer = window.setTimeout(poll, 2000)
        }
      } finally {
        if (!stopped) setTaskLoading(false)
      }
    }

    void poll()
    return () => {
      stopped = true
      controller.abort()
      if (timer) window.clearTimeout(timer)
    }
  }, [activeTaskId, taskStorageKey, taskPollTick])

  useEffect(() => () => uploadXhr.current?.abort(), [])

  /* ── JSON parsing ──────────────────────────── */
  const parseJson = (f: File) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string)
        if (!data.name && !data.items) {
          setError('JSON 格式不正确：需要 name 和 items 字段')
          return
        }
        const g: ParsedGroup = {
          name: data.name || f.name.replace(/\.json$/i, ''),
          description: data.description || '',
          items: Array.isArray(data.items) ? data.items : [],
        }
        setParsed(g)
        setName(g.name)
        setDescription(g.description)
      } catch { setError('文件解析失败：不是有效的 JSON') }
    }
    reader.readAsText(f)
  }

  /* ── File handling ─────────────────────────── */
  const handleFile = (f: File) => {
    setError('')
    setParsed(null)
    if (isJsonFile(f)) {
      setFile(f); setFileType('json'); parseJson(f)
    } else if (isPaperFile(f)) {
      if (f.size > MAX_PAPER_UPLOAD_BYTES) {
        setFile(null); setFileType(''); setError(FILE_TOO_LARGE_MESSAGE)
        return
      }
      setFile(f); setFileType('paper')
    } else {
      setFile(null); setFileType(''); setError(`不支持的文件类型。支持: ${ACCEPTED_STR}`)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault(); setDragOver(false)
    const f = e.dataTransfer.files[0]
    if (f) handleFile(f)
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    if (f) handleFile(f)
  }

  /* ── Paper upload with progress ────────────── */
  const handleUploadPaper = () => {
    if (!file) return
    if (file.size > MAX_PAPER_UPLOAD_BYTES) {
      setError(FILE_TOO_LARGE_MESSAGE)
      return
    }
    setUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('auth_token')
    const lowerName = file.name.toLowerCase()
    const isText = lowerName.endsWith('.txt') || lowerName.endsWith('.md')
    const url = isText ? '/api/rag/upload-text' : '/api/rag/upload-pdf'

    const xhr = new XMLHttpRequest()
    uploadXhr.current = xhr
    xhr.open('POST', url)
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        setUploadProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      setUploading(false)
      uploadXhr.current = null
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText) as UploadAcceptedResponse
          if (!data.task_id) throw new Error('上传响应缺少任务编号')
          setActiveTaskId(data.task_id)
          setTaskState({
            task_id: data.task_id,
            filename: data.filename || file.name,
            stage: data.stage || 'saving_file',
            stage_index: data.stage_index || 1,
            stage_total: data.stage_total || 5,
            processing_status: data.processing_status || 'processing',
            processing_error: data.processing_error || null,
            completed_chunks: data.completed_chunks || 0,
            total_chunks: data.total_chunks || 0,
          })
          if (taskStorageKey) localStorage.setItem(taskStorageKey, data.task_id)
          setSnackbar('文件已保存，正在解析论文')
          setFile(null); setFileType('')
        } catch {
          setError('响应解析失败')
        }
      } else {
        if (xhr.status === 413) {
          setError(FILE_TOO_LARGE_MESSAGE)
          return
        }
        try {
          const err = JSON.parse(xhr.responseText)
          const detail = err.detail
          const message = typeof detail === 'string' ? detail : (detail?.message || detail?.detail || err.message)
          setError(message || '上传失败')
        } catch {
          const plainText = xhr.responseText.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
          setError(plainText || `上传失败（HTTP ${xhr.status}）`)
        }
      }
    }

    xhr.onerror = () => {
      setUploading(false)
      uploadXhr.current = null
      setError('网络错误，上传失败')
    }

    xhr.onabort = () => {
      setUploading(false)
      uploadXhr.current = null
    }

    xhr.send(formData)
  }

  const retryTask = async () => {
    if (!activeTaskId) return
    setTaskLoading(true)
    try {
      await api.post(`/api/rag/upload-tasks/${activeTaskId}/retry`)
      setTaskState(current => current ? {
        ...current, processing_status: 'processing', processing_error: null,
      } : current)
      setTaskPollTick(value => value + 1)
      setSnackbar('已重新开始解析失败或未完成的段落')
    } catch (reason: any) {
      setError(reason.message || '重新解析失败')
    } finally {
      setTaskLoading(false)
    }
  }

  const openManualDraft = async () => {
    if (!activeTaskId) return
    setTaskLoading(true)
    try {
      await api.post(`/api/rag/upload-tasks/${activeTaskId}/manual`)
      setTaskState(current => current ? {
        ...current, stage: 'ready', stage_index: 5, processing_status: 'succeeded', processing_error: null,
      } : current)
      setSnackbar('已打开手动填写草稿')
    } catch (reason: any) {
      setError(reason.message || '无法打开手动草稿')
    } finally {
      setTaskLoading(false)
    }
  }

  const handleTaskSubmitted = (paperId: number) => {
    if (taskStorageKey) localStorage.removeItem(taskStorageKey)
    setActiveTaskId(null)
    setTaskState(null)
    setSnackbar('已提交管理员审核')
    void loadHistory()
    setDetailPaperId(paperId)
    setStage('detail')
  }

  const openExistingPaper = (paperId: number) => {
    if (taskStorageKey) localStorage.removeItem(taskStorageKey)
    setActiveTaskId(null)
    setTaskState(null)
    handleDetailOpen(paperId)
  }

  /* ── JSON group save ───────────────────────── */
  const handleSaveGroup = async () => {
    if (!parsed || !name.trim()) return
    setSaving(true)
    try {
      const body = { name: name.trim(), description: description.trim(), items: parsed.items }
      if (user) {
        await api.post('/api/chart-groups/import', body)
      } else {
        const stored = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        stored.push({
          id: Date.now(), ...body, is_preset: false, is_public: false,
          item_count: parsed.items.length, created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        })
        localStorage.setItem('scwiki_local_groups', JSON.stringify(stored))
      }
      setSnackbar('组合导入成功')
      setTimeout(() => navigate('/share'), 500)
    } catch (e: any) { setError(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  const handleDetailOpen = (paperId: number) => {
    setDetailPaperId(paperId)
    setStage('detail')
  }

  const handleDetailBack = () => {
    setStage('list')
    setDetailPaperId(null)
    loadHistory()
  }

  const getFileIcon = () => {
    if (!file) return <CloudUpload sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
    if (fileType === 'json') return <Code sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
    if (file.name.endsWith('.pdf')) return <PictureAsPdf sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
    return <Description sx={{ fontSize: 48, color: 'info.main', mb: 2 }} />
  }

  /* ═══════════════════════════════════════════════ */
  /* Detail Stage                                  */
  /* ═══════════════════════════════════════════════ */
  if (stage === 'detail' && detailPaperId) {
    return (
      <PaperEditView
        paperId={detailPaperId}
        onBack={handleDetailBack}
      />
    )
  }

  /* ═══════════════════════════════════════════════ */
  /* Unauthenticated                               */
  /* ═══════════════════════════════════════════════ */
  if (!user) {
    return (
      <Box sx={{ maxWidth: 560, mx: 'auto', textAlign: 'center', py: 8 }}>
        <CloudUpload sx={{ fontSize: 64, color: 'text.disabled', mb: 3 }} />
        <Typography variant="h5" fontWeight={700} gutterBottom>请登录后使用上传功能</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          登录后可以上传超导论文 PDF/TXT/MD 文件，系统会自动解析并富化物性数据。
        </Typography>
        <Button variant="contained" size="large" onClick={() => setAuthOpen(true)}
          sx={{ borderRadius: '999px', px: 6, py: 1.5, fontSize: 16 }}>
          登录 / 注册
        </Button>
        <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} />
      </Box>
    )
  }

  /* ═══════════════════════════════════════════════ */
  /* List Stage                                    */
  /* ═══════════════════════════════════════════════ */
  return (
    <Box sx={{ maxWidth: 840, mx: 'auto' }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 3 }}>
        <Box>
          <Typography variant="overline" color="text.secondary">Upload</Typography>
          <Typography variant="h4" fontWeight={800}>上传</Typography>
        </Box>
        <Button variant="text" startIcon={<RefreshIcon />} onClick={loadHistory} disabled={historyLoading}>
          刷新
        </Button>
      </Box>

      {/* Tabs: Paper / JSON */}
      <Tabs value={tab} onChange={(_, v) => { setTab(v); setFile(null); setError(''); setParsed(null); }}
        sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="论文上传" />
        <Tab label="组合导入 (JSON)" />
      </Tabs>

      {/* ── TAB 0: Paper upload ── */}
      {tab === 0 && !parsed && (
        <>
          <UploadTaskCenter refreshKey={taskCenterTick} onOpen={task => {
            setActiveTaskId(task.task_id)
            setTaskState(task)
            if (taskStorageKey) localStorage.setItem(taskStorageKey, task.task_id)
            void api.post(`/api/upload-tasks/${task.task_id}/activity`)
          }} />
          {!activeTaskId && <MultiFileUploadPanel onCreated={task => {
            setActiveTaskId(task.task_id)
            setTaskState(task)
            setTaskCenterTick(value => value + 1)
            if (taskStorageKey) localStorage.setItem(taskStorageKey, task.task_id)
          }} />}
          {!activeTaskId && <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: -2, mb: 2 }}>
            支持 PDF · TXT · MD，每个文件最大 50 MB
          </Typography>}
          {activeTaskId && (
            <Box sx={{ mb: 3 }}>
              <Card variant="outlined">
                <CardContent>
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, mb: 2 }}>
                    <Box>
                      <Typography variant="h6" fontWeight={700}>{taskState?.filename || '正在读取上传任务'}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {taskState
                          ? `第 ${taskState.stage_index}/${taskState.stage_total} 步：${PROCESSING_STAGES.find(item => item.key === taskState.stage)?.label || taskState.stage}`
                          : '正在恢复处理进度…'}
                      </Typography>
                    </Box>
                    {taskLoading && <CircularProgress size={22} />}
                  </Box>

                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'repeat(5, minmax(0, 1fr))' }, gap: 1 }}>
                    {PROCESSING_STAGES.map((item, index) => {
                      const current = Math.max(0, (taskState?.stage_index || 1) - 1)
                      const complete = index < current || taskState?.processing_status === 'succeeded'
                      const active = index === current && taskState?.processing_status !== 'succeeded'
                      return (
                        <Box key={item.key} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, minWidth: 0 }}>
                          <Box sx={{
                            width: 24, height: 24, flexShrink: 0, borderRadius: '50%',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 12, fontWeight: 700,
                            color: complete || active ? 'primary.contrastText' : 'text.secondary',
                            bgcolor: complete || active ? 'primary.main' : 'action.disabledBackground',
                          }}>{complete ? '✓' : index + 1}</Box>
                          <Typography variant="caption" color={active ? 'text.primary' : 'text.secondary'}
                            sx={{ fontWeight: active ? 700 : 400, overflowWrap: 'anywhere' }}>{item.label}</Typography>
                        </Box>
                      )
                    })}
                  </Box>

                  {taskState?.stage === 'reading' && taskState.total_chunks > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">全文分段阅读进度</Typography>
                        <Typography variant="caption" fontWeight={700}>
                          {taskState.completed_chunks}/{taskState.total_chunks}
                        </Typography>
                      </Box>
                      <LinearProgress variant="determinate"
                        value={Math.min(100, taskState.completed_chunks / taskState.total_chunks * 100)} />
                    </Box>
                  )}

                  {taskState?.processing_status === 'processing' && (
                    <Alert severity="info" sx={{ mt: 2 }}>
                      当前进度来自服务器。关闭或刷新页面不会中断处理，再次打开本页会继续显示。
                    </Alert>
                  )}
                  {taskState?.processing_status === 'failed' && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      <Typography variant="body2" fontWeight={700}>
                        第 {taskState.stage_index}/{taskState.stage_total} 步失败
                      </Typography>
                      <Typography variant="body2">{taskState.processing_error || '服务器没有返回具体失败原因'}</Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
                        <Button size="small" variant="contained" startIcon={<ReplayIcon />}
                          disabled={taskLoading} onClick={() => void retryTask()}>重新解析</Button>
                        <Button size="small" variant="outlined" startIcon={<EditNoteIcon />}
                          disabled={taskLoading} onClick={() => void openManualDraft()}>手动填写</Button>
                      </Box>
                    </Alert>
                  )}
                  {taskState?.duplicate && taskState.existing_paper_id && (
                    <Alert severity="warning" sx={{ mt: 2 }}
                      action={taskState.allowed_actions?.includes('view')
                        ? <Button color="inherit" size="small" onClick={() => openExistingPaper(taskState.existing_paper_id!)}>打开已有论文</Button>
                        : undefined}>
                      {taskState.duplicate_reason || '数据库中已有相同 DOI，未创建重复论文。'}
                    </Alert>
                  )}
                  {activeTaskId && <UploadParsingDetail taskId={activeTaskId} />}
                </CardContent>
              </Card>

              {taskState?.stage === 'ready' && taskState.processing_status === 'succeeded' && !taskState.duplicate && (
                <UploadTaskEditor taskId={activeTaskId} onSubmitted={handleTaskSubmitted} />
              )}
            </Box>
          )}

          {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>{error}</Alert>}

          {/* Upload history */}
          <Box sx={{ mt: 4 }}>
            <Typography variant="h6" fontWeight={700} sx={{ mb: 2 }}>
              上传记录
              {uploads.length > 0 && (
                <Chip size="small" label={uploads.length} sx={{ ml: 1, fontWeight: 700 }} />
              )}
            </Typography>

            {historyLoading && <LinearProgress sx={{ mb: 2, borderRadius: 999 }} />}

            {uploads.length === 0 && !historyLoading && (
              <Card variant="outlined" sx={{ textAlign: 'center', py: 4 }}>
                <Typography variant="body2" color="text.secondary">
                  暂无上传记录。拖拽 PDF/TXT/MD 文件到上方区域开始上传。
                </Typography>
              </Card>
            )}

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              {uploads.map(record => {
                const status = getDisplayStatus(record)
                const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.pending
                const sourcePath = record.source_file_path || ''
                const fileName = sourcePath.replace(/^upload\//, '') || '-'
                const isPdf = fileName.endsWith('.pdf')

                return (
                  <Card key={record.id} variant="outlined"
                    sx={{
                      cursor: 'pointer', transition: 'all 0.15s',
                      '&:hover': { borderColor: 'primary.main', boxShadow: '0 2px 12px rgba(79,70,229,.08)' },
                    }}
                    onClick={() => handleDetailOpen(record.id)}>
                    <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2, py: 2, '&:last-child': { pb: 2 } }}>
                      {/* File icon */}
                      <Box sx={{
                        width: 44, height: 44, borderRadius: 2, display: 'flex', alignItems: 'center',
                        justifyContent: 'center', bgcolor: isPdf ? '#fee2e2' : '#e0f2fe', flexShrink: 0,
                      }}>
                        {isPdf
                          ? <PictureAsPdf sx={{ color: '#b3261e' }} />
                          : <Description sx={{ color: '#0891b2' }} />}
                      </Box>

                      {/* Content */}
                      <Box sx={{ flex: 1, minWidth: 0 }}>
                        <Typography variant="body1" fontWeight={700} noWrap>
                          {record.title || fileName}
                        </Typography>
                        <Box sx={{ display: 'flex', gap: 1.5, mt: 0.25, flexWrap: 'wrap' }}>
                          <Typography variant="caption" color="text.secondary">
                            {fileName}
                          </Typography>
                          {record.year && (
                            <Typography variant="caption" color="text.secondary">
                              {record.year}
                            </Typography>
                          )}
                          <Typography variant="caption" color="text.secondary">
                            {record.created_at ? new Date(record.created_at).toLocaleDateString('zh-CN') : '-'}
                          </Typography>
                        </Box>
                      </Box>

                      {/* Status + arrow */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                        <Chip
                          size="small"
                          label={cfg.label}
                          color={cfg.color}
                          sx={{ fontWeight: 700, minWidth: 72 }}
                        />
                        <ChevronRightIcon sx={{ color: 'text.disabled' }} />
                      </Box>
                    </CardContent>
                  </Card>
                )
              })}
            </Box>
          </Box>
        </>
      )}

      {/* ── TAB 1: JSON import ── */}
      {tab === 1 && (
        <>
          {!parsed ? (
            <Card variant="outlined"
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
              onClick={() => fileInput.current?.click()}
              sx={{
                cursor: 'pointer', borderStyle: 'dashed', borderWidth: 2,
                borderColor: dragOver ? 'primary.main' : 'divider',
                bgcolor: dragOver ? '#eef2ff' : 'transparent', transition: 'all 0.2s',
              }}>
              <CardContent sx={{ textAlign: 'center', py: 8 }}>
                <Code sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
                <Typography variant="h6" gutterBottom>导入 JSON 组合文件</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  需要包含 name 和 items 字段，用于 Tc-P 图表可视化
                </Typography>
                <input ref={fileInput} type="file" accept=".json" hidden onChange={handleFileChange} />
                <Button variant="outlined" onClick={(e) => { e.stopPropagation(); fileInput.current?.click() }}>
                  选择 JSON 文件
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" fontWeight={600} gutterBottom>组合预览</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mb: 2 }}>
                    <TextField label="组合名称" size="small" value={name}
                      onChange={e => setName(e.target.value)} />
                    <TextField label="描述" size="small" value={description}
                      onChange={e => setDescription(e.target.value)} />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip size="small" label={`${parsed.items.length} 个数据点`} variant="outlined" />
                    <Chip size="small" label={user ? '保存到数据库' : '保存到本地'}
                      color={user ? 'primary' : 'default'} variant="outlined" />
                  </Box>
                  {parsed.items.length > 0 && (
                    <Paper variant="outlined" sx={{ maxHeight: 320, overflow: 'auto' }}>
                      <Box component="table" sx={{
                        width: '100%', borderCollapse: 'collapse', fontSize: 13,
                      }}>
                        <Box component="thead">
                          <Box component="tr">
                            {['材料', 'Tc(K)', 'P(GPa)', '类型'].map(h => (
                              <Box key={h} component="th" sx={{
                                p: '8px 12px', borderBottom: '2px solid', borderColor: 'divider',
                                textAlign: 'left', color: 'text.secondary', fontSize: 12,
                                whiteSpace: 'nowrap',
                              }}>{h}</Box>
                            ))}
                          </Box>
                        </Box>
                        <Box component="tbody">
                          {parsed.items.map((it: any, i: number) => (
                            <Box component="tr" key={i}>
                              <Box component="td" sx={{ p: '8px 12px', borderBottom: '1px solid', borderColor: 'divider' }}>
                                <Typography variant="body2" noWrap sx={{ maxWidth: 180 }}>
                                  {it.material || it.label || it.custom_label || it.formula || '-'}
                                </Typography>
                              </Box>
                              <Box component="td" sx={{ p: '8px 12px', borderBottom: '1px solid', borderColor: 'divider' }}>
                                {it.tc ?? it.custom_tc ?? it.value_max ?? '-'}
                              </Box>
                              <Box component="td" sx={{ p: '8px 12px', borderBottom: '1px solid', borderColor: 'divider' }}>
                                {it.pressure ?? it.custom_pressure ?? '-'}
                              </Box>
                              <Box component="td" sx={{ p: '8px 12px', borderBottom: '1px solid', borderColor: 'divider' }}>
                                <Chip size="small"
                                  label={it.type ?? it.custom_type ?? it.superconductor_type ?? '-'}
                                  sx={{ fontSize: 10, height: 18 }} />
                              </Box>
                            </Box>
                          ))}
                        </Box>
                      </Box>
                    </Paper>
                  )}
                </CardContent>
              </Card>
              <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
                <Button variant="outlined" onClick={() => { setParsed(null); setFile(null); setError('') }}>
                  重新上传
                </Button>
                <Button variant="contained" onClick={handleSaveGroup} disabled={saving || !name.trim()}
                  startIcon={saving ? <CircularProgress size={18} /> : <Check />}>
                  {saving ? '保存中…' : '保存组合'}
                </Button>
              </Box>
            </Box>
          )}
          {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>{error}</Alert>}
        </>
      )}

      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="success" variant="filled">{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default UploadPage
