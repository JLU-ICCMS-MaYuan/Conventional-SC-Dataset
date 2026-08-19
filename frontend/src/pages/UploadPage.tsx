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
} from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import AuthDialog from '../components/AuthDialog'
import PaperEditView from '../components/PaperEditView'
import { api } from '../lib/api'

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

const STATUS_CONFIG: Record<string, { label: string; color: 'warning' | 'info' | 'success' | 'error' }> = {
  parsing:   { label: '解析中',   color: 'warning' },
  processing: { label: '处理中', color: 'warning' },
  succeeded: { label: '解析完成', color: 'success' },
  failed: { label: '解析失败', color: 'error' },
  pending:   { label: '待审核',   color: 'info' },
  approved:  { label: '审核完成', color: 'success' },
  rejected:  { label: '已拒绝',   color: 'error' },
  needs_revision: { label: '需修改', color: 'warning' },
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
  const isPaperFile = (f: File) =>
    f.name.endsWith('.pdf') || f.name.endsWith('.txt') || f.name.endsWith('.md')
  const isJsonFile = (f: File) => f.name.endsWith('.json')
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
    setFile(f)
    if (isJsonFile(f)) { setFileType('json'); parseJson(f) }
    else if (isPaperFile(f)) { setFileType('paper') }
    else { setError(`不支持的文件类型。支持: ${ACCEPTED_STR}`); setFileType('') }
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
    setUploading(true)
    setUploadProgress(0)

    const formData = new FormData()
    formData.append('file', file)
    const token = localStorage.getItem('auth_token')
    const isText = file.name.endsWith('.txt') || file.name.endsWith('.md')
    const url = isText ? '/api/rag/upload-text' : '/api/rag/upload-pdf'

    const xhr = new XMLHttpRequest()
    xhr.open('POST', url)
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        setUploadProgress(Math.round((e.loaded / e.total) * 100))
      }
    }

    xhr.onload = () => {
      setUploading(false)
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText)
          setSnackbar('上传成功')
          setFile(null); setFileType('')
          loadHistory()
        } catch {
          setError('响应解析失败')
        }
      } else {
        try {
          const err = JSON.parse(xhr.responseText)
          const detail = err.detail
          const message = typeof detail === 'string' ? detail : (detail?.message || detail?.detail || err.message)
          setError(message || '上传失败')
        } catch { setError('上传失败') }
      }
    }

    xhr.onerror = () => {
      setUploading(false)
      setError('网络错误，上传失败')
    }

    xhr.send(formData)
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
        onDeleted={() => { handleDetailBack() }}
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
          {/* Upload drop zone */}
          <Card variant="outlined"
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
            onClick={() => fileInput.current?.click()}
            sx={{
              cursor: 'pointer', borderStyle: 'dashed', borderWidth: 2,
              borderColor: dragOver ? 'primary.main' : 'divider',
              bgcolor: dragOver ? '#eef2ff' : 'transparent', transition: 'all 0.2s',
            }}>
            <CardContent sx={{ textAlign: 'center', py: 6 }}>
              {getFileIcon()}
              {file ? (
                <>
                  <Typography variant="h6" gutterBottom>{file.name}</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {formatSize(file.size)} · {fileType === 'json' ? '组合 JSON' : '论文文件'}
                  </Typography>
                  {fileType === 'paper' && (
                    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 1 }}>
                      <Button variant="contained" onClick={(e) => { e.stopPropagation(); handleUploadPaper() }}
                        disabled={uploading}
                        startIcon={uploading ? <CircularProgress size={18} /> : <CloudUpload />}>
                        {uploading ? '上传中…' : '上传论文'}
                      </Button>
                      {uploading && (
                        <Box sx={{ width: '100%', maxWidth: 320, mt: 1 }}>
                          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
                            <Typography variant="caption" color="text.secondary">上传进度</Typography>
                            <Typography variant="caption" fontWeight={700}>{uploadProgress}%</Typography>
                          </Box>
                          <LinearProgress variant="determinate" value={uploadProgress}
                            sx={{ height: 6, borderRadius: 3 }} />
                        </Box>
                      )}
                    </Box>
                  )}
                </>
              ) : (
                <>
                  <Typography variant="h6" gutterBottom>拖拽文件到此处</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    支持 PDF · TXT · MD (超导论文)
                  </Typography>
                </>
              )}
              <input ref={fileInput} type="file" accept={ACCEPTED_STR} hidden onChange={handleFileChange} />
              <Button variant="outlined" onClick={(e) => { e.stopPropagation(); fileInput.current?.click() }}>
                选择文件
              </Button>
            </CardContent>
          </Card>

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
