import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress, Collapse,
  FormControl, InputLabel, MenuItem, Select, TextField, Typography, useMediaQuery,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import SaveIcon from '@mui/icons-material/Save'
import SendIcon from '@mui/icons-material/Send'
import { api, ApiError } from '../lib/api'
import {
  DraftKeyProperty, DraftMaterialState, DraftTcResult, SourceEvidence, UploadDraft, evidenceList,
  normalizeUploadDraft, unwrapData,
} from '../lib/paperProcessing'

interface UploadTaskEditorProps {
  taskId: string
  onSubmitted: (paperId: number) => void
}

interface SubmitResponse {
  ok: boolean
  paper_id: number
  review_status: 'pending'
}

const PAPER_TYPE_OPTIONS = [
  { value: 'theoretical', label: '理论文章' },
  { value: 'experimental', label: '实验文章' },
  { value: 'review', label: '综述文章' },
  { value: 'unknown', label: '暂不确定' },
]

const SC_TYPE_OPTIONS = [
  'hydride', 'cuprate', 'iron_based', 'nickel_based', 'carbon', 'organic', 'others',
]

const toLines = (value: string[] | undefined) => (value || []).join('\n')
const fromLines = (value: string) => value.split(/[\n,，]/).map(item => item.trim()).filter(Boolean)
const displayValue = (value: unknown) => {
  if (value == null || value === '') return '未提供'
  if (Array.isArray(value)) return value.join('、') || '未提供'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

const COLLAPSED_EVIDENCE_HEIGHT = 120

const EvidenceNotes: React.FC<{
  label: string
  aiValue?: unknown
  evidence?: SourceEvidence | SourceEvidence[] | null
}> = ({ label, aiValue, evidence }) => {
  const items = evidenceList(evidence)
  const contentId = useId()
  const contentRef = useRef<HTMLDivElement>(null)
  const overflowRef = useRef(false)
  const [isOverflowing, setIsOverflowing] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

  const measureOverflow = useCallback(() => {
    const nextOverflowing = (contentRef.current?.scrollHeight || 0) > COLLAPSED_EVIDENCE_HEIGHT
    if (nextOverflowing === overflowRef.current) return

    overflowRef.current = nextOverflowing
    setIsOverflowing(nextOverflowing)
    setExpanded(false)
  }, [])

  useLayoutEffect(() => {
    measureOverflow()
  }, [aiValue, evidence, measureOverflow])

  useEffect(() => {
    const content = contentRef.current
    if (!content) return undefined

    window.addEventListener('resize', measureOverflow)
    let observer: ResizeObserver | undefined
    if (typeof ResizeObserver !== 'undefined') {
      observer = new ResizeObserver(measureOverflow)
      observer.observe(content)
    }

    return () => {
      observer?.disconnect()
      window.removeEventListener('resize', measureOverflow)
    }
  }, [measureOverflow])

  if (aiValue === undefined && items.length === 0) return null
  return (
    <Box sx={{
      mt: 0.75,
      width: '100%',
      maxWidth: '100%',
      minWidth: 0,
      boxSizing: 'border-box',
      p: 1,
      borderRadius: 1,
      bgcolor: 'action.hover',
    }}>
      <Collapse
        in={!isOverflowing || expanded}
        collapsedSize={isOverflowing ? COLLAPSED_EVIDENCE_HEIGHT : 0}
        timeout={prefersReducedMotion ? 0 : 180}
      >
        <Box id={contentId} ref={contentRef} sx={{ minWidth: 0 }}>
          {aiValue !== undefined && (
            <Typography variant="caption" color="text.secondary" display="block" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
              AI 建议：{displayValue(aiValue)}
            </Typography>
          )}
          {items.map((item, index) => (
            <Typography key={index} variant="caption" color="text.secondary" display="block" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
              {[item.section, item.page ? `第 ${item.page} 页` : ''].filter(Boolean).join(' · ') || '原文'}
              {item.quote ? `：“${item.quote}”` : ''}
            </Typography>
          ))}
        </Box>
      </Collapse>
      {isOverflowing && (
        <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 0.25 }}>
          <Button
            size="small"
            aria-expanded={expanded}
            aria-controls={contentId}
            aria-label={`${expanded ? '收起' : '展开'} ${label}的 AI 解释`}
            onClick={() => setExpanded(value => !value)}
            endIcon={<ExpandMoreIcon sx={{
              transform: expanded ? 'rotate(180deg)' : 'none',
              transition: prefersReducedMotion ? 'none' : 'transform 180ms ease',
            }} />}
            sx={{ minHeight: 28, px: 1 }}
          >
            {expanded ? '收起 AI 解释' : '展开 AI 解释'}
          </Button>
        </Box>
      )}
    </Box>
  )
}

const UploadTaskEditor: React.FC<UploadTaskEditorProps> = ({ taskId, onSubmitted }) => {
  const [draft, setDraft] = useState<UploadDraft | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [error, setError] = useState('')
  const revisionRef = useRef(0)

  useEffect(() => {
    const controller = new AbortController()
    setLoading(true)
    api.get<{ ok: boolean; data: UploadDraft }>(
      `/api/rag/upload-tasks/${taskId}/draft`,
      { signal: controller.signal },
    ).then(response => {
      setDraft(normalizeUploadDraft(unwrapData(response)))
      setDirty(false)
      setError('')
    }).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason.message || '草稿加载失败')
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [taskId])

  const changeDraft = useCallback((updater: (current: UploadDraft) => UploadDraft) => {
    setDraft(current => current ? updater(current) : current)
    revisionRef.current += 1
    setDirty(true)
    setError('')
  }, [])

  const setPaperField = (field: keyof UploadDraft['paper'], value: unknown) => {
    changeDraft(current => ({ ...current, paper: { ...current.paper, [field]: value } }))
  }

  const setDraftField = (field: keyof UploadDraft, value: unknown) => {
    changeDraft(current => ({ ...current, [field]: value }))
  }

  const setSuperconductorType = (value: string) => {
    changeDraft(current => ({
      ...current,
      sc_type: value,
      sc_type_review_status: value && !SC_TYPE_OPTIONS.includes(value) ? 'pending' : 'none',
    }))
  }

  const updateMaterialState = (index: number, field: keyof DraftMaterialState, value: unknown) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item),
    }))
  }

  const updateCalculationContext = (
    index: number,
    field: 'lambda_ep' | 'omega_log_k' | 'mu_star',
    value: number | null,
  ) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) =>
        itemIndex === index
          ? {
              ...item,
              calculation_context: {
                phonon_nuclear_treatment: 'unknown',
                lambda_ep: null,
                omega_log_k: null,
                mu_star: null,
                ...item.calculation_context,
                [field]: value,
              },
            }
          : item),
    }))
  }

  const updateTcResult = (stateIndex: number, resultIndex: number, field: keyof DraftTcResult, value: unknown) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((state, index) => index === stateIndex ? {
        ...state,
        tc_results: (state.tc_results || []).map((item, itemIndex) =>
          itemIndex === resultIndex ? { ...item, [field]: value } : item),
      } : state),
    }))
  }

  const updateProperty = (stateIndex: number, propertyIndex: number, field: keyof DraftKeyProperty, value: unknown) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((state, index) => index === stateIndex ? {
        ...state,
        properties: (state.properties || []).map((item, itemIndex) =>
          itemIndex === propertyIndex ? { ...item, [field]: value } : item),
      } : state),
    }))
  }

  const saveDraft = useCallback(async (showResult = false): Promise<boolean> => {
    if (!draft || saving) return !dirty
    const revision = revisionRef.current
    setSaving(true)
    try {
      await api.put(`/api/rag/upload-tasks/${taskId}/draft`, draft)
      if (revision === revisionRef.current) setDirty(false)
      setLastSavedAt(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }))
      if (showResult) setError('')
      return true
    } catch (reason) {
      setError((reason as Error).message || '草稿保存失败')
      return false
    } finally {
      setSaving(false)
    }
  }, [dirty, draft, saving, taskId])

  useEffect(() => {
    if (!dirty || !draft || saving) return
    const timer = window.setTimeout(() => { void saveDraft(false) }, 5000)
    return () => window.clearTimeout(timer)
  }, [dirty, draft, saveDraft, saving])

  const validate = (): string | null => {
    if (!draft?.paper.title?.trim()) return '标题不能为空'
    if (draft.paper.doi && !/^10\.\d{4,9}\/\S+$/i.test(draft.paper.doi.trim())) return 'DOI 格式不正确'
    if (!draft.paper.paper_type || draft.paper.paper_type === 'unknown') return '请选择论文整体类型'
    if (draft.paper.paper_type === 'theoretical' && !draft.paper.theoretical_subtype) {
      return '理论文章必须选择理论二级类型'
    }
    if (draft.paper.paper_type !== 'review' && draft.material_states.length === 0) {
      return '非综述文章至少需要一个材料状态'
    }
    const invalidState = draft.material_states.findIndex(item => !item.material?.trim())
    if (invalidState >= 0) return `第 ${invalidState + 1} 个材料状态缺少材料`
    const invalidSpaceGroup = draft.material_states.findIndex(item =>
      item.reported_space_group_number != null &&
      (item.reported_space_group_number < 1 || item.reported_space_group_number > 230))
    if (invalidSpaceGroup >= 0) return `第 ${invalidSpaceGroup + 1} 个材料状态的空间群号必须在 1–230 之间`
    const invalidCalculation = draft.material_states.findIndex(item =>
      [item.calculation_context?.lambda_ep, item.calculation_context?.omega_log_k, item.calculation_context?.mu_star]
        .some(value => value != null && value < 0))
    if (invalidCalculation >= 0) return `第 ${invalidCalculation + 1} 个材料状态的计算参数不能为负数`
    for (const [stateIndex, state] of draft.material_states.entries()) {
      const invalidTc = (state.tc_results || []).findIndex(item =>
        !item.value_raw?.trim() && item.tc_value_k == null && (item.tc_min_k == null || item.tc_max_k == null))
      if (invalidTc >= 0) return `第 ${stateIndex + 1} 个材料状态的第 ${invalidTc + 1} 条 Tc 缺少数值`
      const invalidProperty = (state.properties || []).findIndex(item =>
        !String(item.name || item.name_raw || '').trim() ||
        (!item.value_raw?.trim() && item.value == null && item.value_min == null && item.value_max == null))
      if (invalidProperty >= 0) return `第 ${stateIndex + 1} 个材料状态的第 ${invalidProperty + 1} 条普通物性不完整`
    }
    return null
  }

  const submit = async () => {
    const validationError = validate()
    if (validationError) { setError(validationError); return }
    setSubmitting(true)
    try {
      if (!(await saveDraft(false))) return
      let response: SubmitResponse | { data: SubmitResponse }
      try {
        response = await api.post<SubmitResponse | { data: SubmitResponse }>(`/api/rag/upload-tasks/${taskId}/submit`)
      } catch (reason) {
        const apiError = reason as ApiError
        if (apiError.code !== 'consistency_ack_required' || !window.confirm(
          '正文与附件的标题、DOI 或作者存在差异。确认这些文件属于同一篇论文并继续提交吗？',
        )) throw reason
        response = await api.post<SubmitResponse | { data: SubmitResponse }>(
          `/api/rag/upload-tasks/${taskId}/submit`,
          { consistency_acknowledged: true },
        )
      }
      onSubmitted(unwrapData(response).paper_id)
    } catch (reason) {
      const apiError = reason as ApiError
      if (apiError.status === 409 && apiError.existingPaperId) {
        setError(`该 DOI 已存在（论文 #${apiError.existingPaperId}），没有创建重复记录。`)
      } else {
        setError(apiError.message || '提交审核失败')
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}><CircularProgress /></Box>
  }
  if (!draft) return <Alert severity="error">{error || '草稿不存在或已过期'}</Alert>

  const ai = draft.ai_original || {}
  const aiPaper = ai.paper || {}
  const classificationEvidence = draft.classification_evidence || []

  return (
    <Box sx={{ mt: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>检查 AI 草稿</Typography>
          <Typography variant="body2" color="text.secondary">核对后保存，确认无误再提交管理员审核。</Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="caption" color={error ? 'error' : 'text.secondary'}>
            {saving ? '保存中…' : dirty ? '有修改，5 秒后自动保存' : lastSavedAt ? `${lastSavedAt} 已保存` : '草稿已加载'}
          </Typography>
          <Button variant="outlined" startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
            disabled={saving || submitting} onClick={() => void saveDraft(true)}>立即保存</Button>
          <Button variant="contained" startIcon={submitting ? <CircularProgress size={16} /> : <SendIcon />}
            disabled={saving || submitting} onClick={() => void submit()}>提交审核</Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
        <Box>
          <TextField fullWidth label="标题" value={draft.paper.title || ''}
            onChange={event => setPaperField('title', event.target.value)} />
          <EvidenceNotes aiValue={aiPaper.title} />
        </Box>
        <Box>
          <TextField fullWidth label="DOI" value={draft.paper.doi || ''}
            onChange={event => setPaperField('doi', event.target.value.trim())} />
          <EvidenceNotes aiValue={aiPaper.doi} />
        </Box>
        <Box>
          <TextField fullWidth label="作者（每行一位）" multiline minRows={2}
            value={toLines(draft.paper.authors)}
            onChange={event => setPaperField('authors', fromLines(event.target.value))} />
          <EvidenceNotes aiValue={aiPaper.authors} />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: '2fr 1fr 1fr 1fr' }, gap: 1 }}>
          <TextField label="期刊" value={draft.paper.journal || ''}
            onChange={event => setPaperField('journal', event.target.value)} />
          <TextField label="年份" type="number" value={draft.paper.year ?? ''}
            onChange={event => setPaperField('year', event.target.value ? Number(event.target.value) : null)} />
          <TextField label="卷" value={draft.paper.volume || ''}
            onChange={event => setPaperField('volume', event.target.value)} />
          <TextField label="页" value={draft.paper.pages || ''}
            onChange={event => setPaperField('pages', event.target.value)} />
          <Box sx={{ gridColumn: '1 / -1' }}>
            <EvidenceNotes aiValue={[aiPaper.journal, aiPaper.year, aiPaper.volume, aiPaper.pages].filter(Boolean).join(' · ')} />
          </Box>
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr 1fr' }, gap: 2, mt: 2 }}>
        <FormControl fullWidth>
          <InputLabel>论文整体类型</InputLabel>
          <Select label="论文整体类型" value={draft.paper.paper_type || 'unknown'}
            onChange={event => setPaperField('paper_type', event.target.value)}>
            {PAPER_TYPE_OPTIONS.map(option => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
          </Select>
          <EvidenceNotes aiValue={aiPaper.paper_type} evidence={classificationEvidence} />
        </FormControl>
        <FormControl fullWidth disabled={draft.paper.paper_type !== 'theoretical'}>
          <InputLabel>理论二级类型</InputLabel>
          <Select label="理论二级类型" value={draft.paper.theoretical_subtype || ''}
            onChange={event => setPaperField('theoretical_subtype', event.target.value || null)}>
            <MenuItem value="calculation">计算类</MenuItem>
            <MenuItem value="method">方法类</MenuItem>
            <MenuItem value="theory">理论模型与机制</MenuItem>
          </Select>
          <EvidenceNotes aiValue={aiPaper.theoretical_subtype} />
        </FormControl>
        <Box>
          <TextField fullWidth label="超导材料类型（可输入自定义）" value={draft.sc_type || ''}
            slotProps={{ htmlInput: { list: 'sc-type-options' } }}
            onChange={event => setSuperconductorType(event.target.value)} />
          <datalist id="sc-type-options">{SC_TYPE_OPTIONS.map(value => <option key={value} value={value} />)}</datalist>
          {draft.sc_type && !SC_TYPE_OPTIONS.includes(draft.sc_type) && (
            <Chip size="small" color="warning" label="新类型，待管理员确认" sx={{ mt: 0.75 }} />
          )}
          <EvidenceNotes aiValue={ai.sc_type} evidence={classificationEvidence} />
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2 }}>
        {[
          ['research_materials', '研究材料（每行一个）'],
          ['keywords_tags', '关键词（每行一个）'],
          ['methodology', '研究方法（每行一项）'],
        ].map(([field, label]) => (
          <Box key={field}>
            <TextField fullWidth label={label} multiline minRows={3}
              value={toLines(draft.paper[field as keyof UploadDraft['paper']] as string[] | undefined)}
              onChange={event => setPaperField(field as keyof UploadDraft['paper'], fromLines(event.target.value))} />
            <EvidenceNotes
              aiValue={aiPaper[field as keyof typeof aiPaper]}
              evidence={draft.field_evidence?.[field]}
            />
          </Box>
        ))}
      </Box>

      {[
        ['abstract', '论文摘要', 4],
        ['summary', '中文总结', 3],
        ['key_finding', '核心发现', 3],
      ].map(([field, label, rows]) => (
        <Box key={String(field)} sx={{ mt: 2 }}>
          <TextField fullWidth label={String(label)} multiline minRows={Number(rows)}
            value={String(draft.paper[field as keyof UploadDraft['paper']] || '')}
            onChange={event => setPaperField(field as keyof UploadDraft['paper'], event.target.value)} />
          <EvidenceNotes aiValue={aiPaper[field as keyof typeof aiPaper]} />
        </Box>
      ))}

      <Box sx={{ mt: 2 }}>
        <TextField fullWidth label="分类理由" multiline minRows={3}
          value={draft.classification_reason || ''}
          onChange={event => setDraftField('classification_reason', event.target.value)} />
        <EvidenceNotes aiValue={ai.classification_reason} evidence={classificationEvidence} />
      </Box>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Typography variant="h6" fontWeight={700}>材料状态与计算条件</Typography>
        <Button startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
          ...current,
          material_states: [...current.material_states, {
            material: '',
            pressure_value_gpa: null,
            state_kind: current.paper.paper_type === 'experimental' ? 'experimental' : 'theoretical',
            reported_space_group_symbol: null,
            reported_space_group_number: null,
            calculation_context: current.paper.paper_type === 'experimental' ? null : {
              phonon_nuclear_treatment: 'unknown', lambda_ep: null, omega_log_k: null, mu_star: null,
            },
            experimental_context: current.paper.paper_type === 'experimental' ? { tc_criterion: 'unknown' } : null,
            tc_results: [],
            properties: [],
          }],
        }))}>添加材料状态</Button>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1.5 }}>
        {draft.material_states.map((state, index) => {
          const aiState = ai.material_states?.[index]
          return (
            <Card key={index} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Typography variant="subtitle2" fontWeight={700}>材料状态 #{index + 1}</Typography>
                  </Box>
                  <Button size="small" color="error" startIcon={<DeleteIcon />}
                    onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.filter((_, itemIndex) => itemIndex !== index),
                    }))}>删除</Button>
                </Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1.5 }}>
                  <TextField label="材料" value={state.material || ''}
                    onChange={event => updateMaterialState(index, 'material', event.target.value)} />
                  <TextField label="压力 (GPa)" type="number" value={state.pressure_value_gpa ?? ''}
                    onChange={event => updateMaterialState(index, 'pressure_value_gpa', event.target.value ? Number(event.target.value) : null)} />
                  <TextField label="物相" value={state.phase_label || ''}
                    onChange={event => updateMaterialState(index, 'phase_label', event.target.value || null)} />
                  <TextField label="空间群符号" value={state.reported_space_group_symbol || ''}
                    onChange={event => updateMaterialState(index, 'reported_space_group_symbol', event.target.value || null)} />
                  <TextField label="空间群号" type="number" value={state.reported_space_group_number ?? ''}
                    onChange={event => updateMaterialState(index, 'reported_space_group_number', event.target.value ? Number(event.target.value) : null)}
                    slotProps={{ htmlInput: { min: 1, max: 230 } }} />
                  <TextField label="电声耦合强度 λ" type="number" value={state.calculation_context?.lambda_ep ?? ''}
                    onChange={event => updateCalculationContext(index, 'lambda_ep', event.target.value ? Number(event.target.value) : null)}
                    slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                  <TextField label="对数声子频率 ωlog (K)" type="number" value={state.calculation_context?.omega_log_k ?? ''}
                    onChange={event => updateCalculationContext(index, 'omega_log_k', event.target.value ? Number(event.target.value) : null)}
                    slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                </Box>
                <EvidenceNotes
                  aiValue={aiState ? `${aiState.material || ''} ${aiState.pressure_value_gpa ?? ''} GPa`.trim() : undefined}
                  evidence={state.space_group_evidence || aiState?.space_group_evidence}
                />

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>临界温度 Tc</Typography>
                  <Button size="small" startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
                    ...current,
                    material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                      ...item,
                      tc_results: [...(item.tc_results || []), {
                        result_kind: item.state_kind === 'experimental' ? 'experimental' : 'theoretical',
                        tc_method: item.state_kind === 'experimental' ? 'experimental' : 'unknown',
                        tc_value_k: null, tc_min_k: null, tc_max_k: null, value_raw: '', unit_raw: 'K',
                      }],
                    } : item),
                  }))}>添加 Tc</Button>
                </Box>
                {(state.tc_results || []).map((result, resultIndex) => (
                  <Box key={resultIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr 1fr auto' }, gap: 1, mt: 1 }}>
                    <TextField size="small" label={`Tc #${resultIndex + 1} 原始值`} value={result.value_raw || ''}
                      onChange={event => updateTcResult(index, resultIndex, 'value_raw', event.target.value)} />
                    <TextField size="small" label="Tc 数值 (K)" type="number" value={result.tc_value_k ?? ''}
                      onChange={event => updateTcResult(index, resultIndex, 'tc_value_k', event.target.value ? Number(event.target.value) : null)} />
                    <TextField size="small" label="Tc 方法" value={result.tc_method || ''}
                      onChange={event => updateTcResult(index, resultIndex, 'tc_method', event.target.value)} />
                    <Button size="small" color="error" onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                        ...item, tc_results: (item.tc_results || []).filter((_, tcIndex) => tcIndex !== resultIndex),
                      } : item),
                    }))}>删除</Button>
                  </Box>
                ))}

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>其他普通物性</Typography>
                  <Button size="small" startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
                    ...current,
                    material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                      ...item,
                      properties: [...(item.properties || []), { name: '', name_raw: '', value_raw: '', unit: '' }],
                    } : item),
                  }))}>添加普通物性</Button>
                </Box>
                {(state.properties || []).map((property, propertyIndex) => (
                  <Box key={propertyIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 2fr 1fr auto' }, gap: 1, mt: 1 }}>
                    <TextField size="small" label={`物性 #${propertyIndex + 1} 名称`} value={property.name_raw || property.name || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'name_raw', event.target.value)} />
                    <TextField size="small" label="原始值" value={property.value_raw || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'value_raw', event.target.value)} />
                    <TextField size="small" label="单位" value={property.unit || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'unit', event.target.value)} />
                    <Button size="small" color="error" onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                        ...item, properties: (item.properties || []).filter((_, propIndex) => propIndex !== propertyIndex),
                      } : item),
                    }))}>删除</Button>
                  </Box>
                ))}
              </CardContent>
            </Card>
          )
        })}
        {draft.material_states.length === 0 && (
          <Alert severity="info">AI 没有提取到材料状态。综述可以直接提交，其他论文请补充后提交。</Alert>
        )}
      </Box>
    </Box>
  )
}

export default UploadTaskEditor
