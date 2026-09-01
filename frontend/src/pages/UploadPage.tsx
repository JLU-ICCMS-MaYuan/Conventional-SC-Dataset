import React, { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Paper, Chip, Alert, Snackbar, CircularProgress, LinearProgress,
  IconButton, Tooltip, Tabs, Tab,
} from '@mui/material'
import {
  CloudUpload, Check, PictureAsPdf, Description, Code,
  Replay as ReplayIcon, EditNote as EditNoteIcon, KeyboardArrowUp as KeyboardArrowUpIcon,
} from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import AuthDialog from '../components/AuthDialog'
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

/* ── Constants ────────────────────────────────── */

const ACCEPTED_TYPES = ['.json', '.pdf', '.txt', '.md']
const ACCEPTED_STR = ACCEPTED_TYPES.join(',')
const MAX_PAPER_UPLOAD_BYTES = 50 * 1024 * 1024

/* ═══════════════════════════════════════════════ */
const UploadPage: React.FC = () => {
  const { user } = useAuth()
  const { t } = useLanguage()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const uploadXhr = useRef<XMLHttpRequest | null>(null)

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

  // 处理阶段标签统一走 upload.step.<stage.key>（与处理流程组件保持一致）
  const stageLabel = (key: string): string => {
    const stage = PROCESSING_STAGES.find(item => item.key === key)
    return stage ? t('upload.step.' + stage.key) : key
  }

  const taskStorageKey = user ? `scwiki_active_upload_task:${user.id}` : null

  const collapseActiveTask = () => {
    setActiveTaskId(null)
    setTaskState(null)
    if (taskStorageKey) localStorage.removeItem(taskStorageKey)
  }

  const toggleTask = (task: UploadTaskState) => {
    if (task.task_id === activeTaskId) {
      collapseActiveTask()
      return
    }
    setActiveTaskId(task.task_id)
    setTaskState(task)
    if (taskStorageKey) localStorage.setItem(taskStorageKey, task.task_id)
    void api.post(`/api/upload-tasks/${task.task_id}/activity`)
  }

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
          setError(reason.message || t('upload.progressQueryFailed'))
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
          setError(t('upload.jsonInvalid'))
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
      } catch { setError(t('upload.jsonParseFailed')) }
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
        setFile(null); setFileType(''); setError(t('upload.fileTooLarge'))
        return
      }
      setFile(f); setFileType('paper')
    } else {
      setFile(null); setFileType(''); setError(t('upload.unsupportedFileType', { types: ACCEPTED_STR }))
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
      setError(t('upload.fileTooLarge'))
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
          if (!data.task_id) throw new Error(t('upload.responseMissingTask'))
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
          setSnackbar(t('upload.fileSavedParsing'))
          setFile(null); setFileType('')
        } catch {
          setError(t('upload.responseParseFailed'))
        }
      } else {
        if (xhr.status === 413) {
          setError(t('upload.fileTooLarge'))
          return
        }
        try {
          const err = JSON.parse(xhr.responseText)
          const detail = err.detail
          const message = typeof detail === 'string' ? detail : (detail?.message || detail?.detail || err.message)
          setError(message || t('upload.uploadFailed'))
        } catch {
          const plainText = xhr.responseText.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim()
          setError(plainText || t('upload.uploadFailedHttp', { status: xhr.status }))
        }
      }
    }

    xhr.onerror = () => {
      setUploading(false)
      uploadXhr.current = null
      setError(t('upload.networkError'))
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
      setSnackbar(t('upload.retryStarted'))
    } catch (reason: any) {
      setError(reason.message || t('upload.retryParseFailed'))
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
      setSnackbar(t('upload.manualDraftOpened'))
    } catch (reason: any) {
      setError(reason.message || t('upload.manualDraftFailed'))
    } finally {
      setTaskLoading(false)
    }
  }

  // 论文详情由 /papers/:id 路由承载，离开后仍可通过刷新、前进/后退或直接访问地址回到
  const handleTaskSubmitted = (paperId: number) => {
    if (taskStorageKey) localStorage.removeItem(taskStorageKey)
    setActiveTaskId(null)
    setTaskState(null)
    setSnackbar(t('upload.submittedForReview'))
    navigate(`/papers/${paperId}`)
  }

  const openExistingPaper = (paperId: number) => {
    if (taskStorageKey) localStorage.removeItem(taskStorageKey)
    setActiveTaskId(null)
    setTaskState(null)
    navigate(`/papers/${paperId}`)
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
      setSnackbar(t('upload.groupImportSuccess'))
      setTimeout(() => navigate('/share'), 500)
    } catch (e: any) { setError(e.message || t('upload.groupSaveFailed')) }
    finally { setSaving(false) }
  }

  const getFileIcon = () => {
    if (!file) return <CloudUpload sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
    if (fileType === 'json') return <Code sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
    if (file.name.endsWith('.pdf')) return <PictureAsPdf sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
    return <Description sx={{ fontSize: 48, color: 'info.main', mb: 2 }} />
  }

  /* ═══════════════════════════════════════════════ */
  /* Unauthenticated                               */
  /* ═══════════════════════════════════════════════ */
  if (!user) {
    return (
      <Box sx={{ maxWidth: 560, mx: 'auto', textAlign: 'center', py: 8 }}>
        <CloudUpload sx={{ fontSize: 64, color: 'text.disabled', mb: 3 }} />
        <Typography variant="h5" fontWeight={700} gutterBottom>{t('upload.loginRequired')}</Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          {t('upload.loginHint')}
        </Typography>
        <Button variant="contained" size="large" onClick={() => setAuthOpen(true)}
          sx={{ borderRadius: '999px', px: 6, py: 1.5, fontSize: 16 }}>
          {t('upload.loginRegister')}
        </Button>
        <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} />
      </Box>
    )
  }

  /* ═══════════════════════════════════════════════ */
  /* List Stage                                    */
  /* ═══════════════════════════════════════════════ */
  return (
    <Box sx={{ width: '100%', maxWidth: 'none' }}>
      <Box sx={{ mb: 3 }}>
        <Box>
          <Typography variant="overline" color="text.secondary">Upload</Typography>
          <Typography variant="h4" fontWeight={800}>{t('upload.pageTitle')}</Typography>
        </Box>
      </Box>

      {/* Tabs: Paper / JSON */}
      <Tabs value={tab} onChange={(_, v) => { setTab(v); setFile(null); setError(''); setParsed(null); }}
        sx={{ mb: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label={t('upload.tabPaper')} />
        <Tab label={t('upload.tabJson')} />
      </Tabs>

      {/* ── TAB 0: Paper upload ── */}
      {tab === 0 && !parsed && (
        <>
          <MultiFileUploadPanel onCreated={task => {
            setActiveTaskId(task.task_id)
            setTaskState(task)
            setTaskCenterTick(value => value + 1)
            if (taskStorageKey) localStorage.setItem(taskStorageKey, task.task_id)
          }} />
          <UploadTaskCenter refreshKey={taskCenterTick} activeTaskId={activeTaskId} onToggle={toggleTask} />
          {activeTaskId && (
            <Box sx={{ mb: 3 }}>
              <Card variant="outlined" sx={{ overflow: 'visible' }}>
                <CardContent>
                  <Box role="region" aria-label={t('upload.taskActionsAria')} sx={{
                    position: 'sticky', top: '80px', zIndex: theme => theme.zIndex.appBar - 1,
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2,
                    mx: -2, mt: -2, mb: 2, px: 2, py: 1.5,
                    bgcolor: 'background.paper', borderBottom: '1px solid', borderColor: 'divider',
                    boxShadow: '0 1px 2px rgba(15,23,42,0.08)',
                  }}>
                    <Box sx={{ minWidth: 0, flex: 1 }}>
                      <Typography variant="h6" fontWeight={700} noWrap>{taskState?.filename || t('upload.readingTask')}</Typography>
                      <Typography variant="body2" color="text.secondary">
                        {taskState
                          ? t('upload.stageProgress', {
                              index: taskState.stage_index,
                              total: taskState.stage_total,
                              label: stageLabel(taskState.stage),
                            })
                          : t('upload.restoringProgress')}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexShrink: 0 }}>
                      {taskLoading && <CircularProgress size={22} />}
                      <Button
                        size="small"
                        variant="contained"
                        startIcon={<KeyboardArrowUpIcon />}
                        aria-label={t('upload.collapseDetailAria')}
                        onClick={collapseActiveTask}
                        sx={{ minHeight: 44, flexShrink: 0 }}
                      >{t('upload.collapseDetail')}</Button>
                    </Box>
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
                            sx={{ fontWeight: active ? 700 : 400, overflowWrap: 'anywhere' }}>{t('upload.step.' + item.key)}</Typography>
                        </Box>
                      )
                    })}
                  </Box>

                  {taskState?.stage === 'reading' && taskState.total_chunks > 0 && (
                    <Box sx={{ mt: 2 }}>
                      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                        <Typography variant="caption" color="text.secondary">{t('upload.chunkReadingProgress')}</Typography>
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
                      {t('upload.serverProgressNote')}
                    </Alert>
                  )}
                  {taskState?.processing_status === 'failed' && (
                    <Alert severity="error" sx={{ mt: 2 }}>
                      <Typography variant="body2" fontWeight={700}>
                        {t('upload.stageFailed', { index: taskState.stage_index, total: taskState.stage_total })}
                      </Typography>
                      <Typography variant="body2">{taskState.processing_error || t('upload.noFailureReason')}</Typography>
                      <Box sx={{ display: 'flex', gap: 1, mt: 1.5, flexWrap: 'wrap' }}>
                        <Button size="small" variant="contained" startIcon={<ReplayIcon />}
                          disabled={taskLoading} onClick={() => void retryTask()}>{t('upload.retryParse')}</Button>
                        <Button size="small" variant="outlined" startIcon={<EditNoteIcon />}
                          disabled={taskLoading} onClick={() => void openManualDraft()}>{t('upload.manualFill')}</Button>
                      </Box>
                    </Alert>
                  )}
                  {taskState?.duplicate && taskState.existing_paper_id && (
                    <Alert severity="warning" sx={{ mt: 2 }}
                      action={taskState.allowed_actions?.includes('view')
                        ? <Button color="inherit" size="small" onClick={() => openExistingPaper(taskState.existing_paper_id!)}>{t('upload.openExistingPaper')}</Button>
                        : undefined}>
                      {taskState.duplicate_reason || t('upload.duplicateExisting')}
                    </Alert>
                  )}
                  {activeTaskId && <UploadParsingDetail taskId={activeTaskId} onSubmitted={handleTaskSubmitted} />}
                </CardContent>
              </Card>
            </Box>
          )}

          {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>{error}</Alert>}

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
                <Typography variant="h6" gutterBottom>{t('upload.importJsonTitle')}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {t('upload.importJsonHint')}
                </Typography>
                <input ref={fileInput} type="file" accept=".json" hidden onChange={handleFileChange} />
                <Button variant="outlined" onClick={(e) => { e.stopPropagation(); fileInput.current?.click() }}>
                  {t('upload.chooseJsonFile')}
                </Button>
              </CardContent>
            </Card>
          ) : (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="h6" fontWeight={600} gutterBottom>{t('upload.groupPreview')}</Typography>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mb: 2 }}>
                    <TextField label={t('upload.groupName')} size="small" value={name}
                      onChange={e => setName(e.target.value)} />
                    <TextField label={t('upload.groupDescription')} size="small" value={description}
                      onChange={e => setDescription(e.target.value)} />
                  </Box>
                  <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                    <Chip size="small" label={t('upload.dataPoints', { count: parsed.items.length })} variant="outlined" />
                    <Chip size="small" label={user ? t('upload.saveToDatabase') : t('upload.saveToLocal')}
                      color={user ? 'primary' : 'default'} variant="outlined" />
                  </Box>
                  {parsed.items.length > 0 && (
                    <Paper variant="outlined" sx={{ maxHeight: 320, overflow: 'auto' }}>
                      <Box component="table" sx={{
                        width: '100%', borderCollapse: 'collapse', fontSize: 13,
                      }}>
                        <Box component="thead">
                          <Box component="tr">
                            {[t('upload.colMaterial'), 'Tc(K)', 'P(GPa)', t('upload.colType')].map(h => (
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
                  {t('upload.reUpload')}
                </Button>
                <Button variant="contained" onClick={handleSaveGroup} disabled={saving || !name.trim()}
                  startIcon={saving ? <CircularProgress size={18} /> : <Check />}>
                  {saving ? t('common.saving') : t('upload.saveGroup')}
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
