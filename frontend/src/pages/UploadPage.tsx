import React, { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button, TextField,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, Chip, Alert, Snackbar, CircularProgress, LinearProgress,
  IconButton, Tooltip, Dialog, DialogTitle, DialogContent, DialogActions,
} from '@mui/material'
import { CloudUpload, Check, PictureAsPdf, Description, Code, Edit, Delete } from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import { api } from '../lib/api'

interface ParsedGroup {
  name: string
  description: string
  items: any[]
}

interface UploadedFile {
  id: string
  name: string
  size: number
  type: 'json' | 'pdf' | 'text'
  status: 'uploading' | 'done' | 'error'
  paperId?: number
  title?: string
  error?: string
}

const ACCEPTED_TYPES = ['.json', '.pdf', '.txt', '.md']
const ACCEPTED_STR = ACCEPTED_TYPES.join(',')

const UploadPage: React.FC = () => {
  const { user } = useAuth()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)

  const [dragOver, setDragOver] = useState(false)
  const [file, setFile] = useState<File | null>(null)
  const [fileType, setFileType] = useState<'json' | 'paper' | ''>('')
  const [parsed, setParsed] = useState<ParsedGroup | null>(null)
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [snackbar, setSnackbar] = useState('')

  // Upload history
  const [uploads, setUploads] = useState<UploadedFile[]>([])

  // Edit dialog
  const [editDlg, setEditDlg] = useState<{ open: boolean; item: UploadedFile | null }>({ open: false, item: null })
  const [editTitle, setEditTitle] = useState('')
  const [editDoi, setEditDoi] = useState('')
  const [editSaving, setEditSaving] = useState(false)

  const isPaperFile = (f: File) =>
    f.name.endsWith('.pdf') || f.name.endsWith('.txt') || f.name.endsWith('.md')

  const isJsonFile = (f: File) => f.name.endsWith('.json')

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

  const handleSaveGroup = async () => {
    if (!parsed || !name.trim()) return
    setSaving(true)
    try {
      const body = { name: name.trim(), description: description.trim(), items: parsed.items }
      if (user) {
        await api.post('/api/chart-groups/import', body)
      } else {
        const stored = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        stored.push({ id: Date.now(), ...body, is_preset: false, is_public: false,
          item_count: parsed.items.length, created_at: new Date().toISOString(), updated_at: new Date().toISOString() })
        localStorage.setItem('scwiki_local_groups', JSON.stringify(stored))
      }
      setSnackbar('组合导入成功')
      setTimeout(() => navigate('/share'), 500)
    } catch (e: any) { setError(e.message || '保存失败') }
    finally { setSaving(false) }
  }

  const handleUploadPaper = async () => {
    if (!file) return
    const id = `${Date.now()}`
    const newItem: UploadedFile = { id, name: file.name, size: file.size, type: file.name.endsWith('.pdf') ? 'pdf' : 'text', status: 'uploading' }
    setUploads(prev => [newItem, ...prev])
    setUploading(true)
    try {
      const formData = new FormData(); formData.append('file', file)
      const token = localStorage.getItem('auth_token')
      const isText = file.name.endsWith('.txt') || file.name.endsWith('.md')
      const url = isText ? '/api/rag/upload-text' : '/api/rag/upload-pdf'
      const res = await fetch(url, { method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {}, body: formData })
      if (!res.ok) throw new Error((await res.json()).detail || '上传失败')
      const data = await res.json()
      setUploads(prev => prev.map(u => u.id === id
        ? { ...u, status: 'done', paperId: data.paper_id, title: data.title || data.data?.title }
        : u))
      setSnackbar('上传成功')
      setFile(null); setFileType('')
    } catch (e: any) {
      setUploads(prev => prev.map(u => u.id === id ? { ...u, status: 'error', error: e.message } : u))
    } finally { setUploading(false) }
  }

  const handleEditOpen = (item: UploadedFile) => {
    setEditDlg({ open: true, item })
    setEditTitle(item.title || item.name)
    setEditDoi('')
  }

  const handleEditSave = async () => {
    if (!editDlg.item?.paperId) return
    setEditSaving(true)
    try {
      await api.put(`/api/admin/papers/${editDlg.item.paperId}`, { title: editTitle, doi: editDoi || undefined })
      setUploads(prev => prev.map(u => u.id === editDlg.item!.id ? { ...u, title: editTitle } : u))
      setSnackbar('已更新')
      setEditDlg({ open: false, item: null })
    } catch (e: any) { setSnackbar(`保存失败: ${e.message}`) }
    finally { setEditSaving(false) }
  }

  const handleDeleteUpload = (id: string) => {
    setUploads(prev => prev.filter(u => u.id !== id))
  }

  const formatSize = (s: number) => s > 1024 * 1024 ? `${(s / 1024 / 1024).toFixed(1)} MB` : `${(s / 1024).toFixed(1)} KB`

  const getFileIcon = () => {
    if (!file) return <CloudUpload sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
    if (fileType === 'json') return <Code sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
    if (file.name.endsWith('.pdf')) return <PictureAsPdf sx={{ fontSize: 48, color: 'error.main', mb: 2 }} />
    return <Description sx={{ fontSize: 48, color: 'info.main', mb: 2 }} />
  }

  return (
    <Box sx={{ maxWidth: 720, mx: 'auto' }}>
      <Typography variant="overline" color="text.secondary">Upload</Typography>
      <Typography variant="h4" fontWeight={800} sx={{ mb: 3 }}>上传</Typography>

      {!parsed && (
        <Card variant="outlined"
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
          onClick={() => fileInput.current?.click()}
          sx={{ cursor: 'pointer', borderStyle: 'dashed', borderWidth: 2,
            borderColor: dragOver ? 'primary.main' : 'divider',
            bgcolor: dragOver ? '#eef2ff' : 'transparent', transition: 'all 0.2s' }}>
          <CardContent sx={{ textAlign: 'center', py: 8 }}>
            {getFileIcon()}
            {file ? (
              <>
                <Typography variant="h6" gutterBottom>{file.name}</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {formatSize(file.size)} · {fileType === 'json' ? '组合 JSON' : '论文文件'}
                </Typography>
                {fileType === 'paper' && (
                  <Button variant="contained" onClick={handleUploadPaper}
                    disabled={uploading} startIcon={uploading ? <CircularProgress size={18} /> : <CloudUpload />}>
                    {uploading ? '上传中…' : '上传论文'}
                  </Button>
                )}
              </>
            ) : (
              <>
                <Typography variant="h6" gutterBottom>拖拽文件到此处</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  支持 JSON (组合) · PDF · TXT · MD (论文)
                </Typography>
              </>
            )}
            <input ref={fileInput} type="file" accept={ACCEPTED_STR} hidden onChange={handleFileChange} />
            <Button variant="outlined" onClick={(e) => { e.stopPropagation(); fileInput.current?.click() }}>
              选择文件
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Upload list */}
      {uploads.length > 0 && (
        <Card variant="outlined" sx={{ mt: 2 }}>
          <CardContent sx={{ pb: 1 }}>
            <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
              上传记录 ({uploads.length})
            </Typography>
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>文件</TableCell>
                    <TableCell sx={{ width: 80 }}>大小</TableCell>
                    <TableCell sx={{ width: 60 }}>状态</TableCell>
                    <TableCell sx={{ width: 100 }}>标题</TableCell>
                    <TableCell sx={{ width: 80 }} align="right">操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {uploads.map(u => (
                    <TableRow key={u.id}>
                      <TableCell>
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          {u.type === 'pdf' ? <PictureAsPdf fontSize="small" color="error" />
                            : u.type === 'json' ? <Code fontSize="small" color="primary" />
                            : <Description fontSize="small" color="info" />}
                          <Typography variant="body2" noWrap sx={{ maxWidth: 200 }}>{u.name}</Typography>
                        </Box>
                      </TableCell>
                      <TableCell>{formatSize(u.size)}</TableCell>
                      <TableCell>
                        {u.status === 'uploading' ? <CircularProgress size={16} />
                          : u.status === 'done' ? <Chip size="small" label="已上传" color="success" />
                          : <Chip size="small" label="失败" color="error" />}
                      </TableCell>
                      <TableCell>
                        <Typography variant="body2" noWrap sx={{ maxWidth: 100 }}>
                          {u.title || u.name}
                        </Typography>
                      </TableCell>
                      <TableCell align="right">
                        <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                          {u.status === 'done' && u.paperId && (
                            <Tooltip title="编辑"><IconButton size="small"
                              onClick={() => handleEditOpen(u)}><Edit fontSize="small" /></IconButton></Tooltip>
                          )}
                          <Tooltip title="移除"><IconButton size="small"
                            onClick={() => handleDeleteUpload(u.id)}><Delete fontSize="small" /></IconButton></Tooltip>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </CardContent>
        </Card>
      )}

      {/* JSON preview */}
      {parsed && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" fontWeight={600} gutterBottom>组合预览</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5, mb: 2 }}>
                <TextField label="组合名称" size="small" value={name} onChange={e => setName(e.target.value)} />
                <TextField label="描述" size="small" value={description} onChange={e => setDescription(e.target.value)} />
              </Box>
              <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
                <Chip size="small" label={`${parsed.items.length} 个数据点`} variant="outlined" />
                <Chip size="small" label={user ? '保存到数据库' : '保存到本地'} color={user ? 'primary' : 'default'} variant="outlined" />
              </Box>
              {parsed.items.length > 0 && (
                <TableContainer component={Paper} variant="outlined" sx={{ maxHeight: 320 }}>
                  <Table size="small" stickyHeader>
                    <TableHead><TableRow>
                      <TableCell>材料</TableCell><TableCell sx={{ width: 70 }}>Tc(K)</TableCell>
                      <TableCell sx={{ width: 70 }}>P(GPa)</TableCell><TableCell sx={{ width: 70 }}>类型</TableCell>
                    </TableRow></TableHead>
                    <TableBody>
                      {parsed.items.map((it: any, i: number) => (
                        <TableRow key={i}>
                          <TableCell><Typography variant="body2" noWrap sx={{ maxWidth: 180 }}>{it.material || it.label || it.custom_label || it.formula || '-'}</Typography></TableCell>
                          <TableCell>{it.tc ?? it.custom_tc ?? it.value_max ?? '-'}</TableCell>
                          <TableCell>{it.pressure ?? it.custom_pressure ?? '-'}</TableCell>
                          <TableCell><Chip size="small" label={it.type ?? it.custom_type ?? it.superconductor_type ?? '-'} sx={{ fontSize: 10, height: 18 }} /></TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              )}
            </CardContent>
          </Card>
          <Box sx={{ display: 'flex', gap: 1, justifyContent: 'flex-end' }}>
            <Button variant="outlined" onClick={() => { setParsed(null); setFile(null); setError('') }}>重新上传</Button>
            <Button variant="contained" onClick={handleSaveGroup} disabled={saving || !name.trim()}
              startIcon={saving ? <CircularProgress size={18} /> : <Check />}>{saving ? '保存中…' : '保存组合'}</Button>
          </Box>
        </Box>
      )}

      {/* Edit dialog */}
      <Dialog open={editDlg.open} onClose={() => setEditDlg({ open: false, item: null })} maxWidth="sm" fullWidth>
        <DialogTitle>编辑论文信息</DialogTitle>
        <DialogContent sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          <TextField label="标题" size="small" fullWidth value={editTitle} onChange={e => setEditTitle(e.target.value)} />
          <TextField label="DOI" size="small" fullWidth value={editDoi} onChange={e => setEditDoi(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditDlg({ open: false, item: null })}>取消</Button>
          <Button variant="contained" onClick={handleEditSave} disabled={editSaving}>保存</Button>
        </DialogActions>
      </Dialog>

      {uploading && <LinearProgress sx={{ mt: 2 }} />}
      {error && <Alert severity="error" sx={{ mt: 2 }} onClose={() => setError('')}>{error}</Alert>}
      <Snackbar open={!!snackbar} autoHideDuration={2000} onClose={() => setSnackbar('')}>
        <Alert severity="success" variant="filled">{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default UploadPage
