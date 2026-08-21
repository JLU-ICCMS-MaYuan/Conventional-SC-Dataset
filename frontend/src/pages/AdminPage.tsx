import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Card, CardContent, Tabs, Tab, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel, Alert,
  Snackbar, CircularProgress, LinearProgress, Avatar, Tooltip,
  Pagination, Checkbox, FormControlLabel,
} from '@mui/material'
import {
  Check as ApproveIcon,
  Close as RejectIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  Shield as AdminIcon,
  Person as UserIcon,
  Gavel as ReviewIcon,
  Download as DownloadIcon,
  DriveFileRenameOutline as RenameIcon,
  History as HistoryIcon,
} from '@mui/icons-material'
import { type User, useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { SourceEvidence, UploadDraft, normalizeUploadDraft, unwrapData } from '../lib/paperProcessing'
import ChartGroupEditor from '../components/ChartGroupEditor'
import NewsManager from '../components/NewsManager'
import UsernameField from '../components/UsernameField'

/* ── Types ───────────────────────────────────── */
interface UserRecord {
  id: number; email: string; username: string; username_change_allowed: boolean; role: string
  is_admin: boolean; is_superadmin: boolean; is_approved: boolean
  is_email_verified: boolean; created_at: string; approved_at: string | null
  submitted_count: number; reviewed_count: number
}

interface UsernameAuditEvent {
  id: number; target_user_id: number; changed_by_user_id: number
  changed_by_username: string; old_username: string; new_username: string
  reason: string; created_at: string
}

interface PaperRecord {
  id: number; doi: string | null; title: string | null; authors: unknown
  journal: string | null; year: number | null; review_status: string
  review_comment: string | null; reviewer_name: string | null
  uploader_name: string | null; created_at: string | null
  record_count: number; show_in_chart: boolean
  compound_symbols: string | null; article_types: string[]
  superconductor_types: string[]
  key_properties?: Array<{ superconductor_type?: string | null }>
}

interface ReviewArtifact {
  ai: UploadDraft
  user: UploadDraft
  evidence: {
    classification?: SourceEvidence[]
    key_properties?: Array<SourceEvidence | SourceEvidence[] | null>
  }
}

interface CandidateAttachment {
  id: string
  filename: string
  file_sha256: string | null
  file_size: number
  uploaded_by_user_id: number | null
  created_at: number | null
}

/* ── Helpers ──────────────────────────────────── */
const ROLE_COLORS: Record<string, 'error'|'primary'|'default'> = {
  superadmin: 'error', admin: 'primary', user: 'default',
}
const ROLE_LABELS: Record<string, string> = {
  superadmin: '超管', admin: '管理员', user: '用户',
}
const STATUS_COLORS: Record<string, 'warning'|'success'|'error'|'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}
const STATUS_LABELS: Record<string, string> = {
  pending: '待审核', approved: '已通过', rejected: '已拒绝', needs_revision: '待审核（旧状态）',
}
const paperRecordCount = (paper?: PaperRecord | null) =>
  paper?.record_count ?? paper?.key_properties?.length ?? 0
const paperSuperconductorTypes = (paper: PaperRecord) =>
  paper.superconductor_types?.length
    ? paper.superconductor_types
    : [...new Set((paper.key_properties || []).map(item => item.superconductor_type).filter(Boolean) as string[])]

/* ═══════════════════════════════════════════════ */
const AdminPage: React.FC = () => {
  const { user, replaceUser } = useAuth()
  const isSuper = user?.role === 'superadmin'

  const [tab, setTab] = useState(0)
  const [snackbar, setSnackbar] = useState('')

  /* ── Dashboard ──────────────────────────────── */
  const [stats, setStats] = useState<{users:number,papers:number,pending:number} | null>(null)

  /* ── Papers ──────────────────────────────────── */
  const [papers, setPapers] = useState<PaperRecord[]>([])
  const [papersTotal, setPapersTotal] = useState(0)
  const [papersPage, setPapersPage] = useState(1)
  const [papersStatus, setPapersStatus] = useState('')
  const [papersKeyword, setPapersKeyword] = useState('')
  const [papersMaterial, setPapersMaterial] = useState('')
  const [papersYearMin, setPapersYearMin] = useState('')
  const [papersYearMax, setPapersYearMax] = useState('')
  const [papersLoading, setPapersLoading] = useState(false)
  const [filterTick, setFilterTick] = useState(0)
  const [reviewDlg, setReviewDlg] = useState<{paper:PaperRecord,open:boolean}>({paper:null!,open:false})
  const [reviewStatus, setReviewStatus] = useState('')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewDetail, setReviewDetail] = useState<Record<string, any> | null>(null)
  const [reviewArtifact, setReviewArtifact] = useState<ReviewArtifact | null>(null)
  const [candidateAttachments, setCandidateAttachments] = useState<CandidateAttachment[]>([])
  const [reviewArtifactLoading, setReviewArtifactLoading] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  /* ── Edit Paper ──────────────────────────────── */
  const [editPaper, setEditPaper] = useState<{paper:PaperRecord|null,open:boolean}>({paper:null,open:false})
  const [editForm, setEditForm] = useState<Record<string,any>>({})
  const [editLoading, setEditLoading] = useState(false)

  /* ── Users ───────────────────────────────────── */
  const [users, setUsers] = useState<UserRecord[]>([])
  const [usersLoading, setUsersLoading] = useState(false)
  const [editUser, setEditUser] = useState<{user:UserRecord,open:boolean}>({user:null!,open:false})
  const [editRole, setEditRole] = useState('')
  const [editApproved, setEditApproved] = useState(true)
  const [renameUser, setRenameUser] = useState<UserRecord | null>(null)
  const [renameUsername, setRenameUsername] = useState('')
  const [renameReason, setRenameReason] = useState('')
  const [renameSaving, setRenameSaving] = useState(false)
  const [auditOpen, setAuditOpen] = useState(false)
  const [auditEvents, setAuditEvents] = useState<UsernameAuditEvent[]>([])
  const [auditLoading, setAuditLoading] = useState(false)

  /* ── Chart Groups ────────────────────────────── */
  const [chartGroups, setChartGroups] = useState<any[]>([])
  const [cgEditorOpen, setCgEditorOpen] = useState(false)
  const [cgEditingId, setCgEditingId] = useState<number | null>(null)

  /* ── Load ────────────────────────────────────── */
  const loadStats = useCallback(async () => {
    try {
      const [u, p] = await Promise.all([
        api.get<UserRecord[]>('/api/admin/all-users').catch(() => [] as UserRecord[]),
        api.get<{items:PaperRecord[],total:number}>('/api/admin/papers/all?limit=1&offset=0').catch(() => ({items:[],total:0})),
      ])
      setStats({
        users: Array.isArray(u) ? u.length : 0,
        papers: p.total || 0,
        pending: Array.isArray(u) ? u.filter(x=>!x.is_approved).length : 0,
      })
    } catch { /* ignore */ }
  }, [])

  const loadPapers = useCallback(async () => {
    setPapersLoading(true)
    try {
      const params = new URLSearchParams()
      params.set('limit','20'); params.set('offset', String((papersPage-1)*20))
      if (papersStatus) params.set('review_status', papersStatus)
      if (papersKeyword) params.set('keyword', papersKeyword)
      if (papersMaterial) params.set('material', papersMaterial)
      if (papersYearMin) params.set('year_min', papersYearMin)
      if (papersYearMax) params.set('year_max', papersYearMax)
      const res = await api.get<{items:PaperRecord[],total:number}>(`/api/admin/papers/all?${params}`)
      setPapers(res.items || [])
      setPapersTotal(res.total || 0)
    } catch { setPapers([]); setPapersTotal(0) }
    finally { setPapersLoading(false) }
  }, [papersPage, papersStatus, papersKeyword, papersMaterial, papersYearMin, papersYearMax, filterTick])

  const loadUsers = useCallback(async () => {
    if (!isSuper) return
    setUsersLoading(true)
    try {
      const res = await api.get<UserRecord[]>('/api/admin/all-users')
      setUsers(Array.isArray(res) ? res : [])
    } catch { setUsers([]) }
    finally { setUsersLoading(false) }
  }, [isSuper])

  const loadChartGroups = useCallback(async () => {
    try {
      const res = await api.get<any[]>('/api/chart-groups')
      setChartGroups(Array.isArray(res) ? res : [])
    } catch { setChartGroups([]) }
  }, [])

  useEffect(() => { loadStats() }, [loadStats])
  useEffect(() => { loadPapers() }, [loadPapers])
  useEffect(() => { loadUsers() }, [loadUsers])
  useEffect(() => { loadChartGroups() }, [loadChartGroups])

  /* ── Review actions ──────────────────────────── */
  const openReview = async (paper: PaperRecord) => {
    setReviewDlg({ paper, open: true })
    setReviewStatus(paper.review_status || 'pending')
    setReviewComment(paper.review_comment || '')
    setReviewDetail(null)
    setReviewArtifact(null)
    setCandidateAttachments([])
    setReviewArtifactLoading(true)
    try {
      const [detail, artifactResponse, attachmentResponse] = await Promise.all([
        api.get<Record<string, any>>(`/api/admin/papers/${paper.id}`),
        api.get<any>(`/api/rag/papers/${paper.id}/review-artifact`).catch(() => null),
        api.get<any>(`/api/rag/papers/${paper.id}/candidate-attachments`).catch(() => null),
      ])
      setReviewDetail(detail)
      if (artifactResponse) {
        const artifactData = unwrapData<any>(artifactResponse)
        setReviewArtifact({
          ai: normalizeUploadDraft(artifactData?.ai_values),
          user: normalizeUploadDraft(artifactData?.user_values),
          evidence: artifactData?.evidence || {},
        })
      }
      setCandidateAttachments(attachmentResponse ? unwrapData<CandidateAttachment[]>(attachmentResponse) : [])
    } catch (reason) {
      setSnackbar(`审核资料加载失败: ${(reason as Error).message}`)
    } finally {
      setReviewArtifactLoading(false)
    }
  }

  const downloadCandidateAttachment = async (attachment: CandidateAttachment) => {
    if (!reviewDlg.paper) return
    try {
      const blob = await api.download(
        `/api/rag/papers/${reviewDlg.paper.id}/candidate-attachments/${attachment.id}`,
      )
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = attachment.filename
      link.click()
      URL.revokeObjectURL(url)
    } catch (reason) {
      setSnackbar(`附件下载失败: ${(reason as Error).message}`)
    }
  }

  const handleReview = async () => {
    if (!reviewDlg.paper) return
    try {
      if (Array.isArray(reviewDetail?.key_properties)) {
        await api.put(`/api/admin/papers/${reviewDlg.paper.id}`, {
          key_properties: reviewDetail.key_properties.map((property: any) => ({
            id: property.id,
            material: property.material,
            name: property.name,
            superconductor_type: property.superconductor_type || null,
          })),
        })
      }
      await api.post(`/api/admin/papers/${reviewDlg.paper.id}/review`, {
        status: reviewStatus, comment: reviewComment, review_request_id: crypto.randomUUID(),
      })
      setSnackbar('审核完成')
      setReviewDlg({paper:null!,open:false})
      setReviewDetail(null)
      setReviewArtifact(null)
      loadPapers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  /* ── Edit paper ──────────────────────────────── */
  const handleEditOpen = async (p: PaperRecord) => {
    setEditLoading(true)
    try {
      const detail = await api.get<Record<string,any>>(`/api/admin/papers/${p.id}`)
      setEditForm(detail)
      setEditPaper({paper:p,open:true})
    } catch (e: unknown) { setSnackbar(`加载失败: ${(e as Error).message}`) }
    finally { setEditLoading(false) }
  }

  const handleEditSave = async () => {
    if (!editPaper.paper) return
    try {
      const payload: Record<string,any> = {...editForm}
      // 清理 key_properties，去掉只读字段
      if (payload.key_properties) {
        payload.key_properties = payload.key_properties.map((kp:any) => ({
          id: kp.id, material: kp.material, name: kp.name, name_raw: kp.name_raw,
          name_note: kp.name_note, value_min: kp.value_min, value_max: kp.value_max,
          value_raw: kp.value_raw, unit: kp.unit, pressure_gpa: kp.pressure_gpa,
          temperature_k: kp.temperature_k, is_primary: kp.is_primary,
          superconductor_type: kp.superconductor_type, article_type: kp.article_type,
          condition_note: kp.condition_note,
        }))
      }
      await api.put(`/api/admin/papers/${editPaper.paper.id}`, payload)
      setSnackbar('已保存')
      setEditPaper({paper:null,open:false})
      loadPapers()
    } catch (e: unknown) { setSnackbar(`保存失败: ${(e as Error).message}`) }
  }

  const handleBatchReview = async (status: string) => {
    if (selectedIds.size === 0) { setSnackbar('请先选择论文'); return }
    try {
      await api.post('/api/admin/papers/batch-review', {
        paper_ids: [...selectedIds], status, review_request_id: crypto.randomUUID(),
      })
      setSnackbar(`批量${STATUS_LABELS[status] || status}完成`)
      setSelectedIds(new Set())
      loadPapers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) { setSnackbar('请先选择论文'); return }
    if (!window.confirm(`确认删除 ${selectedIds.size} 篇论文？不可撤销！`)) return
    try {
      await api.post('/api/admin/papers/batch-delete', { paper_ids: [...selectedIds] })
      setSnackbar('批量删除完成')
      setSelectedIds(new Set())
      loadPapers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleDeletePaper = async (id: number) => {
    if (!window.confirm('确认删除？不可撤销！')) return
    try {
      await api.del(`/api/admin/papers/${id}`)
      setSnackbar('已删除')
      loadPapers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  /* ── User actions ────────────────────────────── */
  const handleUserSave = async () => {
    if (!editUser.user) return
    try {
      await api.put(`/api/admin/users/${editUser.user.id}/permissions`, {
        role: editRole, is_approved: editApproved,
      })
      setSnackbar('用户权限已更新')
      setEditUser({user:null!,open:false})
      loadUsers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleUsernameRename = async () => {
    if (!renameUser || !renameReason.trim()) return
    setRenameSaving(true)
    try {
      const result = await api.put<{ user: User }>(`/api/admin/users/${renameUser.id}/username`, {
        username: renameUsername, reason: renameReason.trim(),
      })
      if (renameUser.id === user?.id) replaceUser(result.user)
      setSnackbar('用户名已更新并记录审计')
      setRenameUser(null)
      setRenameUsername('')
      setRenameReason('')
      loadUsers()
    } catch (e: unknown) {
      setSnackbar(`失败: ${(e as Error).message}`)
    } finally {
      setRenameSaving(false)
    }
  }

  const openUsernameAudit = async () => {
    setAuditOpen(true)
    setAuditLoading(true)
    try {
      const events = await api.get<UsernameAuditEvent[]>('/api/admin/username-audit-events')
      setAuditEvents(Array.isArray(events) ? events : [])
    } catch (e: unknown) {
      setSnackbar(`失败: ${(e as Error).message}`)
      setAuditEvents([])
    } finally {
      setAuditLoading(false)
    }
  }

  const handleDeleteUser = async (id: number) => {
    if (!window.confirm('确认删除该用户？')) return
    try {
      await api.del(`/api/admin/users/${id}`)
      setSnackbar('已删除')
      loadUsers()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleDeleteGroup = async (id: number) => {
    if (!window.confirm('确认删除该组合？')) return
    try {
      await api.del(`/api/chart-groups/${id}`)
      setSnackbar('已删除')
      loadChartGroups()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleTogglePublic = async (id: number, isPublic: boolean) => {
    try {
      await api.patch(`/api/chart-groups/${id}/public`, { is_public: !isPublic })
      setSnackbar(isPublic ? '已设为私有' : '已设为公开')
      loadChartGroups()
    } catch (e: unknown) { setSnackbar(`失败: ${(e as Error).message}`) }
  }

  const handleToggleSelect = (id: number) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id); else next.add(id)
      return next
    })
  }

  /* ═══════════════════════════════════════════════ */
  /* ═══════════════════════════════════════════════ */

  return (
    <Box sx={{ maxWidth: 1280, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="overline" color="text.secondary">管理后台</Typography>
          <Typography variant="h4" fontWeight={800}>SC-Wiki Admin</Typography>
        </Box>
      </Box>

      <Tabs value={tab} onChange={(_,v)=>setTab(v)} sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}>
        <Tab label="概览" />
        <Tab label={`论文审核${papersStatus === 'pending' ? ` (${papersTotal})` : ''}`} />
        {isSuper && <Tab label="用户管理" icon={<AdminIcon fontSize="small" />} iconPosition="start" />}
        <Tab label="图表管理" />
        <Tab label="快讯管理" />
      </Tabs>

      {/* ═══════════════════════════════════════════ */}
      {/* TAB 0: Dashboard */}
      {/* ═══════════════════════════════════════════ */}
      {tab === 0 && (
        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 2 }}>
          <Card sx={{ borderLeft: '4px solid', borderColor: 'primary.main' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">用户总数</Typography>
              <Typography variant="h3" fontWeight={700}>{stats?.users ?? '…'}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '4px solid', borderColor: 'success.main' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">论文总数</Typography>
              <Typography variant="h3" fontWeight={700}>{stats?.papers ?? '…'}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '4px solid', borderColor: 'warning.main' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">待审批管理员</Typography>
              <Typography variant="h3" fontWeight={700}>{stats?.pending ?? '…'}</Typography>
            </CardContent>
          </Card>
          <Card sx={{ borderLeft: '4px solid', borderColor: 'info.main' }}>
            <CardContent>
              <Typography variant="caption" color="text.secondary">当前角色</Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                <Chip size="small" color="error" label="超级管理员" />
                <Typography variant="h6" fontWeight={700}>{user?.username}</Typography>
              </Box>
            </CardContent>
          </Card>
        </Box>
      )}

      {/* ═══════════════════════════════════════════ */}
      {/* TAB 1: Paper Review */}
      {/* ═══════════════════════════════════════════ */}
      {tab === 1 && (
        <Box>
          {/* Toolbar */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField size="small" placeholder="搜索标题/DOI/期刊…" sx={{ minWidth: 240 }}
              value={papersKeyword}
              onChange={e => setPapersKeyword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setPapersPage(1); setFilterTick(t=>t+1); }}} />
            <TextField size="small" placeholder="Formula" sx={{ width: 150 }}
              value={papersMaterial}
              onChange={e => setPapersMaterial(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setPapersPage(1); setFilterTick(t=>t+1); }}} />
            <TextField size="small" label="年份起" type="number" sx={{ width: 100 }}
              value={papersYearMin}
              onChange={e => { setPapersYearMin(e.target.value); setPapersPage(1); }}
              slotProps={{ htmlInput: { min: 1900, max: 2099 } }} />
            <TextField size="small" label="年份止" type="number" sx={{ width: 100 }}
              value={papersYearMax}
              onChange={e => { setPapersYearMax(e.target.value); setPapersPage(1); }}
              slotProps={{ htmlInput: { min: 1900, max: 2099 } }} />
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>审核状态</InputLabel>
              <Select value={papersStatus} label="审核状态"
                onChange={e => { setPapersStatus(e.target.value); setPapersPage(1); }}>
                <MenuItem value="">全部</MenuItem>
                <MenuItem value="pending">待审核</MenuItem>
                <MenuItem value="approved">已通过</MenuItem>
                <MenuItem value="rejected">已拒绝</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" size="small" sx={{ minWidth: 80 }}
              onClick={() => { setPapersPage(1); setFilterTick(t=>t+1); }}>
              搜索
            </Button>
            <Box sx={{ flex: 1 }} />
            {selectedIds.size > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <Chip label={`已选 ${selectedIds.size}`} size="small" color="primary" onDelete={()=>setSelectedIds(new Set())} />
                <Button size="small" color="success" variant="contained" onClick={()=>handleBatchReview('approved')}>批量通过</Button>
                <Button size="small" color="error" variant="outlined" onClick={()=>handleBatchReview('rejected')}>批量拒绝</Button>
                {isSuper && <Button size="small" color="error" variant="contained" onClick={handleBatchDelete}>批量删除</Button>}
              </Box>
            )}
          </Box>

          {/* Table */}
          {papersLoading && <LinearProgress sx={{ mb: 1 }} />}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell padding="checkbox" sx={{ width: 40 }}>#</TableCell>
                  <TableCell sx={{ minWidth: 260 }}>标题</TableCell>
                  <TableCell sx={{ width: 80 }}>年份</TableCell>
                  <TableCell sx={{ width: 100 }}>上传者</TableCell>
                  <TableCell sx={{ width: 80 }}>状态</TableCell>
                  <TableCell sx={{ width: 100 }}>类型</TableCell>
                  <TableCell sx={{ width: 120 }} align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {papers.map(p => (
                  <TableRow key={p.id} hover selected={selectedIds.has(p.id)}>
                    <TableCell padding="checkbox">
                      <input type="checkbox" checked={selectedIds.has(p.id)} onChange={()=>handleToggleSelect(p.id)}
                        style={{ cursor: 'pointer' }} />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600} noWrap sx={{ maxWidth: 300 }}>
                        {p.title || '(无标题)'}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {p.doi || p.journal || ''}
                      </Typography>
                    </TableCell>
                    <TableCell>{p.year || '-'}</TableCell>
                    <TableCell>
                      <Typography variant="body2" noWrap sx={{ maxWidth: 100 }}>{p.uploader_name || '-'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={STATUS_LABELS[p.review_status] || p.review_status}
                        color={STATUS_COLORS[p.review_status] || 'default'} />
                    </TableCell>
                    <TableCell>
                      <Box sx={{ display: 'flex', gap: 0.25, flexWrap: 'wrap' }}>
                        {paperSuperconductorTypes(p).slice(0,2).map(t=>(
                          <Chip key={t} label={t} size="small" variant="outlined" sx={{fontSize:10,height:18}} />
                        ))}
                      </Box>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title="编辑"><IconButton size="small" color="info"
                          onClick={()=>handleEditOpen(p)}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        <Tooltip title="审核"><IconButton size="small" color="primary"
                          onClick={() => void openReview(p)}>
                          <ReviewIcon fontSize="small" /></IconButton></Tooltip>
                        {isSuper && (
                          <Tooltip title="删除"><IconButton size="small" color="error"
                            onClick={()=>handleDeletePaper(p.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
                {papers.length === 0 && !papersLoading && (
                  <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>暂无数据</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>
          {papersTotal > 20 && (
            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
              <Pagination count={Math.ceil(papersTotal/20)} page={papersPage}
                onChange={(_,p)=>setPapersPage(p)} color="primary" />
            </Box>
          )}
        </Box>
      )}

      {/* ═══════════════════════════════════════════ */}
      {/* TAB 2: User Management (superadmin only) */}
      {/* ═══════════════════════════════════════════ */}
      {tab === 2 && isSuper && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
            <Button variant="outlined" size="small" startIcon={<HistoryIcon />} onClick={() => void openUsernameAudit()}>
              更名审计
            </Button>
          </Box>
          {usersLoading && <LinearProgress sx={{ mb: 1 }} />}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>用户</TableCell>
                  <TableCell sx={{ width: 80 }}>角色</TableCell>
                  <TableCell sx={{ width: 80 }}>审批</TableCell>
                  <TableCell sx={{ width: 80 }}>邮箱验证</TableCell>
                  <TableCell sx={{ width: 80 }}>提交/审核</TableCell>
                  <TableCell sx={{ width: 140 }}>注册时间</TableCell>
                  <TableCell sx={{ width: 100 }} align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {users.map(u => (
                  <TableRow key={u.id} hover sx={{ opacity: u.id === user?.id ? undefined : 1, bgcolor: u.id === user?.id ? 'action.hover' : undefined }}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Avatar sx={{ width: 28, height: 28, fontSize: 12, bgcolor: u.role==='superadmin'?'error.main':u.role==='admin'?'primary.main':'grey.400' }}>
                          {u.username.charAt(0).toUpperCase()}
                        </Avatar>
                        <Box>
                          <Typography variant="body2" fontWeight={600}>{u.username}</Typography>
                          <Typography variant="caption" color="text.secondary">{u.email}</Typography>
                        </Box>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={ROLE_LABELS[u.role] || u.role}
                        color={ROLE_COLORS[u.role] || 'default'} />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={u.is_approved ? '已批准' : '待审批'}
                        color={u.is_approved ? 'success' : 'warning'} />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={u.is_email_verified ? '已验证' : '未验证'}
                        color={u.is_email_verified ? 'success' : 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{u.submitted_count} / {u.reviewed_count}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString('zh-CN') : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title="修改用户名"><IconButton size="small"
                          onClick={()=>{setRenameUser(u);setRenameUsername(u.username);setRenameReason('')}}>
                          <RenameIcon fontSize="small" /></IconButton></Tooltip>
                        <Tooltip title="编辑权限"><IconButton size="small" color="primary"
                          onClick={()=>{setEditUser({user:u,open:true});setEditRole(u.role);setEditApproved(u.is_approved)}}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        {u.id !== user?.id && (
                          <Tooltip title="删除用户"><IconButton size="small" color="error"
                            onClick={()=>handleDeleteUser(u.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </Box>
      )}

      {/* ═══════════════════════════════════════════ */}
      {/* TAB: Chart Groups */}
      {/* ═══════════════════════════════════════════ */}
      {tab === (isSuper ? 4 : 3) && (
        /* ── News Management ── */
        <Box>
          <NewsManager />
        </Box>
      )}
      {tab === (isSuper ? 3 : 2) && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
            <Typography variant="h6" fontWeight={600} sx={{ flex: 1 }}>图表组合管理</Typography>
            <Button variant="contained" size="small" onClick={() => { setCgEditingId(null); setCgEditorOpen(true); }}>
              + 新建组合
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>名称</TableCell>
                  <TableCell sx={{ width: 100 }}>数据点</TableCell>
                  <TableCell sx={{ width: 60 }}>预设</TableCell>
                  <TableCell sx={{ width: 60 }}>公开</TableCell>
                  <TableCell sx={{ width: 100 }}>创建者</TableCell>
                  <TableCell sx={{ width: 100 }}>更新时间</TableCell>
                  <TableCell sx={{ width: 120 }} align="right">操作</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {chartGroups.map((g: any) => (
                  <TableRow key={g.id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight={600}>{g.name}</Typography>
                      <Typography variant="caption" color="text.secondary">{g.description || '-'}</Typography>
                    </TableCell>
                    <TableCell>{g.item_count || 0}</TableCell>
                    <TableCell>
                      <Chip size="small" label={g.is_preset ? '是' : '否'} color={g.is_preset ? 'primary' : 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {isSuper || user?.role === 'admin' ? (
                        <Chip size="small" label={g.is_public ? '公开' : '私有'}
                          color={g.is_public ? 'success' : 'default'} variant="outlined"
                          onClick={() => handleTogglePublic(g.id, g.is_public)}
                          sx={{ cursor: 'pointer' }} />
                      ) : (
                        <Chip size="small" label={g.is_public ? '公开' : '私有'}
                          color={g.is_public ? 'success' : 'default'} variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>{g.creator_name || '-'}</TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {g.updated_at ? new Date(g.updated_at).toLocaleDateString('zh-CN') : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title="编辑"><IconButton size="small" color="primary"
                          onClick={() => { setCgEditingId(g.id); setCgEditorOpen(true); }}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        {!g.is_preset && (
                          <Tooltip title="删除"><IconButton size="small" color="error"
                            onClick={() => handleDeleteGroup(g.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
                {chartGroups.length === 0 && (
                  <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>暂无组合</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </TableContainer>

          <ChartGroupEditor
            open={cgEditorOpen}
            groupId={cgEditingId}
            onClose={() => setCgEditorOpen(false)}
            onSaved={() => { loadChartGroups(); }}
          />
        </Box>
      )}

      {/* ═══════════════════════════════════════════ */}
      {/* Review Dialog */}
      {/* ═══════════════════════════════════════════ */}
      <Dialog open={reviewDlg.open} onClose={()=>setReviewDlg({paper:null!,open:false})} maxWidth="md" fullWidth>
        <DialogTitle>审核论文</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,mt:1 }}>
          <Typography variant="body2" fontWeight={600} noWrap>
            {reviewDlg.paper?.title || '(无标题)'}
          </Typography>
          <Box sx={{ display:'flex',gap:1,flexWrap:'wrap' }}>
            <Chip size="small" label={`DOI: ${reviewDlg.paper?.doi || '-'}`} variant="outlined" />
            <Chip size="small" label={`年份: ${reviewDlg.paper?.year || '-'}`} variant="outlined" />
            <Chip size="small" label={`记录: ${paperRecordCount(reviewDlg.paper)}`} variant="outlined" />
          </Box>
          <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>AI 建议、用户提交与原文证据</Typography>
            {reviewArtifactLoading ? (
              <LinearProgress />
            ) : !reviewArtifact ? (
              <Alert severity="info">临时证据已清理或当前记录没有可用证据，不阻断审核。</Alert>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.25 }}>
                {[
                  ['论文类型', reviewArtifact.ai.paper.paper_type, reviewDetail?.paper_type || reviewArtifact.user.paper.paper_type],
                  ['理论二级类型', reviewArtifact.ai.paper.theoretical_subtype, reviewDetail?.theoretical_subtype || reviewArtifact.user.paper.theoretical_subtype],
                  ['超导材料类型', reviewArtifact.ai.sc_type, reviewArtifact.user.sc_type],
                  ['分类理由', reviewArtifact.ai.classification_reason, reviewArtifact.user.classification_reason],
                ].map(([label, aiValue, userValue]) => (
                  <Box key={String(label)} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '120px 1fr 1fr' }, gap: 1 }}>
                    <Typography variant="caption" fontWeight={700}>{String(label)}</Typography>
                    <Typography variant="caption" color="text.secondary">AI：{aiValue == null || aiValue === '' ? '未提供' : String(aiValue)}</Typography>
                    <Typography variant="caption">提交：{userValue == null || userValue === '' ? '未提供' : String(userValue)}</Typography>
                  </Box>
                ))}
                {(reviewArtifact.evidence.classification || reviewArtifact.user.classification_evidence || []).map((item, index) => (
                  <Box key={index} sx={{ pl: 1.25, borderLeft: '3px solid', borderColor: 'info.light' }}>
                    <Typography variant="caption" color="text.secondary">
                      {[item.section, item.page ? `第 ${item.page} 页` : ''].filter(Boolean).join(' · ') || '原文'}
                      {item.quote ? `：“${item.quote}”` : ''}
                    </Typography>
                  </Box>
                ))}
                {reviewArtifact.user.key_properties.map((property, index) => (
                  <Box key={index} sx={{ p: 1.25, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="caption" fontWeight={700} display="block">
                      物性 #{index + 1}：{property.material || '-'} · {property.name || property.name_raw || '-'} · {property.value_raw || property.value_max || property.value_min || '-'} {property.unit || ''}
                    </Typography>
                    {(Array.isArray(reviewArtifact.evidence.key_properties?.[index])
                      ? reviewArtifact.evidence.key_properties?.[index] as SourceEvidence[]
                      : reviewArtifact.evidence.key_properties?.[index]
                        ? [reviewArtifact.evidence.key_properties[index] as SourceEvidence]
                        : Array.isArray(property.evidence) ? property.evidence : property.evidence ? [property.evidence] : []
                    ).map((item, itemIndex) => (
                      <Typography key={itemIndex} variant="caption" color="text.secondary" display="block">
                        {[item.section, item.page ? `第 ${item.page} 页` : ''].filter(Boolean).join(' · ') || '原文'}
                        {item.quote ? `：“${item.quote}”` : ''}
                      </Typography>
                    ))}
                  </Box>
                ))}
              </Box>
            )}
          </Box>
          {(reviewDetail?.key_properties || []).length > 0 && (
            <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>确认最终材料类型</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {(reviewDetail?.key_properties || []).map((property: any, index: number) => (
                  <TextField key={property.id || index} size="small" fullWidth
                    label={property.material || `物性 #${index + 1}`}
                    value={property.superconductor_type || ''}
                    onChange={event => setReviewDetail(current => {
                      if (!current) return current
                      const properties = [...(current.key_properties || [])]
                      properties[index] = { ...properties[index], superconductor_type: event.target.value }
                      return { ...current, key_properties: properties }
                    })} />
                ))}
              </Box>
            </Box>
          )}
          {candidateAttachments.length > 0 && (
            <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>同 DOI 候选附件</Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {candidateAttachments.map(attachment => (
                  <Box key={attachment.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ flex: 1, minWidth: 0 }}>
                      <Typography variant="body2" noWrap>{attachment.filename}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {(attachment.file_size / 1024 / 1024).toFixed(2)} MB · SHA-256 {attachment.file_sha256?.slice(0, 12) || '-'}
                      </Typography>
                    </Box>
                    <Tooltip title="下载候选附件">
                      <IconButton size="small" onClick={() => void downloadCandidateAttachment(attachment)}>
                        <DownloadIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </Box>
                ))}
              </Box>
            </Box>
          )}
          <FormControl fullWidth size="small">
            <InputLabel>审核结果</InputLabel>
            <Select value={reviewStatus} label="审核结果" onChange={e=>setReviewStatus(e.target.value)}>
              <MenuItem value="approved">✅ 通过</MenuItem>
              <MenuItem value="rejected">❌ 拒绝</MenuItem>
              <MenuItem value="pending">退回待审核</MenuItem>
            </Select>
          </FormControl>
          <TextField label="审核意见" multiline rows={3} size="small" fullWidth
            value={reviewComment} onChange={e=>setReviewComment(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setReviewDlg({paper:null!,open:false})}>取消</Button>
          <Button variant="contained" onClick={handleReview}>确认审核</Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════ */}
      {/* Edit Paper Dialog */}
      {/* ═══════════════════════════════════════════ */}
      <Dialog open={editPaper.open} onClose={()=>setEditPaper({paper:null,open:false})} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display:'flex',justifyContent:'space-between',alignItems:'center' }}>
            <Typography variant="h6" fontWeight={600}>编辑论文</Typography>
            {editLoading && <CircularProgress size={20} />}
          </Box>
        </DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:1.5,mt:1 }}>
          <TextField label="标题" size="small" fullWidth multiline rows={2}
            value={editForm.title || ''} onChange={e=>setEditForm({...editForm,title:e.target.value})} />
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:1.5 }}>
            <TextField label="DOI" size="small" value={editForm.doi || ''}
              onChange={e=>setEditForm({...editForm,doi:e.target.value})} />
            <TextField label="期刊" size="small" value={editForm.journal || ''}
              onChange={e=>setEditForm({...editForm,journal:e.target.value})} />
            <TextField label="年份" size="small" type="number" value={editForm.year || ''}
              onChange={e=>setEditForm({...editForm,year:e.target.value ? Number(e.target.value) : null})} />
          </Box>
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
            <TextField label="卷" size="small" value={editForm.volume || ''}
              onChange={e=>setEditForm({...editForm,volume:e.target.value})} />
            <TextField label="页" size="small" value={editForm.pages || ''}
              onChange={e=>setEditForm({...editForm,pages:e.target.value})} />
          </Box>
          <TextField label="作者" size="small" fullWidth multiline rows={2}
            helperText="JSON 数组格式"
            value={typeof editForm.authors === 'string' ? editForm.authors : JSON.stringify(editForm.authors || [], null, 2)}
            onChange={e=>{ try { setEditForm({...editForm,authors:JSON.parse(e.target.value)}) } catch { setEditForm({...editForm,authors:e.target.value}) }}} />
          <TextField label="摘要" size="small" fullWidth multiline rows={3}
            value={editForm.abstract || ''} onChange={e=>setEditForm({...editForm,abstract:e.target.value})} />
          <TextField label="LLM 摘要 (summary)" size="small" fullWidth multiline rows={2}
            value={editForm.summary || ''} onChange={e=>setEditForm({...editForm,summary:e.target.value})} />
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:1.5 }}>
            <TextField label="论文类型 (paper_type)" size="small" value={editForm.paper_type || ''}
              onChange={e=>setEditForm({...editForm,paper_type:e.target.value})} />
            <TextField label="关键词 (keywords_tags)" size="small" value={editForm.keywords_tags || ''}
              onChange={e=>setEditForm({...editForm,keywords_tags:e.target.value})} />
            <TextField label="源文件 (source_file_path)" size="small" value={editForm.source_file_path || ''}
              onChange={e=>setEditForm({...editForm,source_file_path:e.target.value})} />
          </Box>
          <TextField label="研究方法 (methodology)" size="small" fullWidth multiline rows={2}
            value={typeof editForm.methodology === 'string' ? editForm.methodology : JSON.stringify(editForm.methodology || [], null, 2)}
            onChange={e=>{ try { setEditForm({...editForm,methodology:JSON.parse(e.target.value)}) } catch { setEditForm({...editForm,methodology:e.target.value})}}} />
          <TextField label="核心发现 (key_finding)" size="small" fullWidth multiline rows={2}
            value={editForm.key_finding || ''} onChange={e=>setEditForm({...editForm,key_finding:e.target.value})} />
          <TextField label="研究理由 (rationale)" size="small" fullWidth multiline rows={2}
            value={editForm.rationale || ''} onChange={e=>setEditForm({...editForm,rationale:e.target.value})} />
          {/* Non-editable metadata */}
          <Box sx={{ display:'flex',gap:1,flexWrap:'wrap',mt:0.5 }}>
            <Chip size="small" label={`ID: ${editForm.id || '-'}`} variant="outlined" />
            <Chip size="small" label={`物性数: ${editForm.record_count || 0}`} variant="outlined" />
            <Chip size="small" label={`创建: ${editForm.created_at ? new Date(editForm.created_at).toLocaleString('zh-CN') : '-'}`} />
            {(editForm.materials || []).map((m:string)=>(
              <Chip key={m} size="small" label={m} color="primary" variant="outlined" />
            ))}
          </Box>

          {/* Key Properties */}
          {(editForm.key_properties || []).length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                物性数据 ({editForm.key_properties.length})
              </Typography>
              <Box sx={{ display:'flex',flexDirection:'column',gap:1.5, maxHeight: 480, overflow:'auto' }}>
                {(editForm.key_properties || []).map((kp:any, i:number) => {
                  const setKp = (f:string, v:any) => {
                    const n = [...(editForm.key_properties||[])]
                    n[i] = {...n[i], [f]: v}
                    setEditForm({...editForm, key_properties:n})
                  }
                  return (
                  <Box key={kp.id || i} sx={{
                    p:1.5, borderRadius:1, bgcolor: kp.is_primary ? '#eef2ff' : 'grey.50',
                    border:'1px solid', borderColor: kp.is_primary ? '#818cf8' : 'divider',
                  }}>
                    {/* KP header */}
                    <Box sx={{ display:'flex',alignItems:'center',gap:1,mb:1 }}>
                      <Chip size="small" label={`#${i+1}`} variant="outlined" />
                      {kp.is_primary && <Chip size="small" label="主要物性" color="primary" />}
                      <Typography variant="caption" color="text.secondary">
                        ID: {kp.id} · source: {kp.name_raw || '-'}
                      </Typography>
                    </Box>
                    {/* Row 1: 核心数值 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:1 }}>
                      <TextField label="材料 (material)" size="small" value={kp.material || ''}
                        onChange={e=>setKp('material',e.target.value)} />
                      <TextField label="物性名 (name)" size="small" value={kp.name || ''}
                        onChange={e=>setKp('name',e.target.value)} />
                      <FormControlLabel control={
                        <Checkbox checked={!!kp.is_primary} size="small"
                          onChange={e=>setKp('is_primary',e.target.checked)} />
                      } label="主要物性" sx={{ m:0 }} />
                      <FormControl size="small">
                        <InputLabel>物性名备注</InputLabel>
                        <Select value={kp.name_note || ''} label="物性名备注"
                          onChange={e=>setKp('name_note',e.target.value)}>
                          <MenuItem value="">-</MenuItem>
                          <MenuItem value="temperature/position dependent">温度/位置依赖</MenuItem>
                          <MenuItem value="pressure dependent">压强依赖</MenuItem>
                          <MenuItem value="doping dependent">掺杂依赖</MenuItem>
                          <MenuItem value="dynamically stable">动力学稳定</MenuItem>
                          <MenuItem value="thermodynamically stable">热力学稳定</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    {/* Row 2: 数值 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr 1fr',gap:1,mt:1 }}>
                      <TextField label="最小值 (value_min)" size="small" type="number"
                        value={kp.value_min ?? ''} onChange={e=>setKp('value_min',e.target.value?Number(e.target.value):null)} />
                      <TextField label="最大值 (value_max)" size="small" type="number"
                        value={kp.value_max ?? ''} onChange={e=>setKp('value_max',e.target.value?Number(e.target.value):null)} />
                      <TextField label="原始值 (value_raw)" size="small"
                        value={kp.value_raw || ''} onChange={e=>setKp('value_raw',e.target.value)} />
                      <TextField label="单位 (unit)" size="small"
                        value={kp.unit || ''} onChange={e=>setKp('unit',e.target.value)} />
                      <TextField label="原始物性名 (name_raw)" size="small"
                        value={kp.name_raw || ''} onChange={e=>setKp('name_raw',e.target.value)} />
                    </Box>
                    {/* Row 3: 条件与分类 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:1,mt:1 }}>
                      <TextField label="压强 (pressure_gpa, GPa)" size="small" type="number"
                        value={kp.pressure_gpa ?? ''} onChange={e=>setKp('pressure_gpa',e.target.value?Number(e.target.value):null)} />
                      <TextField label="温度 (temperature_k, K)" size="small" type="number"
                        value={kp.temperature_k ?? ''} onChange={e=>setKp('temperature_k',e.target.value?Number(e.target.value):null)} />
                      <FormControl size="small">
                        <InputLabel>文献类型 (article_type)</InputLabel>
                        <Select value={kp.article_type || ''} label="文献类型 (article_type)"
                          onChange={e=>setKp('article_type',e.target.value)}>
                          <MenuItem value="">-</MenuItem>
                          <MenuItem value="e">e · 实验</MenuItem>
                          <MenuItem value="t">t · 理论</MenuItem>
                        </Select>
                      </FormControl>
                      <FormControl size="small">
                        <InputLabel>超导类型 (sc_type)</InputLabel>
                        <Select value={kp.superconductor_type || ''} label="超导类型 (sc_type)"
                          onChange={e=>setKp('superconductor_type',e.target.value)}>
                          <MenuItem value="">-</MenuItem>
                          <MenuItem value="hydride">hydride · 氢化物</MenuItem>
                          <MenuItem value="cuprate">cuprate · 铜基</MenuItem>
                          <MenuItem value="iron_based">iron_based · 铁基</MenuItem>
                          <MenuItem value="nickel_based">nickel_based · 镍基</MenuItem>
                          <MenuItem value="carbon">carbon · 碳基</MenuItem>
                          <MenuItem value="organic">organic · 有机</MenuItem>
                          <MenuItem value="others">others · 其他</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    {/* Row 4: notes */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:1 }}>
                      <TextField label="条件备注 (condition_note)" size="small"
                        value={kp.condition_note || ''} onChange={e=>setKp('condition_note',e.target.value)} />
                      <TextField label="物性备注 (name_note)" size="small"
                        value={kp.name_note || ''} onChange={e=>setKp('name_note',e.target.value)} />
                    </Box>
                  </Box>
                )})}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setEditPaper({paper:null,open:false})}>取消</Button>
          <Button variant="contained" onClick={handleEditSave}>保存修改</Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════ */}
      {/* Edit User Dialog */}
      {/* ═══════════════════════════════════════════ */}
      <Dialog open={editUser.open} onClose={()=>setEditUser({user:null!,open:false})} maxWidth="xs" fullWidth>
        <DialogTitle>编辑用户权限</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,mt:1 }}>
          <Typography variant="body2" fontWeight={600}>
            {editUser.user?.username} ({editUser.user?.email})
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>角色</InputLabel>
            <Select value={editRole} label="角色" onChange={e=>setEditRole(e.target.value)}>
              <MenuItem value="user">普通用户</MenuItem>
              <MenuItem value="admin">管理员</MenuItem>
              <MenuItem value="superadmin">超级管理员</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel>审批状态</InputLabel>
            <Select value={editApproved ? 'approved':'pending'} label="审批状态"
              onChange={e=>setEditApproved(e.target.value==='approved')}>
              <MenuItem value="approved">已批准</MenuItem>
              <MenuItem value="pending">待审批</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setEditUser({user:null!,open:false})}>取消</Button>
          <Button variant="contained" onClick={handleUserSave}>保存</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!renameUser} onClose={()=>!renameSaving&&setRenameUser(null)} maxWidth="xs" fullWidth>
        <DialogTitle>修改用户名</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,pt:'12px !important' }}>
          <Alert severity="warning">更名会立即改变公开贡献身份，并写入不可变审计记录。</Alert>
          <UsernameField value={renameUsername} onChange={setRenameUsername} autoFocus />
          <TextField label="更名原因" value={renameReason} onChange={e=>setRenameReason(e.target.value)}
            required multiline minRows={2} inputProps={{ maxLength: 500 }} helperText={`${renameReason.length}/500`} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setRenameUser(null)} disabled={renameSaving}>取消</Button>
          <Button variant="contained" onClick={()=>void handleUsernameRename()}
            disabled={renameSaving || !renameUsername || !renameReason.trim() || renameUsername === renameUser?.username}>
            {renameSaving ? <CircularProgress size={18} /> : '确认更名'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={auditOpen} onClose={()=>setAuditOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>用户名更名审计</DialogTitle>
        <DialogContent>
          {auditLoading ? <LinearProgress /> : auditEvents.length === 0 ? (
            <Alert severity="info">暂无更名记录</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead><TableRow>
                  <TableCell>时间</TableCell><TableCell>变更</TableCell><TableCell>操作者</TableCell><TableCell>原因</TableCell>
                </TableRow></TableHead>
                <TableBody>{auditEvents.map(event => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.created_at).toLocaleString('zh-CN')}</TableCell>
                    <TableCell>{event.old_username} → {event.new_username}</TableCell>
                    <TableCell>{event.changed_by_username}</TableCell>
                    <TableCell>{event.reason}</TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions><Button onClick={()=>setAuditOpen(false)}>关闭</Button></DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={()=>setSnackbar('')}
        anchorOrigin={{vertical:'bottom',horizontal:'center'}}>
        <Alert severity="info" variant="filled" onClose={()=>setSnackbar('')}>{snackbar}</Alert>
      </Snackbar>
    </Box>
  )
}

export default AdminPage
