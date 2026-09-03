import React, { useEffect, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Checkbox, Chip, CircularProgress, Container, Dialog,
  DialogActions, DialogContent, DialogTitle, Divider, FormControl, FormControlLabel, IconButton,
  InputLabel, MenuItem, Select, Snackbar, TextField, Typography,
} from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import HistoryIcon from '@mui/icons-material/History'
import { useNavigate, useParams } from 'react-router-dom'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import {
  ClassificationCatalogs, ClassificationTerm, FamilySelection, familyName,
  loadClassificationCatalogs, pendingSelection, selectionForTerm,
} from '../lib/classifications'
import { DraftMaterialState, StructureCandidate, unwrapData } from '../lib/paperProcessing'
import MaterialStatesEditor, { SpaceGroupOption } from '../components/MaterialStatesEditor'
import { useLanguage } from '../context/LanguageContext'

/**
 * Go 详情行的材料状态 → 共享编辑器（MaterialStatesEditor）的 DraftMaterialState（T020）。
 * Go 侧返回的是模型序列化：化学式在 superconductor.chemical_formula，
 * structure_families 是 {id, is_primary, structure_family:{...}} 的链接行，
 * 需要转成编辑器的 {id, name, status, is_primary} 选择形态。
 * （原 AdminPage.tsx 弹窗逻辑迁移，Issue #78。）
 */
const materialStateFromDetail = (state: Record<string, any>): DraftMaterialState => {
  const { superconductor_kind: _legacySuperconductorKind, ...stateWithoutLegacyKind } = state
  const contextsById = new Map(
    (state.calculation_contexts || []).map((context: Record<string, any>) => [context.id, context]),
  )
  return {
    ...stateWithoutLegacyKind,
    material: state.superconductor?.chemical_formula || state.material || '',
    structure_families: (state.structure_families || []).map((item: any) => ({
      id: item.id ?? item.structure_family_id,
      name: item.structure_family?.name || item.name || '',
      name_zh: item.structure_family?.name_zh || item.structure_family?.name || item.name || '',
      name_en: item.structure_family?.name_en || item.name_en || '',
      status: 'confirmed',
      is_primary: Boolean(item.is_primary),
    })),
    tc_results: (state.tc_results || []).map((result: Record<string, any>) => ({
      ...result,
      calculation_context: result.calculation_context
        || contextsById.get(result.calculation_context_id)
        || undefined,
    })),
    properties: (state.properties || []).map((item: any) => ({
      ...item,
      value_raw: item.value_raw ?? (item.value == null ? '' : String(item.value)),
    })),
  }
}

const SUPERCONDUCTOR_KIND_VALUES = ['conventional', 'unconventional', 'unknown'] as const

/**
 * Go 已落库的结构模型 → 已确认候选（T020）。
 * 科学数据保存是整体替换（契约 C1）：既有结构必须并入候选列表，
 * 否则保存时会被整体删除重建流程丢掉。
 * （原 AdminPage.tsx 弹窗逻辑迁移，Issue #78。）
 */
const candidateFromStructureModel = (model: Record<string, any>, ref: string): StructureCandidate => ({
  candidate_id: `structure_${model.id}`,
  material_state_ref: ref,
  source_kind: 'attachment',
  status: 'confirmed',
  confirmation: 'confirmed',
  original_format: model.structure_format || 'cif',
  original_text: model.structure_text || null,
  validation: {
    structure_format: model.structure_format || 'cif',
    atom_count: model.atom_count ?? undefined,
    volume: model.volume_angstrom3 ?? undefined,
    cell_parameters: model.cell_parameters || undefined,
  },
  representations: model.structure_text ? {
    // Python 端只把惯用胞 CIF 作为规范表示落库（scientific_drafts.py），统一放 cif 槽位
    conventional: { cif: { text: model.structure_text, available: true } },
  } : undefined,
  sources: [{
    file_id: `structure_${model.id}`,
    filename: model.source_locator || `structure_${model.id}.cif`,
    role: 'attachment',
  }],
})

type PaperHistoryEvent = {
  id: number
  event_type: 'uploaded' | 'modified' | 'reviewed'
  paper_revision: number
  actor: { username: string | null; unknown: boolean }
  occurred_at: string
  review: { status: 'approved' | 'rejected' | 'pending'; comment: string | null } | null
}

/**
 * 管理端论文编辑独立页（Issue #78，路由 /admin/papers/:id/edit）。
 * 由原 AdminPage 编辑弹窗迁移而来：论文级字段、科学数据（MaterialStatesEditor）、
 * 审核区与两段保存全部保留，容器从 Dialog 改为页面；
 * 并新增已落库结构的完整表示加载（晶胞/格式切换与下载，FR-004/FR-005/FR-006）。
 */
const AdminPaperEditPage: React.FC = () => {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const { t, lang, dict } = useLanguage()
  const locale = lang === 'zh' ? 'zh-CN' : 'en-US'
  const paperId = Number(id)
  const workspacePath = user?.role === 'superadmin' ? '/superadmin' : '/admin'

  /* ── 论文级字段 ─────────────────────────────── */
  const [editForm, setEditForm] = useState<Record<string, any>>({})
  const [editLoading, setEditLoading] = useState(true)
  const [loadError, setLoadError] = useState('')

  /* ── 审核区（论文级 family 与状态级标签均可在本页确认后批准）─ */
  const [editReviewStatus, setEditReviewStatus] = useState('')
  const [editReviewComment, setEditReviewComment] = useState('')
  const [editReviewSaving, setEditReviewSaving] = useState(false)

  const [historyOpen, setHistoryOpen] = useState(false)
  const [historyLoading, setHistoryLoading] = useState(false)
  const [historyError, setHistoryError] = useState('')
  const [historyEvents, setHistoryEvents] = useState<PaperHistoryEvent[]>([])

  /* ── 科学数据（Issue #76）：材料状态与结构候选受控于共享编辑器，保存时随 C1 提交 ─ */
  const [editMaterialStates, setEditMaterialStates] = useState<DraftMaterialState[]>([])
  const [editMaterialFamilies, setEditMaterialFamilies] = useState<FamilySelection[]>([])
  const [editStructureCandidates, setEditStructureCandidates] = useState<StructureCandidate[]>([])
  const [editSpaceGroups, setEditSpaceGroups] = useState<SpaceGroupOption[]>([])
  // 论文原本是否有科学数据：有才在保存时走科学数据段（契约 C4 第二步）
  const [editHadScientificData, setEditHadScientificData] = useState(false)
  // 结构表示生成失败降级提示（Issue #78，FR-007）
  const [representationLoadFailed, setRepresentationLoadFailed] = useState(false)

  /* ── 分类目录与通用提示 ─────────────────────── */
  const [classificationCatalogs, setClassificationCatalogs] = useState<ClassificationCatalogs | null>(null)
  const [classificationCatalogError, setClassificationCatalogError] = useState('')
  const [snackbar, setSnackbar] = useState('')

  useEffect(() => {
    loadClassificationCatalogs()
      .then(setClassificationCatalogs)
      .catch((reason: Error) => setClassificationCatalogError(reason.message || t('admin.catalogLoadFailed')))
  }, [])

  // 空间群标准表加载（与上传页同一端点；失败降级为纯自由输入，不阻塞编辑）
  useEffect(() => {
    api.get<{ space_groups?: SpaceGroupOption[] }>('/api/rag/space-groups')
      .then(response => { if (Array.isArray(response?.space_groups)) setEditSpaceGroups(response.space_groups) })
      .catch(() => { /* 空间群表不可用时降级为自由输入，不阻塞编辑 */ })
  }, [])

  /**
   * 结构表示加载（Issue #78 核心，FR-004/FR-007）：详情加载后为每个已落库结构
   * 调用表示端点，把返回的完整 representations（primitive/conventional × cif/poscar）
   * 合并进对应候选，使 StructureCandidatePanel 的晶胞/格式切换与下载可用；
   * 端点失败时保留候选自带的落库惯用胞 CIF（降级，不阻塞编辑）。
   */
  const loadStructureRepresentations = async (detailStates: Array<Record<string, any>>) => {
    await Promise.all(detailStates.flatMap((state) =>
      (state.structures || []).map(async (model: any) => {
        const structureId: number = model.id
        try {
          const response = await api.get<{ ok: boolean; data: { representations?: StructureCandidate['representations'] } }>(
            `/api/rag/papers/${paperId}/structures/${structureId}/representations`,
          )
          const representations = response?.data?.representations
          if (representations) {
            setEditStructureCandidates(current => current.map(candidate =>
              candidate.candidate_id === `structure_${structureId}`
                ? { ...candidate, representations: { ...candidate.representations, ...representations } }
                : candidate))
          }
        } catch {
          // 表示生成服务不可用：保留落库 CIF（候选转换自带），轻提示但不阻塞编辑
          setRepresentationLoadFailed(true)
        }
      }),
    ))
  }

  // 详情加载：论文级字段 + 科学数据转共享编辑器形态 + 已落库结构并入候选
  useEffect(() => {
    const loadDetail = async () => {
      setEditLoading(true)
      try {
        const detail = await api.get<Record<string, any>>(`/api/admin/papers/${paperId}`)
        let pendingValues: Record<string, any> | null = null
        if (detail.review_status === 'pending') {
          try {
            const artifact = await api.get<{ data?: { user_values?: Record<string, any> } }>(
              `/api/rag/papers/${paperId}/review-artifact`,
            )
            pendingValues = artifact?.data?.user_values || null
          } catch {
            // 手工创建或已清理临时证据的待审论文没有 artifact，继续使用正式详情。
          }
        }
        setEditForm({
          ...detail,
          superconductor_kind: pendingValues?.paper?.superconductor_kind
            ?? detail.superconductor_kind
            ?? 'unknown',
        })
        const pendingFamilies = pendingValues?.paper?.material_families
        const materialFamilies = Array.isArray(pendingFamilies)
          ? pendingFamilies
          : (detail.material_families || [])
        setEditMaterialFamilies(materialFamilies.map((family: any) => ({
          id: family.id ?? null,
          name: family.name || family.name_zh || '',
          name_zh: family.name_zh || family.name || '',
          name_en: family.name_en || '',
          status: family.status === 'pending' ? 'pending' : 'confirmed',
        })))
        // 已通过论文重新编辑时默认退回待审核，避免无修改地重复批准。
        setEditReviewStatus(detail.review_status === 'rejected' ? 'rejected' : 'pending')
        setEditReviewComment(detail.review_comment || '')
        // 科学数据：Go 详情行转成共享编辑器形态；既有结构并入候选（整体替换语义，T020）
        const detailStates: Array<Record<string, any>> = detail.material_states || []
        const pendingStates: Array<Record<string, any>> = Array.isArray(pendingValues?.material_states)
          ? pendingValues.material_states
          : []
        const materialStates = detailStates.map((state, index) => {
          const normalized = materialStateFromDetail(state)
          const pendingState = pendingStates[index]
          if (!pendingState) return normalized
          return {
            ...normalized,
            material_dimensionality: pendingState.material_dimensionality || normalized.material_dimensionality,
            structure_families: Array.isArray(pendingState.structure_families)
              ? pendingState.structure_families
              : normalized.structure_families,
          }
        })
        const structureCandidates = detailStates.flatMap((state, index) =>
          (state.structures || []).map((model: any) =>
            candidateFromStructureModel(model, `material_states[${index}]`)))
        setEditMaterialStates(materialStates)
        setEditStructureCandidates(structureCandidates)
        setEditHadScientificData(
          materialStates.length > 0 || structureCandidates.length > 0 || materialFamilies.length > 0,
        )
        // 已落库结构表示：异步拉取完整表示并入候选，不阻塞表单渲染
        void loadStructureRepresentations(detailStates)
      } catch (e: unknown) {
        setLoadError(t('admin.loadFailedReason', { reason: (e as Error).message }))
      } finally {
        setEditLoading(false)
      }
    }
    void loadDetail()
  }, [paperId])

  // 编辑页内提交审核；批准时由后端校验当前论文级 family 和状态分类完整性。
  const handleEditReview = async () => {
    setEditReviewSaving(true)
    try {
      const materialStates = editMaterialStates.map(state => ({
        id: (state as DraftMaterialState & { id?: number }).id,
        material_dimensionality: state.material_dimensionality || 'unknown',
        structure_families: (state.structure_families || []).map(item => ({
          id: item.id || null,
          name: item.name || '',
          is_primary: Boolean(item.is_primary),
        })),
      }))
      await api.post(`/api/admin/papers/${paperId}/review`, {
        status: editReviewStatus,
        comment: editReviewComment,
        review_request_id: crypto.randomUUID(),
        ...(editReviewStatus === 'approved' ? {
          superconductor_kind: editForm.superconductor_kind || 'unknown',
          material_families: editMaterialFamilies.map(family => ({ id: family.id || null, name: family.name })),
          material_states: materialStates,
        } : {}),
      })
      navigate(workspacePath)
    } catch (e: unknown) {
      setSnackbar(t('admin.reviewFailed', { reason: (e as Error).message }))
    } finally { setEditReviewSaving(false) }
  }

  const loadPaperHistory = async () => {
    setHistoryLoading(true)
    setHistoryError('')
    try {
      const response = await api.get<{ events?: PaperHistoryEvent[] }>(`/api/admin/papers/${paperId}/history`)
      setHistoryEvents(Array.isArray(response.events) ? response.events : [])
    } catch (e: unknown) {
      setHistoryError(t('admin.historyLoadFailed', { reason: (e as Error).message }))
    } finally {
      setHistoryLoading(false)
    }
  }

  const openPaperHistory = () => {
    setHistoryOpen(true)
    void loadPaperHistory()
  }

  // 两段保存（契约 C4）：先论文级（Go，低风险），后科学数据（Python，整体替换）。
  // 科学数据段仅当论文原本有科学数据或当前编辑区有内容时执行——纯论文级编辑
  // （如无材料状态的综述）不需要触发整体替换。
  const handleEditSave = async () => {
    try {
      const historyOperationId = crypto.randomUUID()
      const payload: Record<string, any> = { ...editForm, history_operation_id: historyOperationId }
      // 只提交 superconductor_properties 的真实列。压强、温度等条件字段属材料状态，
      // 不经物性接口修改；后端也不再接受这些无对应列的字段。
      if (payload.key_properties) {
        payload.key_properties = payload.key_properties.map((kp: any) => ({
          id: kp.id, material: kp.material, name_raw: kp.name_raw,
          value_min: kp.value_min, value_max: kp.value_max,
          value_raw: kp.value_raw, value_number: kp.value_number,
          unit: kp.unit, canonical_unit: kp.canonical_unit,
          condition_note: kp.condition_note,
        }))
      }
      // 第一步：论文级字段保存（Go）。失败在此终止，不调用科学数据段。
      await api.put(`/api/admin/papers/${paperId}`, payload)
      if (editHadScientificData || editMaterialFamilies.length > 0 || editMaterialStates.length > 0 || editStructureCandidates.length > 0) {
        try {
          // 第二步：科学数据整体替换（Python，契约 C1）。
          // structure_candidates 只提交已确认候选：未确认（unreviewed）与已排除（excluded）
          // 的候选不落库，与上传链路「先确认后保存」的语义一致（契约 C1/C2）。
          const response = await api.put<{ ok: boolean; data: { revision_bumped?: boolean } }>(
            `/api/rag/papers/${paperId}/scientific-draft`,
            {
              paper_type: editForm.paper_type || '',
              superconductor_kind: editForm.superconductor_kind || 'unknown',
              material_families: editMaterialFamilies,
              material_states: editMaterialStates,
              structure_candidates: editStructureCandidates.filter(candidate => candidate.confirmation === 'confirmed'),
              history_operation_id: historyOperationId,
            },
          )
          // 升版成功（T045）：论文已退回待审核，明确提示审核通过前不对外公开
          setSnackbar(response?.data?.revision_bumped
            ? t('admin.scientificSavedRevisionBumped')
            : t('common.saved'))
        } catch (e: unknown) {
          // FR-019：论文级已保存成功，只需重试科学数据部分；不离开编辑页
          setSnackbar(t('admin.scientificSaveFailed', { reason: (e as Error).message }))
          return
        }
      } else {
        setSnackbar(t('common.saved'))
      }
    } catch (e: unknown) { setSnackbar(t('admin.saveFailedReason', { reason: (e as Error).message })) }
  }

  // 论文结构补传（契约 C2）：只产出并校验候选、不落库；成功后并入本地候选，
  // 由保存时的 C1 structure_candidates 字段一并提交（T034）。
  const handleUploadStructure = async (stateIndex: number, file: File) => {
    const body = new FormData()
    body.append('material_state_index', String(stateIndex))
    body.append('file', file)
    const response = await api.post<{ ok: boolean; data: Record<string, any> }>(
      `/api/rag/papers/${paperId}/structure-candidates`, body,
    )
    const data = unwrapData(response)
    const candidate: StructureCandidate = {
      candidate_id: String(data.candidate_id),
      material_state_ref: `material_states[${stateIndex}]`,
      source_kind: 'attachment',
      status: data.status || 'needs_review',
      confirmation: 'unreviewed',
      original_format: data.structure_format || null,
      validation: data.validation,
      representations: data.representations,
      sources: [{ file_id: String(data.candidate_id), filename: file.name, role: 'attachment' }],
    }
    setEditStructureCandidates(current => [
      ...current.filter(item => item.candidate_id !== candidate.candidate_id),
      candidate,
    ])
  }

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      {/* 标题栏 + 返回列表 */}
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 2 }}>
        <IconButton aria-label={t('admin.editBackToList')} onClick={() => navigate(workspacePath)}>
          <ArrowBackIcon fontSize="small" />
        </IconButton>
        <Typography variant="h5" fontWeight={700}>{t('admin.editPaperTitle')}</Typography>
        {editLoading && <CircularProgress size={20} />}
      </Box>

      {loadError && <Alert severity="error" sx={{ mb: 2 }}>{loadError}</Alert>}
      {representationLoadFailed && (
        <Alert severity="warning" sx={{ mb: 2 }}>{t('admin.representationsLoadFailed')}</Alert>
      )}

      {editForm.id != null ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
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
                  onChange={e => setEditReviewStatus(e.target.value)}
                >
                  <MenuItem value="approved">{t('admin.reviewApprove')}</MenuItem>
                  <MenuItem value="rejected">{t('admin.reviewReject')}</MenuItem>
                  <MenuItem value="pending">{t('admin.reviewBackToPending')}</MenuItem>
                </Select>
              </FormControl>
              <TextField label={t('admin.reviewComment')} size="small" multiline rows={2} sx={{ flex: 1, minWidth: 240 }}
                value={editReviewComment} onChange={e => setEditReviewComment(e.target.value)} />
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
            value={editForm.title || ''} onChange={e => setEditForm({ ...editForm, title: e.target.value })} />
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1.5 }}>
            <TextField label={t('admin.fieldDoi')} size="small" value={editForm.doi || ''}
              onChange={e => setEditForm({ ...editForm, doi: e.target.value })} />
            <TextField label={t('admin.fieldJournal')} size="small" value={editForm.journal || ''}
              onChange={e => setEditForm({ ...editForm, journal: e.target.value })} />
            <TextField label={t('admin.fieldYear')} size="small" type="number" value={editForm.year || ''}
              onChange={e => setEditForm({ ...editForm, year: e.target.value ? Number(e.target.value) : null })} />
          </Box>
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
            <TextField label={t('admin.fieldVolume')} size="small" value={editForm.volume || ''}
              onChange={e => setEditForm({ ...editForm, volume: e.target.value })} />
            <TextField label={t('admin.fieldPages')} size="small" value={editForm.pages || ''}
              onChange={e => setEditForm({ ...editForm, pages: e.target.value })} />
          </Box>
          <TextField label={t('admin.fieldAuthors')} size="small" fullWidth multiline rows={2}
            helperText={t('admin.jsonArrayFormat')}
            value={typeof editForm.authors === 'string' ? editForm.authors : JSON.stringify(editForm.authors || [], null, 2)}
            onChange={e => { try { setEditForm({ ...editForm, authors: JSON.parse(e.target.value) }) } catch { setEditForm({ ...editForm, authors: e.target.value }) } }} />
          <TextField label={t('admin.fieldAbstract')} size="small" fullWidth multiline rows={3}
            value={editForm.abstract || ''} onChange={e => setEditForm({ ...editForm, abstract: e.target.value })} />
          <TextField label={t('admin.fieldLlmSummary')} size="small" fullWidth multiline rows={2}
            value={editForm.summary || ''} onChange={e => setEditForm({ ...editForm, summary: e.target.value })} />
          <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1.5 }}>
            <TextField label={t('admin.fieldPaperType')} size="small" value={editForm.paper_type || ''}
              onChange={e => setEditForm({ ...editForm, paper_type: e.target.value })} />
            <FormControl size="small">
              <InputLabel id="paper-superconductor-kind-label">{t('upload.superconductorKindField')}</InputLabel>
              <Select labelId="paper-superconductor-kind-label" label={t('upload.superconductorKindField')} value={editForm.superconductor_kind || 'unknown'}
                onChange={e => setEditForm({ ...editForm, superconductor_kind: e.target.value })}>
                {SUPERCONDUCTOR_KIND_VALUES.map(value => (
                  <MenuItem key={value} value={value}>{value === 'unknown' ? dict.enums.superconductorKind.unknown : dict.enums.superconductorKind[value]}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <Autocomplete<ClassificationTerm | string, true, false, true>
              multiple
              freeSolo
              options={classificationCatalogs?.material_families || []}
              loading={!classificationCatalogs && !classificationCatalogError}
              value={editMaterialFamilies.map(selection => {
                if (selection.id == null) return selection.name
                return classificationCatalogs?.material_families?.find(item => item.id === selection.id) || selection.name
              })}
              getOptionLabel={option => typeof option === 'string' ? option : familyName(option, lang)}
              isOptionEqualToValue={(option, value) => (
                typeof option !== 'string' && typeof value !== 'string' && option.id === value.id
              )}
              onChange={(_, values) => setEditMaterialFamilies(values.map(value => (
                typeof value === 'string' ? pendingSelection(value) : selectionForTerm(value)
              )).filter((value): value is FamilySelection => Boolean(value)))}
              renderInput={params => (
                <TextField
                  {...params}
                  size="small"
                  label={t('upload.materialFamilyField')}
                  error={Boolean(classificationCatalogError)}
                  helperText={classificationCatalogError || undefined}
                />
              )}
            />
            <TextField label={t('admin.fieldKeywordsTags')} size="small" value={editForm.keywords_tags || ''}
              onChange={e => setEditForm({ ...editForm, keywords_tags: e.target.value })} />
            <TextField label={t('admin.fieldSourceFilePath')} size="small" value={editForm.source_file_path || ''}
              onChange={e => setEditForm({ ...editForm, source_file_path: e.target.value })} />
          </Box>
          <TextField label={t('admin.fieldMethodology')} size="small" fullWidth multiline rows={2}
            value={typeof editForm.methodology === 'string' ? editForm.methodology : JSON.stringify(editForm.methodology || [], null, 2)}
            onChange={e => { try { setEditForm({ ...editForm, methodology: JSON.parse(e.target.value) }) } catch { setEditForm({ ...editForm, methodology: e.target.value }) } }} />
          <TextField label={t('admin.fieldKeyFinding')} size="small" fullWidth multiline rows={2}
            value={editForm.key_finding || ''} onChange={e => setEditForm({ ...editForm, key_finding: e.target.value })} />
          <TextField label={t('admin.fieldResearchMotivation')} size="small" fullWidth multiline rows={2}
            value={editForm.research_motivation || ''} onChange={e => setEditForm({ ...editForm, research_motivation: e.target.value })} />
          {/* 知识图谱标题：单栏英文输入，随 editForm 一并提交（T046）。 */}
          <TextField label={t('admin.fieldKnowledgeGraphTitle')} size="small" fullWidth
            value={editForm.knowledge_graph_title || ''} onChange={e => setEditForm({ ...editForm, knowledge_graph_title: e.target.value })} />
          {/* Non-editable metadata */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 0.5 }}>
            <Chip size="small" label={t('admin.idChip', { value: editForm.id || '-' })} variant="outlined" />
            <Chip size="small" label={`${t('admin.thUploader')}: ${editForm.uploader_name || '-'}`} variant="outlined" />
            <Chip size="small" label={t('admin.propertyCountChip', { value: editForm.record_count || 0 })} variant="outlined" />
            <Button size="small" variant="outlined" startIcon={<HistoryIcon />} onClick={openPaperHistory}>
              {t('admin.processingHistory')}
            </Button>
            <Chip size="small" label={t('admin.createdChip', { value: editForm.created_at ? new Date(editForm.created_at).toLocaleString(locale) : '-' })} />
            {(editForm.materials || []).map((m: string) => (
              <Chip key={m} size="small" label={m} color="primary" variant="outlined" />
            ))}
          </Box>

          {/* Key Properties */}
          {(editForm.key_properties || []).length > 0 && (
            <Box sx={{ mt: 1 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                {t('admin.keyPropertiesHeader', { n: editForm.key_properties.length })}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, maxHeight: 480, overflow: 'auto' }}>
                {(editForm.key_properties || []).map((kp: any, i: number) => {
                  const setKp = (f: string, v: any) => {
                    const n = [...(editForm.key_properties || [])]
                    n[i] = { ...n[i], [f]: v }
                    setEditForm({ ...editForm, key_properties: n })
                  }
                  return (
                    <Box key={kp.id || i} sx={{
                      p: 1.5, borderRadius: 1, bgcolor: kp.is_primary ? '#eef2ff' : 'grey.50',
                      border: '1px solid', borderColor: kp.is_primary ? '#818cf8' : 'divider',
                    }}>
                      {/* KP header */}
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                        <Chip size="small" label={`#${i + 1}`} variant="outlined" />
                        {kp.is_primary && <Chip size="small" label={t('admin.primaryProperty')} color="primary" />}
                        <Typography variant="caption" color="text.secondary">
                          ID: {kp.id} · source: {kp.name_raw || '-'}
                        </Typography>
                      </Box>
                      {/* Row 1: 核心数值 */}
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 1 }}>
                        <TextField label={t('admin.fieldMaterial')} size="small" value={kp.material || ''}
                          onChange={e => setKp('material', e.target.value)} />
                        <TextField label={t('admin.fieldPropertyName')} size="small" value={kp.name || ''}
                          onChange={e => setKp('name', e.target.value)} />
                        <FormControlLabel control={
                          <Checkbox checked={!!kp.is_primary} size="small"
                            onChange={e => setKp('is_primary', e.target.checked)} />
                        } label={t('admin.primaryProperty')} sx={{ m: 0 }} />
                        <FormControl size="small">
                          <InputLabel>{t('admin.nameNoteLabel')}</InputLabel>
                          <Select value={kp.name_note || ''} label={t('admin.nameNoteLabel')}
                            onChange={e => setKp('name_note', e.target.value)}>
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
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr 1fr', gap: 1, mt: 1 }}>
                        <TextField label={t('admin.fieldValueMin')} size="small" type="number"
                          value={kp.value_min ?? ''} onChange={e => setKp('value_min', e.target.value ? Number(e.target.value) : null)} />
                        <TextField label={t('admin.fieldValueMax')} size="small" type="number"
                          value={kp.value_max ?? ''} onChange={e => setKp('value_max', e.target.value ? Number(e.target.value) : null)} />
                        <TextField label={t('admin.fieldValueRaw')} size="small"
                          value={kp.value_raw || ''} onChange={e => setKp('value_raw', e.target.value)} />
                        <TextField label={t('admin.fieldUnit')} size="small"
                          value={kp.unit || ''} onChange={e => setKp('unit', e.target.value)} />
                        <TextField label={t('admin.fieldNameRaw')} size="small"
                          value={kp.name_raw || ''} onChange={e => setKp('name_raw', e.target.value)} />
                      </Box>
                      {/* Row 3: 条件与分类 */}
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 1, mt: 1 }}>
                        <TextField label={t('admin.fieldPressure')} size="small" type="number"
                          value={kp.pressure_gpa ?? ''} onChange={e => setKp('pressure_gpa', e.target.value ? Number(e.target.value) : null)} />
                        <TextField label={t('admin.fieldTemperature')} size="small" type="number"
                          value={kp.temperature_k ?? ''} onChange={e => setKp('temperature_k', e.target.value ? Number(e.target.value) : null)} />
                        <FormControl size="small">
                          <InputLabel>{t('admin.fieldArticleType')}</InputLabel>
                          <Select value={kp.article_type || ''} label={t('admin.fieldArticleType')}
                            onChange={e => setKp('article_type', e.target.value)}>
                            <MenuItem value="">-</MenuItem>
                            <MenuItem value="e">{t('admin.articleTypeExperimental')}</MenuItem>
                            <MenuItem value="t">{t('admin.articleTypeTheoretical')}</MenuItem>
                          </Select>
                        </FormControl>
                      </Box>
                      {/* Row 4: notes */}
                      <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1, mt: 1 }}>
                        <TextField label={t('admin.fieldConditionNote')} size="small"
                          value={kp.condition_note || ''} onChange={e => setKp('condition_note', e.target.value)} />
                        <TextField label={t('admin.fieldNameNote')} size="small"
                          value={kp.name_note || ''} onChange={e => setKp('name_note', e.target.value)} />
                      </Box>
                    </Box>
                  )
                })}
              </Box>
            </Box>
          )}

          {/* 升版警告：编辑已通过论文时提示保存科学数据将递增版本并退回待审核（T044） */}
          {editForm.review_status === 'approved' && (
            <Alert severity="warning">{t('admin.revisionBumpWarning')}</Alert>
          )}
          {/* 科学数据编辑区（Issue #76）：材料状态、Tc、物性、结构候选与补传。
              数据来自 /api/admin/papers/:id 的 material_states（含 tc_results/properties/structures），
              编辑结果随保存时的 C1 请求整体替换（T020/T030/T034）。 */}
          <MaterialStatesEditor
            states={editMaterialStates}
            onChange={setEditMaterialStates}
            catalogs={classificationCatalogs}
            catalogLoading={!classificationCatalogs && !classificationCatalogError}
            catalogError={classificationCatalogError}
            structureCandidates={editStructureCandidates}
            onStructureCandidatesChange={setEditStructureCandidates}
            spaceGroups={editSpaceGroups}
            paperType={editForm.paper_type}
            superconductorKind={editForm.superconductor_kind}
            onUploadStructure={handleUploadStructure}
            onError={setSnackbar}
          />

          <Box sx={{ display: 'flex', justifyContent: 'flex-end', gap: 1, mt: 1 }}>
            <Button variant="outlined" onClick={() => navigate(workspacePath)}>{t('common.cancel')}</Button>
            <Button variant="contained" onClick={handleEditSave}>{t('admin.saveChanges')}</Button>
          </Box>
        </Box>
      ) : (
        !loadError && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 10 }}>
            <CircularProgress />
          </Box>
        )
      )}

      <Dialog open={historyOpen} onClose={() => setHistoryOpen(false)} fullWidth maxWidth="sm">
        <DialogTitle>{t('admin.processingHistoryTitle')}</DialogTitle>
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
          {historyError && <Button onClick={() => void loadPaperHistory()}>{t('admin.historyRetry')}</Button>}
          <Button onClick={() => setHistoryOpen(false)}>{t('common.close')}</Button>
        </DialogActions>
      </Dialog>

      {/* Snackbar */}
      <Snackbar open={!!snackbar} autoHideDuration={3000} onClose={() => setSnackbar('')}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}>
        <Alert severity="info" variant="filled" onClose={() => setSnackbar('')}>{snackbar}</Alert>
      </Snackbar>
    </Container>
  )
}

export default AdminPaperEditPage
