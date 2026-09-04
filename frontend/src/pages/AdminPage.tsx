import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Card, CardActionArea, CardContent, Button, Chip,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, IconButton, Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel, Alert, Divider, Link,
  Snackbar, CircularProgress, LinearProgress, Avatar, Tooltip,
  Pagination,
} from '@mui/material'
import {
  Delete as DeleteIcon,
  Edit as EditIcon,
  Gavel as ReviewIcon,
  DriveFileRenameOutline as RenameIcon,
  History as HistoryIcon,
} from '@mui/icons-material'
import { type User, useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { Link as RouterLink, useNavigate } from 'react-router-dom'
import ChartGroupEditor from '../components/ChartGroupEditor'
import NewsManager from '../components/NewsManager'
import SuperAdminGovernance from '../components/SuperAdminGovernance'
import UsernameField from '../components/UsernameField'
import DefaultLlmConfigPanel from '../components/DefaultLlmConfigPanel'
import { useLanguage } from '../context/LanguageContext'

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
  show_in_chart: boolean
  compound_symbols: string | null; article_types: string[]
  key_properties?: Array<Record<string, unknown>>
}

type PaperHistoryEvent = {
  id: number
  event_type: 'uploaded' | 'modified' | 'reviewed'
  paper_revision: number
  actor: { username: string | null; unknown: boolean }
  occurred_at: string
  review: { status: 'approved' | 'rejected' | 'pending'; comment: string | null } | null
}

/* ── Helpers ──────────────────────────────────── */
const ROLE_COLORS: Record<string, 'error'|'primary'|'default'> = {
  superadmin: 'error', admin: 'primary', user: 'default',
}
const STATUS_COLORS: Record<string, 'warning'|'success'|'error'|'info'> = {
  pending: 'warning', approved: 'success', rejected: 'error', needs_revision: 'info',
}

/** 工作台卡片式功能入口；替代原顶部 Tabs 导航（Issue #61）。 */
const WORKSPACE_CARDS: Array<{
  key: string
  labelKey: string
  hintKey: string
  accent: string
  tab: number
  metric: 'users' | 'papers' | 'pending' | 'chartGroups' | 'none'
  superOnly?: boolean
}> = [
  { key: 'users', labelKey: 'admin.usersPermissions', hintKey: 'admin.cardHintManage', accent: 'primary.main', tab: 2, metric: 'users', superOnly: true },
  { key: 'papers', labelKey: 'admin.cardPapers', hintKey: 'admin.cardHintReview', accent: 'success.main', tab: 1, metric: 'papers' },
  { key: 'pending', labelKey: 'admin.cardPendingAdmins', hintKey: 'admin.cardHintApprove', accent: 'warning.main', tab: 2, metric: 'pending', superOnly: true },
  { key: 'chartGroups', labelKey: 'admin.cardChartGroups', hintKey: 'admin.cardHintManage', accent: 'secondary.main', tab: 3, metric: 'chartGroups', superOnly: true },
  { key: 'news', labelKey: 'admin.newsTitle', hintKey: 'admin.cardHintManage', accent: 'error.main', tab: 4, metric: 'none', superOnly: true },
]
/* ═══════════════════════════════════════════════ */
interface AdminPageProps { mode?: 'admin' | 'superadmin' }

const AdminPage: React.FC<AdminPageProps> = ({ mode = 'admin' }) => {
  const { user, replaceUser } = useAuth()
  const { t, lang, dict } = useLanguage()
  const navigate = useNavigate()
  const isSuper = mode === 'superadmin'
  const locale = lang === 'zh' ? 'zh-CN' : 'en-US'

  // 审核状态标签按本页历史文案（admin.reviewStatus）取：enums.ts 的 approved 为
  // 「审核完成」，而列表/筛选/批量提示一直显示「已通过」，既有测试依赖原文。
  const reviewStatusLabel = (value: string): string => {
    const labels = dict.admin.reviewStatus
    return labels[value as keyof typeof labels] || value
  }
  const roleLabel = (value: string): string => {
    const labels = dict.enums.role
    return labels[value as keyof typeof labels] || value
  }

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
  const [historyPaper, setHistoryPaper] = useState<PaperRecord | null>(null)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [historyEvents, setHistoryEvents] = useState<PaperHistoryEvent[]>([])
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

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
      const p = await api.get<{items:PaperRecord[],total:number}>('/api/admin/papers/all?limit=1&offset=0')
      const u = isSuper ? await api.get<UserRecord[]>('/api/superadmin/users') : []
      const applications = isSuper ? await api.get<Array<{status:string}>>('/api/superadmin/admin-applications?status=pending') : []
      setStats({
        users: Array.isArray(u) ? u.length : 0,
        papers: p.total || 0,
        pending: applications.length,
      })
    } catch { /* ignore */ }
  }, [isSuper])

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
  useEffect(() => { if (isSuper) void loadChartGroups() }, [isSuper, loadChartGroups])

  /* ── Review actions ──────────────────────────── */
  const openReview = async (paper: PaperRecord) => {
    setReviewDlg({ paper, open: true })
    setReviewStatus(paper.review_status === 'rejected' ? 'rejected' : 'pending')
    setReviewComment(paper.review_comment || '')
  }

  const handleReview = async () => {
    if (!reviewDlg.paper) return
    try {
      await api.post(`/api/admin/papers/${reviewDlg.paper.id}/review`, {
        status: reviewStatus, comment: reviewComment, review_request_id: crypto.randomUUID(),
      })
      setSnackbar(t('admin.reviewDone'))
      setReviewDlg({paper:null!,open:false})
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const loadPaperHistory = async (paperID: number) => {
    setHistoryLoading(true)
    setHistoryError('')
    try {
      const response = await api.get<{ events?: PaperHistoryEvent[] }>(`/api/admin/papers/${paperID}/history`)
      setHistoryEvents(Array.isArray(response.events) ? response.events : [])
    } catch (e: unknown) {
      setHistoryError(t('admin.historyLoadFailed', { reason: (e as Error).message }))
    } finally {
      setHistoryLoading(false)
    }
  }

  const openPaperHistory = (paper: PaperRecord) => {
    setHistoryPaper(paper)
    setHistoryEvents([])
    void loadPaperHistory(paper.id)
  }

  const handleBatchReview = async (status: string) => {
    if (selectedIds.size === 0) { setSnackbar(t('admin.selectPapersFirst')); return }
    try {
      await api.post('/api/admin/papers/batch-review', {
        paper_ids: [...selectedIds], status, review_request_id: crypto.randomUUID(),
      })
      setSnackbar(t('admin.batchReviewDone', { status: reviewStatusLabel(status) }))
      setSelectedIds(new Set())
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const handleBatchDelete = async () => {
    if (selectedIds.size === 0) { setSnackbar(t('admin.selectPapersFirst')); return }
    if (!window.confirm(t('admin.batchDeleteConfirm', { n: selectedIds.size }))) return
    try {
      // 后端部分失败返回 206，而 response.ok 对 2xx 全为 true 不会抛错，
      // 必须按 failed_ids 判定；否则删除失败也会显示「批量删除完成」。
      const result = await api.post<{ message?: string; failed_ids?: number[] }>(
        '/api/admin/papers/batch-delete', { paper_ids: [...selectedIds] },
      )
      const failed = result?.failed_ids || []
      setSnackbar(failed.length > 0
        ? t('admin.batchDeletePartialFailed', { n: failed.length, ids: failed.join(', ') })
        : t('admin.batchDeleteDone'))
      setSelectedIds(new Set())
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const handleDeletePaper = async (id: number) => {
    if (!window.confirm(t('common.deleteConfirm'))) return
    try {
      await api.del(`/api/admin/papers/${id}`)
      setSnackbar(t('admin.deleted'))
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  /* ── User actions ────────────────────────────── */
  const handleUserSave = async () => {
    if (!editUser.user) return
    try {
      await api.put(`/api/admin/users/${editUser.user.id}/permissions`, {
        role: editRole, is_approved: editApproved,
      })
      setSnackbar(t('admin.userPermissionsUpdated'))
      setEditUser({user:null!,open:false})
      loadUsers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const handleUsernameRename = async () => {
    if (!renameUser || !renameReason.trim()) return
    setRenameSaving(true)
    try {
      const result = await api.put<{ user: User }>(`/api/admin/users/${renameUser.id}/username`, {
        username: renameUsername, reason: renameReason.trim(),
      })
      if (renameUser.id === user?.id) replaceUser(result.user)
      setSnackbar(t('admin.usernameUpdatedAudited'))
      setRenameUser(null)
      setRenameUsername('')
      setRenameReason('')
      loadUsers()
    } catch (e: unknown) {
      setSnackbar(t('admin.failed', { reason: (e as Error).message }))
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
      setSnackbar(t('admin.failed', { reason: (e as Error).message }))
      setAuditEvents([])
    } finally {
      setAuditLoading(false)
    }
  }

  const handleDeleteUser = async (id: number) => {
    if (!window.confirm(t('admin.deleteUserConfirm'))) return
    try {
      await api.del(`/api/admin/users/${id}`)
      setSnackbar(t('admin.deleted'))
      loadUsers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const handleDeleteGroup = async (id: number) => {
    if (!window.confirm(t('admin.deleteGroupConfirm'))) return
    try {
      await api.del(`/api/chart-groups/${id}`)
      setSnackbar(t('admin.deleted'))
      loadChartGroups()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  const handleTogglePublic = async (id: number, isPublic: boolean) => {
    try {
      await api.patch(`/api/chart-groups/${id}/public`, { is_public: !isPublic })
      setSnackbar(t(isPublic ? 'admin.setPrivate' : 'admin.setPublic'))
      loadChartGroups()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
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

  // 卡片指标取值；统计未加载完时显示省略号而非 0，避免误读为「真的是 0」。
  const cardMetric = (metric: typeof WORKSPACE_CARDS[number]['metric']): string => {
    switch (metric) {
      case 'users': return stats ? String(stats.users) : '…'
      case 'papers': return stats ? String(stats.papers) : '…'
      case 'pending': return stats ? String(stats.pending) : '…'
      case 'chartGroups': return String(chartGroups.length)
      case 'none': return '-'
    }
  }

  return (
    <Box sx={{ maxWidth: 1280, mx: 'auto' }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="overline" color="text.secondary">WORKSPACE</Typography>
          <Typography variant="h4" fontWeight={800}>{isSuper ? t('admin.titleSuper') : t('admin.title')}</Typography>
        </Box>
      </Box>


      {/* ═══════════════════════════════════════════ */}
      {/* Dashboard - 卡片式功能入口 */}
      {/* ═══════════════════════════════════════════ */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 2, mb: 3 }}>
        {WORKSPACE_CARDS.filter(card => !card.superOnly || isSuper).map(card => (
          <Card key={card.key} sx={{ borderLeft: '4px solid', borderColor: card.accent }}>
            {/* CardActionArea 提供 role=button、键盘可达与焦点环；带 onClick 的 Card 对读屏和键盘用户不可达。 */}
            <CardActionArea onClick={() => setTab(card.tab)} aria-label={t(card.labelKey)}>
              <CardContent>
                <Typography variant="caption" color="text.secondary">{t(card.labelKey)}</Typography>
                <Typography variant="h3" fontWeight={700}>{cardMetric(card.metric)}</Typography>
                <Typography variant="caption" sx={{ mt: 1, display: 'block', color: card.accent }}>
                  {t(card.hintKey)} →
                </Typography>
              </CardContent>
            </CardActionArea>
          </Card>
        ))}
        {isSuper && <DefaultLlmConfigPanel />}
        {/* 当前角色是身份展示，没有目标页面，因此不做成可点击卡片。 */}
        <Card sx={{ borderLeft: '4px solid', borderColor: 'info.main' }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">{t('admin.currentRole')}</Typography>
            <Typography variant="h6" fontWeight={700} noWrap title={roleLabel(isSuper ? 'superadmin' : 'admin')}>
              {roleLabel(isSuper ? 'superadmin' : 'admin')}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }} title={user?.username}>
              {user?.username}
            </Typography>
          </CardContent>
        </Card>
      </Box>

      {/* ═══════════════════════════════════════════ */}
      {/* TAB 1: Paper Review */}
      {/* ═══════════════════════════════════════════ */}
      {tab === 1 && (
        <Box>
          {/* Toolbar */}
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
            <TextField size="small" placeholder={t('admin.searchPaperPlaceholder')} sx={{ minWidth: 240 }}
              value={papersKeyword}
              onChange={e => setPapersKeyword(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setPapersPage(1); setFilterTick(t=>t+1); }}} />
            <TextField size="small" placeholder="Formula" sx={{ width: 150 }}
              value={papersMaterial}
              onChange={e => setPapersMaterial(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setPapersPage(1); setFilterTick(t=>t+1); }}} />
            <TextField size="small" label={t('admin.yearFrom')} type="number" sx={{ width: 100 }}
              value={papersYearMin}
              onChange={e => { setPapersYearMin(e.target.value); setPapersPage(1); }}
              slotProps={{ htmlInput: { min: 1900, max: 2099 } }} />
            <TextField size="small" label={t('admin.yearTo')} type="number" sx={{ width: 100 }}
              value={papersYearMax}
              onChange={e => { setPapersYearMax(e.target.value); setPapersPage(1); }}
              slotProps={{ htmlInput: { min: 1900, max: 2099 } }} />
            <FormControl size="small" sx={{ minWidth: 140 }}>
              <InputLabel>{t('admin.reviewStatusFilter')}</InputLabel>
              <Select value={papersStatus} label={t('admin.reviewStatusFilter')}
                onChange={e => { setPapersStatus(e.target.value); setPapersPage(1); }}>
                <MenuItem value="">{t('common.all')}</MenuItem>
                <MenuItem value="pending">{reviewStatusLabel('pending')}</MenuItem>
                <MenuItem value="approved">{reviewStatusLabel('approved')}</MenuItem>
                <MenuItem value="rejected">{reviewStatusLabel('rejected')}</MenuItem>
              </Select>
            </FormControl>
            <Button variant="contained" size="small" sx={{ minWidth: 80 }}
              onClick={() => { setPapersPage(1); setFilterTick(t=>t+1); }}>
              {t('common.search')}
            </Button>
            <Box sx={{ flex: 1 }} />
            {selectedIds.size > 0 && (
              <Box sx={{ display: 'flex', gap: 0.5 }}>
                <Chip label={t('admin.selectedCount', { n: selectedIds.size })} size="small" color="primary" onDelete={()=>setSelectedIds(new Set())} />
                <Button size="small" color="error" variant="outlined" onClick={()=>handleBatchReview('rejected')}>{t('admin.batchReject')}</Button>
                {isSuper && <Button size="small" color="error" variant="contained" onClick={handleBatchDelete}>{t('admin.batchDelete')}</Button>}
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
                  <TableCell sx={{ minWidth: 260 }}>{t('admin.thTitle')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thYear')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thStatus')}</TableCell>
                  <TableCell sx={{ width: 330 }} align="right">{t('common.operations')}</TableCell>
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
                        {p.title || t('admin.noTitle')}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {p.doi || p.journal || ''}
                      </Typography>
                    </TableCell>
                    <TableCell>{p.year || '-'}</TableCell>
                    <TableCell>
                      <Chip size="small" label={reviewStatusLabel(p.review_status)}
                        color={STATUS_COLORS[p.review_status] || 'default'} />
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end', alignItems: 'center' }}>
                        <Typography component="span" variant="body2" noWrap sx={{ maxWidth: 120 }}>
                          {t('admin.thUploader')}: {p.uploader_name ? (
                            <Link
                              component={RouterLink}
                              to={`/users/${encodeURIComponent(p.uploader_name)}`}
                              underline="hover"
                            >
                              {p.uploader_name}
                            </Link>
                          ) : '-'}
                        </Typography>
                        <Tooltip title={t('admin.historyButton')}>
                          <IconButton size="small" color="primary" aria-label={t('admin.historyButton')}
                            onClick={() => openPaperHistory(p)}>
                            <HistoryIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title={t('common.edit')}><IconButton size="small" color="info"
                          onClick={()=>navigate(`/admin/papers/${p.id}/edit`)}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        <Tooltip title={t('admin.reviewAction')}><IconButton size="small" color="primary"
                          onClick={() => void openReview(p)}>
                          <ReviewIcon fontSize="small" /></IconButton></Tooltip>
                        {isSuper && (
                          <Tooltip title={t('common.delete')}><IconButton size="small" color="error"
                            onClick={()=>handleDeletePaper(p.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
                {papers.length === 0 && !papersLoading && (
                  <TableRow><TableCell colSpan={5} align="center" sx={{ py: 4, color: 'text.secondary' }}>{t('common.empty')}</TableCell></TableRow>
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
      {tab === 2 && isSuper && <SuperAdminGovernance />}
      {false && tab === 2 && isSuper && (
        <Box>
          <Box sx={{ display: 'flex', justifyContent: 'flex-end', mb: 1 }}>
            <Button variant="outlined" size="small" startIcon={<HistoryIcon />} onClick={() => void openUsernameAudit()}>
              {t('admin.renameAudit')}
            </Button>
          </Box>
          {usersLoading && <LinearProgress sx={{ mb: 1 }} />}
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('admin.thUser')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.fieldRole')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thApproval')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thEmailVerified')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thSubmitReview')}</TableCell>
                  <TableCell sx={{ width: 140 }}>{t('admin.thRegisteredAt')}</TableCell>
                  <TableCell sx={{ width: 100 }} align="right">{t('common.operations')}</TableCell>
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
                      <Chip size="small" label={roleLabel(u.role)}
                        color={ROLE_COLORS[u.role] || 'default'} />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={u.is_approved ? t('admin.approved') : t('admin.pendingApproval')}
                        color={u.is_approved ? 'success' : 'warning'} />
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={u.is_email_verified ? t('admin.verified') : t('admin.unverified')}
                        color={u.is_email_verified ? 'success' : 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{u.submitted_count} / {u.reviewed_count}</Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString(locale) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title={t('admin.renameUsername')}><IconButton size="small"
                          onClick={()=>{setRenameUser(u);setRenameUsername(u.username);setRenameReason('')}}>
                          <RenameIcon fontSize="small" /></IconButton></Tooltip>
                        <Tooltip title={t('admin.editPermissions')}><IconButton size="small" color="primary"
                          onClick={()=>{setEditUser({user:u,open:true});setEditRole(u.role);setEditApproved(u.is_approved)}}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        {u.id !== user?.id && (
                          <Tooltip title={t('admin.deleteUser')}><IconButton size="small" color="error"
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
      {isSuper && tab === 4 && (
        /* ── News Management ── */
        <Box>
          <NewsManager />
        </Box>
      )}
      {isSuper && tab === 3 && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, mb: 2, alignItems: 'center' }}>
            <Typography variant="h6" fontWeight={600} sx={{ flex: 1 }}>{t('admin.chartGroupsTitle')}</Typography>
            <Button variant="contained" size="small" onClick={() => { setCgEditingId(null); setCgEditorOpen(true); }}>
              {t('admin.newChartGroup')}
            </Button>
          </Box>
          <TableContainer component={Paper} variant="outlined">
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>{t('admin.thName')}</TableCell>
                  <TableCell sx={{ width: 100 }}>{t('admin.thDataPoints')}</TableCell>
                  <TableCell sx={{ width: 60 }}>{t('admin.thPreset')}</TableCell>
                  <TableCell sx={{ width: 60 }}>{t('admin.thPublic')}</TableCell>
                  <TableCell sx={{ width: 100 }}>{t('admin.thCreator')}</TableCell>
                  <TableCell sx={{ width: 100 }}>{t('common.updatedAt')}</TableCell>
                  <TableCell sx={{ width: 120 }} align="right">{t('common.operations')}</TableCell>
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
                      <Chip size="small" label={g.is_preset ? t('common.yes') : t('common.no')} color={g.is_preset ? 'primary' : 'default'} variant="outlined" />
                    </TableCell>
                    <TableCell>
                      {isSuper || user?.role === 'admin' ? (
                        <Chip size="small" label={g.is_public ? t('common.public') : t('common.private')}
                          color={g.is_public ? 'success' : 'default'} variant="outlined"
                          onClick={() => handleTogglePublic(g.id, g.is_public)}
                          sx={{ cursor: 'pointer' }} />
                      ) : (
                        <Chip size="small" label={g.is_public ? t('common.public') : t('common.private')}
                          color={g.is_public ? 'success' : 'default'} variant="outlined" />
                      )}
                    </TableCell>
                    <TableCell>{g.creator_name || '-'}</TableCell>
                    <TableCell>
                      <Typography variant="caption" color="text.secondary">
                        {g.updated_at ? new Date(g.updated_at).toLocaleDateString(locale) : '-'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title={t('common.edit')}><IconButton size="small" color="primary"
                          onClick={() => { setCgEditingId(g.id); setCgEditorOpen(true); }}>
                          <EditIcon fontSize="small" /></IconButton></Tooltip>
                        {!g.is_preset && (
                          <Tooltip title={t('common.delete')}><IconButton size="small" color="error"
                            onClick={() => handleDeleteGroup(g.id)}><DeleteIcon fontSize="small" /></IconButton></Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                ))}
                {chartGroups.length === 0 && (
                  <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>{t('admin.noChartGroups')}</TableCell></TableRow>
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
        <DialogTitle>{t('admin.reviewTitle')}</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,mt:1 }}>
          <Typography variant="body2" fontWeight={600} noWrap>
            {reviewDlg.paper?.title || t('admin.noTitle')}
          </Typography>
          <Box sx={{ display:'flex',gap:1,flexWrap:'wrap' }}>
            <Chip size="small" label={t('admin.doiChip', { value: reviewDlg.paper?.doi || '-' })} variant="outlined" />
            <Chip size="small" label={t('admin.yearChip', { value: reviewDlg.paper?.year || '-' })} variant="outlined" />
          </Box>
          <FormControl fullWidth size="small">
            <InputLabel id="paper-review-status-label">{t('admin.reviewResult')}</InputLabel>
            <Select
              labelId="paper-review-status-label"
              id="paper-review-status"
              value={reviewStatus}
              label={t('admin.reviewResult')}
              onChange={e=>setReviewStatus(e.target.value)}
            >
              <MenuItem value="rejected">{t('admin.reviewReject')}</MenuItem>
              <MenuItem value="pending">{t('admin.reviewBackToPending')}</MenuItem>
            </Select>
          </FormControl>
          <TextField label={t('admin.reviewComment')} multiline rows={3} size="small" fullWidth
            value={reviewComment} onChange={e=>setReviewComment(e.target.value)} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setReviewDlg({paper:null!,open:false})}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleReview}>{t('admin.confirmReview')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={historyPaper !== null} onClose={() => setHistoryPaper(null)} fullWidth maxWidth="sm">
        <DialogTitle>{t('admin.historyTitle')}</DialogTitle>
        <DialogContent dividers>
          {historyLoading && <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}><CircularProgress size={24} /></Box>}
          {!historyLoading && historyError && <Alert severity="error">{historyError}</Alert>}
          {!historyLoading && !historyError && historyEvents.length === 0 && (
            <Typography color="text.secondary">{t('admin.historyEmpty')}</Typography>
          )}
          {!historyLoading && !historyError && historyEvents.map((event, index) => {
            const actor = event.actor.unknown ? t('admin.historyUnknownUploader') : event.actor.username || '-'
            const eventLabel = t(`admin.historyEvent${event.event_type[0].toUpperCase()}${event.event_type.slice(1)}`)
            const reviewStatus = event.review ? t(`admin.reviewStatus.${event.review.status}`) : ''
            return (
              <Box key={event.id} sx={{ py: 1.25 }}>
                {index > 0 && <Divider sx={{ mb: 1.25 }} />}
                <Typography variant="subtitle2">{eventLabel}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {actor} · {new Date(event.occurred_at).toLocaleString(locale)} · {t('admin.historyRevision', { value: event.paper_revision })}
                </Typography>
                {event.review && (
                  <Typography variant="body2" sx={{ mt: 0.5 }}>
                    {reviewStatus} · {event.review.comment?.trim() || t('admin.historyNoReviewComment')}
                  </Typography>
                )}
              </Box>
            )
          })}
        </DialogContent>
        <DialogActions>
          {historyError && historyPaper && <Button onClick={() => void loadPaperHistory(historyPaper.id)}>{t('admin.historyRetry')}</Button>}
          <Button onClick={() => setHistoryPaper(null)}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>

      {/* ═══════════════════════════════════════════ */}
      {/* Edit User Dialog */}
      {/* ═══════════════════════════════════════════ */}
      <Dialog open={editUser.open} onClose={()=>setEditUser({user:null!,open:false})} maxWidth="xs" fullWidth>
        <DialogTitle>{t('admin.editUserPermissionsTitle')}</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,mt:1 }}>
          <Typography variant="body2" fontWeight={600}>
            {editUser.user?.username} ({editUser.user?.email})
          </Typography>
          <FormControl fullWidth size="small">
            <InputLabel>{t('admin.fieldRole')}</InputLabel>
            <Select value={editRole} label={t('admin.fieldRole')} onChange={e=>setEditRole(e.target.value)}>
              <MenuItem value="user">{t('admin.roleUser')}</MenuItem>
              <MenuItem value="admin">{roleLabel('admin')}</MenuItem>
              <MenuItem value="superadmin">{roleLabel('superadmin')}</MenuItem>
            </Select>
          </FormControl>
          <FormControl fullWidth size="small">
            <InputLabel>{t('admin.approvalStatus')}</InputLabel>
            <Select value={editApproved ? 'approved':'pending'} label={t('admin.approvalStatus')}
              onChange={e=>setEditApproved(e.target.value==='approved')}>
              <MenuItem value="approved">{t('admin.approved')}</MenuItem>
              <MenuItem value="pending">{t('admin.pendingApproval')}</MenuItem>
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setEditUser({user:null!,open:false})}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleUserSave}>{t('common.save')}</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={!!renameUser} onClose={()=>!renameSaving&&setRenameUser(null)} maxWidth="xs" fullWidth>
        <DialogTitle>{t('admin.renameUsername')}</DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:2,pt:'12px !important' }}>
          <Alert severity="warning">{t('admin.renameWarning')}</Alert>
          <UsernameField value={renameUsername} onChange={setRenameUsername} autoFocus />
          <TextField label={t('admin.renameReasonLabel')} value={renameReason} onChange={e=>setRenameReason(e.target.value)}
            required multiline minRows={2} inputProps={{ maxLength: 500 }} helperText={`${renameReason.length}/500`} />
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setRenameUser(null)} disabled={renameSaving}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={()=>void handleUsernameRename()}
            disabled={renameSaving || !renameUsername || !renameReason.trim() || renameUsername === renameUser?.username}>
            {renameSaving ? <CircularProgress size={18} /> : t('admin.confirmRename')}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={auditOpen} onClose={()=>setAuditOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>{t('admin.usernameAuditTitle')}</DialogTitle>
        <DialogContent>
          {auditLoading ? <LinearProgress /> : auditEvents.length === 0 ? (
            <Alert severity="info">{t('admin.noRenameRecords')}</Alert>
          ) : (
            <TableContainer component={Paper} variant="outlined">
              <Table size="small">
                <TableHead><TableRow>
                  <TableCell>{t('admin.thTime')}</TableCell><TableCell>{t('admin.thChange')}</TableCell><TableCell>{t('admin.thOperator')}</TableCell><TableCell>{t('admin.thReason')}</TableCell>
                </TableRow></TableHead>
                <TableBody>{auditEvents.map(event => (
                  <TableRow key={event.id}>
                    <TableCell>{new Date(event.created_at).toLocaleString(locale)}</TableCell>
                    <TableCell>{event.old_username} → {event.new_username}</TableCell>
                    <TableCell>{event.changed_by_username}</TableCell>
                    <TableCell>{event.reason}</TableCell>
                  </TableRow>
                ))}</TableBody>
              </Table>
            </TableContainer>
          )}
        </DialogContent>
        <DialogActions><Button onClick={()=>setAuditOpen(false)}>{t('common.close')}</Button></DialogActions>
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
