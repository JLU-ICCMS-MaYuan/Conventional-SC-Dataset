import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Card, CardActionArea, CardContent, Button, Chip,
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
  Person as UserIcon,
  Gavel as ReviewIcon,
  DriveFileRenameOutline as RenameIcon,
  History as HistoryIcon,
  Add as AddIcon,
} from '@mui/icons-material'
import { type User, useAuth } from '../context/AuthContext'
import { api } from '../lib/api'
import { ClassificationCatalogs, loadClassificationCatalogs, refreshClassificationCatalogs } from '../lib/classifications'
import { SourceEvidence, UploadDraft, normalizeUploadDraft, unwrapData } from '../lib/paperProcessing'
import ChartGroupEditor from '../components/ChartGroupEditor'
import ClassificationAutocomplete from '../components/ClassificationAutocomplete'
import NewsManager from '../components/NewsManager'
import SuperAdminGovernance from '../components/SuperAdminGovernance'
import UsernameField from '../components/UsernameField'
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
  record_count: number; show_in_chart: boolean
  compound_symbols: string | null; article_types: string[]
  key_properties?: Array<Record<string, unknown>>
}

interface ReviewArtifact {
  ai: UploadDraft
  user: UploadDraft
  evidence: {
    classification?: SourceEvidence[]
    classification_scope?: Array<{
      dimension: string
      raw_name: string
      scope: 'current_paper' | 'referenced_work'
      section?: string
      page_start?: number
      quote?: string
    }>
    material_states?: Array<{
      space_group?: SourceEvidence | SourceEvidence[] | null
      calculation_context?: SourceEvidence | SourceEvidence[] | null
      tc_results?: Array<SourceEvidence | SourceEvidence[] | null>
    }>
  }
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
const paperRecordCount = (paper?: PaperRecord | null) =>
  paper?.record_count ?? paper?.key_properties?.length ?? 0
/* ═══════════════════════════════════════════════ */
interface AdminPageProps { mode?: 'admin' | 'superadmin' }

const AdminPage: React.FC<AdminPageProps> = ({ mode = 'admin' }) => {
  const { user, replaceUser } = useAuth()
  const { t, lang, dict } = useLanguage()
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
  const [classificationCatalogs, setClassificationCatalogs] = useState<ClassificationCatalogs | null>(null)
  const [classificationCatalogError, setClassificationCatalogError] = useState('')

  useEffect(() => {
    loadClassificationCatalogs()
      .then(setClassificationCatalogs)
      .catch((reason: Error) => setClassificationCatalogError(reason.message || t('admin.catalogLoadFailed')))
  }, [])

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
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set())

  /* ── Edit Paper ──────────────────────────────── */
  const [editPaper, setEditPaper] = useState<{paper:PaperRecord|null,open:boolean}>({paper:null,open:false})
  const [editForm, setEditForm] = useState<Record<string,any>>({})
  const [editLoading, setEditLoading] = useState(false)
  // 编辑页审核用独立状态：它与审核弹窗可能先后打开，共用一份会串。
  const [editReviewStatus, setEditReviewStatus] = useState('')
  const [editReviewComment, setEditReviewComment] = useState('')
  const [editReviewSaving, setEditReviewSaving] = useState(false)

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
    setReviewStatus(paper.review_status || 'pending')
    setReviewComment(paper.review_comment || '')
    setReviewDetail(null)
    setReviewArtifact(null)
    // 弹窗已简化为只选状态 + 写批注，不再展示 AI 解析；但审核提交仍需
    // detail/artifact 构造 material_states 分类载荷，因此这里继续拉取。
    try {
      const [detail, artifactResponse] = await Promise.all([
        api.get<Record<string, any>>(`/api/admin/papers/${paper.id}`),
        api.get<any>(`/api/rag/papers/${paper.id}/review-artifact`).catch(() => null),
      ])
      let artifact: ReviewArtifact | null = null
      if (artifactResponse) {
        const artifactData = unwrapData<any>(artifactResponse)
        artifact = {
          ai: normalizeUploadDraft(artifactData?.ai_values),
          user: normalizeUploadDraft(artifactData?.user_values),
          evidence: artifactData?.evidence || {},
        }
        setReviewArtifact(artifact)
      }
      setReviewDetail({
        ...detail,
        material_states: (detail.material_states || []).map((state: any, index: number) => {
          const submittedState = artifact?.user.material_states?.[index]
          const aiState = artifact?.ai.material_states?.[index]
          const savedStructures = (state.structure_families || []).map((item: any) => ({
            id: item.id || item.structure_family_id,
            name: item.structure_family?.name || item.name || '',
            status: 'confirmed',
            is_primary: Boolean(item.is_primary),
          }))
          return {
            ...state,
            material_family: state.material_family
              ? { ...state.material_family, status: 'confirmed' }
              : submittedState?.material_family || aiState?.material_family || null,
            material_dimensionality: state.material_dimensionality
              || submittedState?.material_dimensionality
              || aiState?.material_dimensionality
              || 'unknown',
            structure_families: savedStructures.length > 0
              ? savedStructures
              : submittedState?.structure_families || aiState?.structure_families || [],
          }
        }),
      })
    } catch (reason) {
      setSnackbar(t('admin.reviewDataLoadFailed', { reason: (reason as Error).message }))
    }
  }

  const handleReview = async () => {
    if (!reviewDlg.paper) return
    try {
      await api.post(`/api/admin/papers/${reviewDlg.paper.id}/review`, {
        status: reviewStatus, comment: reviewComment, review_request_id: crypto.randomUUID(),
        material_states: reviewStatus === 'approved'
          ? (reviewDetail?.material_states || []).map((state: any) => ({
              id: state.id,
              material_family: {
                id: state.material_family?.id || null,
                name: state.material_family?.name || '',
              },
              material_dimensionality: state.material_dimensionality || 'unknown',
              structure_families: (state.structure_families || []).map((item: any) => ({
                id: item.id || item.structure_family_id || null,
                name: item.name || item.structure_family?.name || '',
                is_primary: Boolean(item.is_primary),
              })),
            }))
          : [],
        classification_context: {
          // Issue #66：分类判据已整体退役，快照不再记录该键；
          // 追溯主体是 classification_scope 与材料状态分类。
          classification_scope: reviewArtifact?.evidence.classification_scope || [],
          ai_material_states: reviewArtifact?.ai.material_states || [],
          user_material_states: reviewArtifact?.user.material_states || [],
        },
      })
      setClassificationCatalogs(await refreshClassificationCatalogs())
      setSnackbar(t('admin.reviewDone'))
      setReviewDlg({paper:null!,open:false})
      setReviewDetail(null)
      setReviewArtifact(null)
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.failed', { reason: (e as Error).message })) }
  }

  /* ── Edit paper ──────────────────────────────── */
  const handleEditOpen = async (p: PaperRecord) => {
    setEditLoading(true)
    try {
      const detail = await api.get<Record<string,any>>(`/api/admin/papers/${p.id}`)
      setEditForm(detail)
      // 编辑页只提供拒绝与退回两项，已通过的论文若原样带入 approved，
      // Select 的值将不在选项内而显示空白，故落到 rejected。
      setEditReviewStatus(p.review_status === 'rejected' ? 'rejected' : 'pending')
      setEditReviewComment(p.review_comment || '')
      setEditPaper({paper:p,open:true})
    } catch (e: unknown) { setSnackbar(t('admin.loadFailedReason', { reason: (e as Error).message })) }
    finally { setEditLoading(false) }
  }

  // 编辑页内提交审核。只允许拒绝与退回待审核：
  // 批准要求逐个材料状态确认分类（不完整则后端返回 409 classification_incomplete），
  // 而编辑页没有分类确认区，放开批准只会得到一个必然失败的按钮。
  const handleEditReview = async () => {
    if (!editPaper.paper) return
    if (editReviewStatus === 'approved') {
      setSnackbar(t('admin.approvalNeedsClassification'))
      return
    }
    setEditReviewSaving(true)
    try {
      await api.post(`/api/admin/papers/${editPaper.paper.id}/review`, {
        status: editReviewStatus,
        comment: editReviewComment,
        review_request_id: crypto.randomUUID(),
      })
      setSnackbar(t('admin.reviewSubmitted'))
      setEditPaper({paper:null,open:false})
      loadPapers()
      loadStats()
    } catch (e: unknown) {
      setSnackbar(t('admin.reviewFailed', { reason: (e as Error).message }))
    } finally { setEditReviewSaving(false) }
  }

  const handleEditSave = async () => {
    if (!editPaper.paper) return
    try {
      const payload: Record<string,any> = {...editForm}
      // 只提交 superconductor_properties 的真实列。压强、温度等条件字段属材料状态，
      // 不经物性接口修改；后端也不再接受这些无对应列的字段。
      if (payload.key_properties) {
        payload.key_properties = payload.key_properties.map((kp:any) => ({
          id: kp.id, material: kp.material, name_raw: kp.name_raw,
          value_min: kp.value_min, value_max: kp.value_max,
          value_raw: kp.value_raw, value_number: kp.value_number,
          unit: kp.unit, canonical_unit: kp.canonical_unit,
          condition_note: kp.condition_note,
        }))
      }
      await api.put(`/api/admin/papers/${editPaper.paper.id}`, payload)
      setSnackbar(t('common.saved'))
      setEditPaper({paper:null,open:false})
      loadPapers()
    } catch (e: unknown) { setSnackbar(t('admin.saveFailedReason', { reason: (e as Error).message })) }
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
        {/* 当前角色是身份展示，没有目标页面，因此不做成可点击卡片。 */}
        <Card sx={{ borderLeft: '4px solid', borderColor: 'info.main' }}>
          <CardContent>
            <Typography variant="caption" color="text.secondary">{t('admin.currentRole')}</Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
              <Chip size="small" color={isSuper ? 'error' : 'primary'} label={isSuper ? roleLabel('superadmin') : roleLabel('admin')} />
              <Typography variant="h6" fontWeight={700}>{user?.username}</Typography>
            </Box>
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
                  <TableCell sx={{ width: 100 }}>{t('admin.thUploader')}</TableCell>
                  <TableCell sx={{ width: 80 }}>{t('admin.thStatus')}</TableCell>
                  <TableCell sx={{ width: 100 }}>{t('admin.thRecords')}</TableCell>
                  <TableCell sx={{ width: 120 }} align="right">{t('common.operations')}</TableCell>
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
                      <Typography variant="body2" noWrap sx={{ maxWidth: 100 }}>{p.uploader_name || '-'}</Typography>
                    </TableCell>
                    <TableCell>
                      <Chip size="small" label={reviewStatusLabel(p.review_status)}
                        color={STATUS_COLORS[p.review_status] || 'default'} />
                    </TableCell>
                    <TableCell>
                      {paperRecordCount(p)}
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end' }}>
                        <Tooltip title={t('common.edit')}><IconButton size="small" color="info"
                          onClick={()=>handleEditOpen(p)}>
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
                  <TableRow><TableCell colSpan={7} align="center" sx={{ py: 4, color: 'text.secondary' }}>{t('common.empty')}</TableCell></TableRow>
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
            <Chip size="small" label={t('admin.recordsChip', { value: paperRecordCount(reviewDlg.paper) })} variant="outlined" />
          </Box>
          {(reviewDetail?.material_states || []).length > 0 && (
            <Box sx={{ borderTop: '1px solid', borderColor: 'divider', pt: 2 }}>
              <Typography variant="subtitle2" fontWeight={700} gutterBottom>{t('admin.confirmMaterialStates')}</Typography>
              {classificationCatalogError && <Alert severity="error" sx={{ mb: 1 }}>{classificationCatalogError}</Alert>}
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {(reviewDetail?.material_states || []).map((state: any, index: number) => {
                  const label = state.superconductor?.chemical_formula || t('admin.materialStateFallback', { n: index + 1 })
                  const aiState = reviewArtifact?.ai.material_states?.[index]
                  const updateState = (updates: Record<string, unknown>) => setReviewDetail(current => {
                    if (!current) return current
                    const materialStates = [...(current.material_states || [])]
                    materialStates[index] = { ...materialStates[index], ...updates }
                    return { ...current, material_states: materialStates }
                  })
                  return (
                    <Box key={state.id || index} sx={{ border: '1px solid', borderColor: 'divider', p: 1.5, borderRadius: 1 }}>
                      <Typography variant="body2" fontWeight={700} gutterBottom>{label}</Typography>
                      {aiState?.material_family?.name && (
                        <Typography variant="caption" color="text.secondary" display="block" sx={{ mb: 1 }}>
                          {t('admin.aiSuggestion', { name: aiState.material_family.name })}
                        </Typography>
                      )}
                      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: 'minmax(0, 2fr) minmax(160px, 1fr)' }, gap: 1 }}>
                        <ClassificationAutocomplete
                          label={t('admin.materialFamilyOf', { label })}
                          options={classificationCatalogs?.material_families || []}
                          value={state.material_family || null}
                          loading={!classificationCatalogs && !classificationCatalogError}
                          error={classificationCatalogError}
                          onChange={value => updateState({
                            material_family: value,
                            material_family_id: value?.id || null,
                          })}
                        />
                        <FormControl fullWidth size="small">
                          <InputLabel>{t('admin.materialDimensionality')}</InputLabel>
                          <Select
                            label={t('admin.materialDimensionality')}
                            value={state.material_dimensionality || 'unknown'}
                            onChange={event => updateState({ material_dimensionality: event.target.value })}
                          >
                            {(classificationCatalogs?.material_dimensionalities || []).map(option => (
                              <MenuItem key={option.value} value={option.value}>
                                {dict.enums.materialDimensionality[option.value] || option.name}
                              </MenuItem>
                            ))}
                          </Select>
                        </FormControl>
                      </Box>
                      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mt: 1 }}>
                        {(state.structure_families || []).map((selection: any, structureIndex: number) => (
                          <Box key={`${state.id}-${structureIndex}`} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr auto', sm: 'minmax(0, 1fr) auto auto' }, gap: 1, alignItems: 'center' }}>
                            <ClassificationAutocomplete
                              label={t('admin.structureFamily')}
                              options={classificationCatalogs?.structure_families || []}
                              value={selection}
                              loading={!classificationCatalogs && !classificationCatalogError}
                              error={classificationCatalogError}
                              onChange={value => {
                                const structures = [...(state.structure_families || [])]
                                structures[structureIndex] = { ...value, is_primary: Boolean(selection.is_primary) }
                                updateState({ structure_families: structures })
                              }}
                            />
                            <FormControlLabel
                              control={<Checkbox
                                checked={Boolean(selection.is_primary)}
                                onChange={event => updateState({
                                  structure_families: (state.structure_families || []).map((item: any, itemIndex: number) => ({
                                    ...item,
                                    is_primary: event.target.checked ? itemIndex === structureIndex : itemIndex === structureIndex ? false : item.is_primary,
                                  })),
                                })}
                              />}
                              label={t('admin.primaryStructure')}
                            />
                            <Tooltip title={t('admin.removeStructureFamily')}>
                              <IconButton
                                aria-label={t('admin.removeStructureFamilyN', { n: structureIndex + 1 })}
                                onClick={() => updateState({
                                  structure_families: (state.structure_families || []).filter((_: any, itemIndex: number) => itemIndex !== structureIndex),
                                })}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          </Box>
                        ))}
                        <Button
                          size="small"
                          startIcon={<AddIcon />}
                          sx={{ alignSelf: 'flex-start' }}
                          onClick={() => updateState({
                            structure_families: [...(state.structure_families || []), { id: null, name: '', status: 'pending', is_primary: false }],
                          })}
                        >
                          {t('admin.addStructureFamily')}
                        </Button>
                      </Box>
                    </Box>
                  )
                })}
              </Box>
            </Box>
          )}
          <FormControl fullWidth size="small">
            <InputLabel id="paper-review-status-label">{t('admin.reviewResult')}</InputLabel>
            <Select
              labelId="paper-review-status-label"
              id="paper-review-status"
              value={reviewStatus}
              label={t('admin.reviewResult')}
              onChange={e=>setReviewStatus(e.target.value)}
            >
              <MenuItem value="approved">{t('admin.reviewApprove')}</MenuItem>
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

      {/* ═══════════════════════════════════════════ */}
      {/* Edit Paper Dialog */}
      {/* ═══════════════════════════════════════════ */}
      <Dialog open={editPaper.open} onClose={()=>setEditPaper({paper:null,open:false})} maxWidth="md" fullWidth>
        <DialogTitle>
          <Box sx={{ display:'flex',justifyContent:'space-between',alignItems:'center' }}>
            <Typography variant="h6" fontWeight={600}>{t('admin.editPaperTitle')}</Typography>
            {editLoading && <CircularProgress size={20} />}
          </Box>
        </DialogTitle>
        <DialogContent sx={{ display:'flex',flexDirection:'column',gap:1.5,mt:1 }}>
          {/* 审核区固定在顶部：编辑页表单很长，随内容滚走的审核控件等于没有。 */}
          <Box sx={{
            position: 'sticky', top: 0, zIndex: 2, bgcolor: 'background.paper',
            pb: 1.5, mb: 0.5, borderBottom: '1px solid', borderColor: 'divider',
          }}>
            <Typography variant="subtitle2" fontWeight={700} gutterBottom>{t('admin.editReviewSection')}</Typography>
            <Box sx={{ display: 'flex', gap: 1.5, alignItems: 'flex-start', flexWrap: 'wrap' }}>
              <FormControl size="small" sx={{ minWidth: 170 }}>
                <InputLabel id="edit-review-status-label">{t('admin.reviewResult')}</InputLabel>
                <Select
                  labelId="edit-review-status-label"
                  value={editReviewStatus}
                  label={t('admin.reviewResult')}
                  onChange={e=>setEditReviewStatus(e.target.value)}
                >
                  <MenuItem value="rejected">{t('admin.reviewReject')}</MenuItem>
                  <MenuItem value="pending">{t('admin.reviewBackToPending')}</MenuItem>
                </Select>
              </FormControl>
              <TextField label={t('admin.reviewComment')} size="small" multiline rows={2} sx={{ flex: 1, minWidth: 240 }}
                value={editReviewComment} onChange={e=>setEditReviewComment(e.target.value)} />
              <Button variant="contained" size="small" disabled={editReviewSaving}
                onClick={handleEditReview} sx={{ mt: 0.5 }}>
                {t('admin.submitReview')}
              </Button>
            </Box>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
              {t('admin.editReviewHint')}
            </Typography>
          </Box>
          <TextField label={t('admin.fieldTitle')} size="small" fullWidth multiline rows={2}
            value={editForm.title || ''} onChange={e=>setEditForm({...editForm,title:e.target.value})} />
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:1.5 }}>
            <TextField label={t('admin.fieldDoi')} size="small" value={editForm.doi || ''}
              onChange={e=>setEditForm({...editForm,doi:e.target.value})} />
            <TextField label={t('admin.fieldJournal')} size="small" value={editForm.journal || ''}
              onChange={e=>setEditForm({...editForm,journal:e.target.value})} />
            <TextField label={t('admin.fieldYear')} size="small" type="number" value={editForm.year || ''}
              onChange={e=>setEditForm({...editForm,year:e.target.value ? Number(e.target.value) : null})} />
          </Box>
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1.5 }}>
            <TextField label={t('admin.fieldVolume')} size="small" value={editForm.volume || ''}
              onChange={e=>setEditForm({...editForm,volume:e.target.value})} />
            <TextField label={t('admin.fieldPages')} size="small" value={editForm.pages || ''}
              onChange={e=>setEditForm({...editForm,pages:e.target.value})} />
          </Box>
          <TextField label={t('admin.fieldAuthors')} size="small" fullWidth multiline rows={2}
            helperText={t('admin.jsonArrayFormat')}
            value={typeof editForm.authors === 'string' ? editForm.authors : JSON.stringify(editForm.authors || [], null, 2)}
            onChange={e=>{ try { setEditForm({...editForm,authors:JSON.parse(e.target.value)}) } catch { setEditForm({...editForm,authors:e.target.value}) }}} />
          <TextField label={t('admin.fieldAbstract')} size="small" fullWidth multiline rows={3}
            value={editForm.abstract || ''} onChange={e=>setEditForm({...editForm,abstract:e.target.value})} />
          <TextField label={t('admin.fieldLlmSummary')} size="small" fullWidth multiline rows={2}
            value={editForm.summary || ''} onChange={e=>setEditForm({...editForm,summary:e.target.value})} />
          <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:1.5 }}>
            <TextField label={t('admin.fieldPaperType')} size="small" value={editForm.paper_type || ''}
              onChange={e=>setEditForm({...editForm,paper_type:e.target.value})} />
            <TextField label={t('admin.fieldKeywordsTags')} size="small" value={editForm.keywords_tags || ''}
              onChange={e=>setEditForm({...editForm,keywords_tags:e.target.value})} />
            <TextField label={t('admin.fieldSourceFilePath')} size="small" value={editForm.source_file_path || ''}
              onChange={e=>setEditForm({...editForm,source_file_path:e.target.value})} />
          </Box>
          <TextField label={t('admin.fieldMethodology')} size="small" fullWidth multiline rows={2}
            value={typeof editForm.methodology === 'string' ? editForm.methodology : JSON.stringify(editForm.methodology || [], null, 2)}
            onChange={e=>{ try { setEditForm({...editForm,methodology:JSON.parse(e.target.value)}) } catch { setEditForm({...editForm,methodology:e.target.value})}}} />
          <TextField label={t('admin.fieldKeyFinding')} size="small" fullWidth multiline rows={2}
            value={editForm.key_finding || ''} onChange={e=>setEditForm({...editForm,key_finding:e.target.value})} />
          <TextField label={t('admin.fieldResearchMotivation')} size="small" fullWidth multiline rows={2}
            value={editForm.research_motivation || ''} onChange={e=>setEditForm({...editForm,research_motivation:e.target.value})} />
          {/* 知识图谱标题：单栏英文输入，随 editForm 一并提交（T046）。 */}
          <TextField label={t('admin.fieldKnowledgeGraphTitle')} size="small" fullWidth
            value={editForm.knowledge_graph_title || ''} onChange={e=>setEditForm({...editForm,knowledge_graph_title:e.target.value})} />
          {/* Non-editable metadata */}
          <Box sx={{ display:'flex',gap:1,flexWrap:'wrap',mt:0.5 }}>
            <Chip size="small" label={t('admin.idChip', { value: editForm.id || '-' })} variant="outlined" />
            <Chip size="small" label={t('admin.propertyCountChip', { value: editForm.record_count || 0 })} variant="outlined" />
            <Chip size="small" label={t('admin.createdChip', { value: editForm.created_at ? new Date(editForm.created_at).toLocaleString(locale) : '-' })} />
            {(editForm.materials || []).map((m:string)=>(
              <Chip key={m} size="small" label={m} color="primary" variant="outlined" />
            ))}
          </Box>

          {/* Key Properties */}
          {(editForm.key_properties || []).length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                {t('admin.keyPropertiesHeader', { n: editForm.key_properties.length })}
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
                      {kp.is_primary && <Chip size="small" label={t('admin.primaryProperty')} color="primary" />}
                      <Typography variant="caption" color="text.secondary">
                        ID: {kp.id} · source: {kp.name_raw || '-'}
                      </Typography>
                    </Box>
                    {/* Row 1: 核心数值 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr',gap:1 }}>
                      <TextField label={t('admin.fieldMaterial')} size="small" value={kp.material || ''}
                        onChange={e=>setKp('material',e.target.value)} />
                      <TextField label={t('admin.fieldPropertyName')} size="small" value={kp.name || ''}
                        onChange={e=>setKp('name',e.target.value)} />
                      <FormControlLabel control={
                        <Checkbox checked={!!kp.is_primary} size="small"
                          onChange={e=>setKp('is_primary',e.target.checked)} />
                      } label={t('admin.primaryProperty')} sx={{ m:0 }} />
                      <FormControl size="small">
                        <InputLabel>{t('admin.nameNoteLabel')}</InputLabel>
                        <Select value={kp.name_note || ''} label={t('admin.nameNoteLabel')}
                          onChange={e=>setKp('name_note',e.target.value)}>
                          <MenuItem value="">-</MenuItem>
                          <MenuItem value="temperature/position dependent">{t('admin.nameNoteTemperaturePositionDependent')}</MenuItem>
                          <MenuItem value="pressure dependent">{t('admin.nameNotePressureDependent')}</MenuItem>
                          <MenuItem value="doping dependent">{t('admin.nameNoteDopingDependent')}</MenuItem>
                          <MenuItem value="dynamically stable">{t('admin.nameNoteDynamicallyStable')}</MenuItem>
                          <MenuItem value="thermodynamically stable">{t('admin.nameNoteThermodynamicallyStable')}</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    {/* Row 2: 数值 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr 1fr 1fr',gap:1,mt:1 }}>
                      <TextField label={t('admin.fieldValueMin')} size="small" type="number"
                        value={kp.value_min ?? ''} onChange={e=>setKp('value_min',e.target.value?Number(e.target.value):null)} />
                      <TextField label={t('admin.fieldValueMax')} size="small" type="number"
                        value={kp.value_max ?? ''} onChange={e=>setKp('value_max',e.target.value?Number(e.target.value):null)} />
                      <TextField label={t('admin.fieldValueRaw')} size="small"
                        value={kp.value_raw || ''} onChange={e=>setKp('value_raw',e.target.value)} />
                      <TextField label={t('admin.fieldUnit')} size="small"
                        value={kp.unit || ''} onChange={e=>setKp('unit',e.target.value)} />
                      <TextField label={t('admin.fieldNameRaw')} size="small"
                        value={kp.name_raw || ''} onChange={e=>setKp('name_raw',e.target.value)} />
                    </Box>
                    {/* Row 3: 条件与分类 */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr 1fr',gap:1,mt:1 }}>
                      <TextField label={t('admin.fieldPressure')} size="small" type="number"
                        value={kp.pressure_gpa ?? ''} onChange={e=>setKp('pressure_gpa',e.target.value?Number(e.target.value):null)} />
                      <TextField label={t('admin.fieldTemperature')} size="small" type="number"
                        value={kp.temperature_k ?? ''} onChange={e=>setKp('temperature_k',e.target.value?Number(e.target.value):null)} />
                      <FormControl size="small">
                        <InputLabel>{t('admin.fieldArticleType')}</InputLabel>
                        <Select value={kp.article_type || ''} label={t('admin.fieldArticleType')}
                          onChange={e=>setKp('article_type',e.target.value)}>
                          <MenuItem value="">-</MenuItem>
                          <MenuItem value="e">{t('admin.articleTypeExperimental')}</MenuItem>
                          <MenuItem value="t">{t('admin.articleTypeTheoretical')}</MenuItem>
                        </Select>
                      </FormControl>
                    </Box>
                    {/* Row 4: notes */}
                    <Box sx={{ display:'grid',gridTemplateColumns:'1fr 1fr',gap:1,mt:1 }}>
                      <TextField label={t('admin.fieldConditionNote')} size="small"
                        value={kp.condition_note || ''} onChange={e=>setKp('condition_note',e.target.value)} />
                      <TextField label={t('admin.fieldNameNote')} size="small"
                        value={kp.name_note || ''} onChange={e=>setKp('name_note',e.target.value)} />
                    </Box>
                  </Box>
                )})}
              </Box>
            </Box>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={()=>setEditPaper({paper:null,open:false})}>{t('common.cancel')}</Button>
          <Button variant="contained" onClick={handleEditSave}>{t('admin.saveChanges')}</Button>
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
