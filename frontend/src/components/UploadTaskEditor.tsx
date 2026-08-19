import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert, Box, Button, Card, CardContent, Chip, CircularProgress,
  FormControl, InputLabel, MenuItem, Select, TextField, Typography,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import SaveIcon from '@mui/icons-material/Save'
import SendIcon from '@mui/icons-material/Send'
import { api, ApiError } from '../lib/api'
import {
  DraftKeyProperty, SourceEvidence, UploadDraft, evidenceList,
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

const EvidenceNotes: React.FC<{
  aiValue?: unknown
  evidence?: SourceEvidence | SourceEvidence[] | null
}> = ({ aiValue, evidence }) => {
  const items = evidenceList(evidence)
  if (aiValue === undefined && items.length === 0) return null
  return (
    <Box sx={{ mt: 0.75, pl: 1.25, borderLeft: '3px solid', borderColor: 'info.light' }}>
      {aiValue !== undefined && (
        <Typography variant="caption" color="text.secondary" display="block">
          AI 建议：{displayValue(aiValue)}
        </Typography>
      )}
      {items.map((item, index) => (
        <Typography key={index} variant="caption" color="text.secondary" display="block">
          {[item.section, item.page ? `第 ${item.page} 页` : ''].filter(Boolean).join(' · ') || '原文'}
          {item.quote ? `：“${item.quote}”` : ''}
        </Typography>
      ))}
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

  const updateKeyProperty = (index: number, field: keyof DraftKeyProperty, value: unknown) => {
    changeDraft(current => ({
      ...current,
      key_properties: current.key_properties.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item),
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
    if (draft.paper.paper_type !== 'review' && !(draft.paper.research_materials || []).length) {
      return '非综述文章至少需要一个研究材料'
    }
    const invalidProperty = draft.key_properties.findIndex(item =>
      !item.material?.trim() || !item.name?.trim() ||
      (item.value_min == null && item.value_max == null && !item.value_raw?.trim()))
    if (invalidProperty >= 0) return `第 ${invalidProperty + 1} 条物性缺少材料、物性名称或数值`
    const missingArticleType = draft.key_properties.findIndex(item => !['e', 't'].includes(item.article_type || ''))
    if (missingArticleType >= 0) return `第 ${missingArticleType + 1} 条物性必须选择实验值或理论值`
    return null
  }

  const submit = async () => {
    const validationError = validate()
    if (validationError) { setError(validationError); return }
    setSubmitting(true)
    try {
      if (!(await saveDraft(false))) return
      const response = await api.post<SubmitResponse | { data: SubmitResponse }>(`/api/rag/upload-tasks/${taskId}/submit`)
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
          ['referenced_materials', '引用材料（每行一个）'],
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
        <Typography variant="h6" fontWeight={700}>关键物性</Typography>
        <Button startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
          ...current,
          key_properties: [...current.key_properties, { material: '', name: '', value_raw: '', unit: '', article_type: '' }],
        }))}>添加物性</Button>
      </Box>

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1.5 }}>
        {draft.key_properties.map((property, index) => {
          const aiProperty = ai.key_properties?.[index]
          return (
            <Card key={index} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1.5 }}>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <Typography variant="subtitle2" fontWeight={700}>物性 #{index + 1}</Typography>
                    {property.is_primary && <Chip size="small" label="主要物性" color="primary" />}
                  </Box>
                  <Button size="small" color="error" startIcon={<DeleteIcon />}
                    onClick={() => changeDraft(current => ({
                      ...current,
                      key_properties: current.key_properties.filter((_, itemIndex) => itemIndex !== index),
                    }))}>删除</Button>
                </Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(4, 1fr)' }, gap: 1.5 }}>
                  <TextField label="材料" value={property.material || ''}
                    onChange={event => updateKeyProperty(index, 'material', event.target.value)} />
                  <TextField label="物性名称" value={property.name || ''}
                    onChange={event => updateKeyProperty(index, 'name', event.target.value)} />
                  <TextField label="原始值" value={property.value_raw || ''}
                    onChange={event => updateKeyProperty(index, 'value_raw', event.target.value)} />
                  <TextField label="单位" value={property.unit || ''}
                    onChange={event => updateKeyProperty(index, 'unit', event.target.value)} />
                  <TextField label="最小值" type="number" value={property.value_min ?? ''}
                    onChange={event => updateKeyProperty(index, 'value_min', event.target.value ? Number(event.target.value) : null)} />
                  <TextField label="最大值" type="number" value={property.value_max ?? ''}
                    onChange={event => updateKeyProperty(index, 'value_max', event.target.value ? Number(event.target.value) : null)} />
                  <TextField label="压力 (GPa)" type="number" value={property.pressure_gpa ?? ''}
                    onChange={event => updateKeyProperty(index, 'pressure_gpa', event.target.value ? Number(event.target.value) : null)} />
                  <FormControl>
                    <InputLabel>数据来源</InputLabel>
                    <Select label="数据来源" value={property.article_type || ''}
                      onChange={event => updateKeyProperty(index, 'article_type', event.target.value)}>
                      <MenuItem value="e">实验值</MenuItem>
                      <MenuItem value="t">理论值</MenuItem>
                    </Select>
                  </FormControl>
                  <TextField label="材料类型" value={property.superconductor_type || ''}
                    onChange={event => updateKeyProperty(index, 'superconductor_type', event.target.value)} />
                  <TextField label="条件说明" value={property.condition_note || ''} sx={{ gridColumn: { sm: 'span 2' } }}
                    onChange={event => updateKeyProperty(index, 'condition_note', event.target.value)} />
                </Box>
                <EvidenceNotes aiValue={aiProperty ? `${aiProperty.material || ''} ${aiProperty.name || ''} ${aiProperty.value_raw || ''}`.trim() : undefined}
                  evidence={property.evidence || aiProperty?.evidence} />
              </CardContent>
            </Card>
          )
        })}
        {draft.key_properties.length === 0 && (
          <Alert severity="info">AI 没有提取到关键物性。综述可以直接提交，其他论文请补充后提交。</Alert>
        )}
      </Box>
    </Box>
  )
}

export default UploadTaskEditor
