import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Checkbox, Chip, CircularProgress,
  FormControl, FormHelperText, InputLabel, ListItemText, Menu, MenuItem, Select, TextField, Typography,
} from '@mui/material'
import SaveIcon from '@mui/icons-material/Save'
import SendIcon from '@mui/icons-material/Send'
import { api, ApiError } from '../lib/api'
import {
  ClassificationCatalogs,
  loadClassificationCatalogs,
} from '../lib/classifications'
import { useLanguage } from '../context/LanguageContext'
import MaterialStatesEditor, { EvidenceNotes, SpaceGroupOption, ValidationIssue } from './MaterialStatesEditor'
import {
  UploadDraft, normalizeUploadDraft, unwrapData,
} from '../lib/paperProcessing'

interface UploadTaskEditorProps {
  taskId: string
  onSubmitted: (paperId: number) => void
  draftOverride?: UploadDraft | null
  readOnly?: boolean
  statusNote?: string
}

interface SubmitResponse {
  ok: boolean
  paper_id: number
  review_status: 'pending'
}

type AuthorRoleField = 'corresponding_authors' | 'co_first_authors'

// 枚举下拉不再携带中文 label：渲染时按 value 查 dict.enums.<组>.<value>（enums.ts）
const PAPER_TYPE_VALUES = ['theoretical', 'experimental', 'review', 'unknown'] as const

const toLines = (value: string[] | undefined) => (value || []).join('\n')
const fromLines = (value: string) => value.split(/[\n,，]/).map(item => item.trim()).filter(Boolean)

// 后端错误体为 FastAPI HTTPException：detail 可能是字符串或 {code, message} 对象。
// 提取具体原因；网络错误或无 detail 时返回 null，由调用方回退通用文案
const backendErrorReason = (reason: unknown): { message: string; code?: string } | null => {
  const detail = (reason as ApiError | null)?.detail
  if (typeof detail === 'string' && detail.trim()) return { message: detail }
  if (detail && typeof detail === 'object') {
    const { code, message } = detail as { code?: unknown; message?: unknown }
    if (typeof message === 'string' && message.trim()) {
      return { message, code: typeof code === 'string' && code ? code : undefined }
    }
  }
  return null
}

// 保存/提交失败的横幅文案：优先展示后端具体原因（可附 code），否则回退通用文案
const failureMessage = (
  t: (key: string, vars?: Record<string, string | number>) => string,
  action: 'save' | 'submit',
  reason: unknown,
  fallback: string,
): string => {
  const reasonDetail = backendErrorReason(reason)
  if (!reasonDetail) return fallback
  return t('upload.failedWithDetail', {
    action: t(action === 'save' ? 'upload.saveAction' : 'upload.submitAction'),
    message: reasonDetail.message,
    code: reasonDetail.code ? t('upload.codeSuffix', { code: reasonDetail.code }) : '',
  })
}

// 后端部分校验规则前端没有（材料家族、压强区间、专用字段等），其 message 已写明
// 「第 N 个材料状态」。据此解析序号以便定位到卡片；解析不出时只显示横幅，不做定位。
// 该耦合依赖后端文案，由测试固定，文案变更时测试会立即失败。
const stateIndexFromMessage = (message: string): number | undefined => {
  const matched = /第\s*(\d+)\s*个材料状态/.exec(message)
  if (!matched) return undefined
  const ordinal = Number(matched[1])
  return Number.isSafeInteger(ordinal) && ordinal > 0 ? ordinal - 1 : undefined
}

const UploadTaskEditor: React.FC<UploadTaskEditorProps> = ({
  taskId, onSubmitted, draftOverride, readOnly = false, statusNote,
}) => {
  const { t, lang, dict } = useLanguage()
  const [draft, setDraft] = useState<UploadDraft | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [error, setError] = useState('')
  // 本次提交发现的校验问题；驱动字段错误态与定位，提交成功或重新加载草稿时清空
  const [issues, setIssues] = useState<ValidationIssue[]>([])
  const [authorMenu, setAuthorMenu] = useState<{ author: string; anchorEl: HTMLElement } | null>(null)
  const [authorInput, setAuthorInput] = useState('')
  const [catalogs, setCatalogs] = useState<ClassificationCatalogs | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')
  const [spaceGroups, setSpaceGroups] = useState<SpaceGroupOption[]>([])
  const revisionRef = useRef(0)

  useEffect(() => {
    let active = true
    setCatalogLoading(true)
    loadClassificationCatalogs()
      .then(value => {
        if (!active) return
        setCatalogs(value)
        setCatalogError('')
      })
      .catch((reason: Error) => {
        if (active) setCatalogError(reason.message || t('upload.catalogLoadFailed'))
      })
      .finally(() => {
        if (active) setCatalogLoading(false)
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    let active = true
    api.get<{ space_groups?: SpaceGroupOption[] }>('/api/rag/space-groups')
      .then(response => {
        if (active) setSpaceGroups(Array.isArray(response?.space_groups) ? response.space_groups : [])
      })
      .catch(() => {
        // 空间群标准表不可用时降级为纯自由输入，不阻塞校对
      })
    return () => { active = false }
  }, [])

  useEffect(() => {
    if (draftOverride !== undefined) {
      const normalized = normalizeUploadDraft(draftOverride)
      setDraft(normalized)
      setLoading(false)
      setDirty(false)
      setError('')
      setIssues([])
      return undefined
    }
    const controller = new AbortController()
    setLoading(true)
    api.get<{ ok: boolean; data: UploadDraft }>(
      `/api/rag/upload-tasks/${taskId}/draft`,
      { signal: controller.signal },
    ).then(response => {
      const normalized = normalizeUploadDraft(unwrapData(response))
      setDraft(normalized)
      setDirty(false)
      setError('')
    }).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason.message || t('upload.draftLoadFailed'))
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [taskId, draftOverride])

  const changeDraft = useCallback((updater: (current: UploadDraft) => UploadDraft) => {
    setDraft(current => current ? updater(current) : current)
    revisionRef.current += 1
    setDirty(true)
    setError('')
  }, [])

  const setPaperField = (field: keyof UploadDraft['paper'], value: unknown) => {
    changeDraft(current => ({ ...current, paper: { ...current.paper, [field]: value } }))
  }

  const setAuthors = (values: string[]) => {
    const authors = values.map(value => value.trim()).filter((value, index, all) => value && all.indexOf(value) === index)
    changeDraft(current => ({
      ...current,
      paper: {
        ...current.paper,
        authors,
        corresponding_authors: (current.paper.corresponding_authors || []).filter(author => authors.includes(author)),
        co_first_authors: (current.paper.co_first_authors || []).filter(author => authors.includes(author)),
      },
    }))
    if (authorMenu && !authors.includes(authorMenu.author)) setAuthorMenu(null)
  }

  const commitAuthorInput = (raw = authorInput) => {
    const author = raw.trim().replace(/[，,]+/g, '').trim()
    if (!author) { setAuthorInput(''); return }
    const authors = draft?.paper.authors || []
    if (!authors.includes(author)) setAuthors([...authors, author])
    setAuthorInput('')
  }

  const toggleAuthorRole = (field: AuthorRoleField, author: string) => {
    changeDraft(current => {
      const selected = current.paper[field] || []
      return {
        ...current,
        paper: {
          ...current.paper,
          [field]: selected.includes(author)
            ? selected.filter(item => item !== author)
            : [...selected, author],
        },
      }
    })
  }

  const setDraftField = (field: keyof UploadDraft, value: unknown) => {
    changeDraft(current => ({ ...current, [field]: value }))
  }

  const saveDraft = useCallback(async (showResult = false): Promise<boolean> => {
    if (!draft || saving || readOnly) return !dirty
    const revision = revisionRef.current
    setSaving(true)
    try {
      await api.put(`/api/rag/upload-tasks/${taskId}/draft`, draft)
      if (revision === revisionRef.current) setDirty(false)
      setLastSavedAt(new Date().toLocaleTimeString(lang === 'zh' ? 'zh-CN' : 'en-US', { hour: '2-digit', minute: '2-digit' }))
      if (showResult) setError('')
      return true
    } catch (reason) {
      setError(failureMessage(t, 'save', reason, t('upload.draftSaveFailed')))
      return false
    } finally {
      setSaving(false)
    }
  }, [dirty, draft, saving, taskId, readOnly, t, lang])

  useEffect(() => {
    if (!dirty || !draft || saving) return
    const timer = window.setTimeout(() => { void saveDraft(false) }, 5000)
    return () => window.clearTimeout(timer)
  }, [dirty, draft, saveDraft, saving])

  // 返回全部问题而不是遇到第一条就退出：用户需要一次看清所有待补字段，
  // 而不是每修一条再提交一次才发现下一条
  const validate = (): ValidationIssue[] => {
    if (!draft) return []
    const issues: ValidationIssue[] = []
    if (!draft.paper.title?.trim()) {
      issues.push({ field: 'paper.title', message: t('upload.titleRequired') })
    }
    if (draft.paper.doi && !/^10\.\d{4,9}\/\S+$/i.test(draft.paper.doi.trim())) {
      issues.push({ field: 'paper.doi', message: t('upload.doiInvalid') })
    }
    if (!draft.paper.paper_type || draft.paper.paper_type === 'unknown') {
      issues.push({ field: 'paper.paper_type', message: t('upload.paperTypeRequired') })
    }
    if (draft.paper.paper_type === 'theoretical' && !draft.paper.theoretical_subtype) {
      issues.push({ field: 'paper.theoretical_subtype', message: t('upload.theoreticalSubtypeRequired') })
    }
    if (draft.paper.paper_type !== 'review' && draft.material_states.length === 0) {
      issues.push({ field: 'material_states', message: t('upload.materialStateRequired') })
    }
    draft.material_states.forEach((state, stateIndex) => {
      const label = t('upload.materialStateLabel', { index: stateIndex + 1 })
      if (!state.material?.trim()) {
        issues.push({ stateIndex, field: `material_states[${stateIndex}].material`, message: t('upload.missingMaterial', { label }) })
      }
      if (state.reported_space_group_number != null &&
        (state.reported_space_group_number < 1 || state.reported_space_group_number > 230)) {
        issues.push({
          stateIndex,
          field: `material_states[${stateIndex}].reported_space_group_number`,
          message: t('upload.spaceGroupRangeInvalid', { label }),
        })
      }
      if ([state.calculation_context?.lambda_ep, state.calculation_context?.omega_log_k, state.calculation_context?.mu_star]
        .some(value => value != null && value < 0)) {
        issues.push({
          stateIndex,
          field: `material_states[${stateIndex}].calculation_context`,
          message: t('upload.negativeCalcParam', { label }),
        })
      }
      const invalidTc = (state.tc_results || []).findIndex(item =>
        !item.value_raw?.trim() && item.tc_value_k == null && (item.tc_min_k == null || item.tc_max_k == null))
      if (invalidTc >= 0) {
        issues.push({
          stateIndex,
          field: `material_states[${stateIndex}].tc_results`,
          message: t('upload.tcMissingValue', { label, n: invalidTc + 1 }),
        })
      }
      const invalidProperty = (state.properties || []).findIndex(item =>
        !String(item.name || item.name_raw || '').trim() ||
        (!item.value_raw?.trim() && item.value == null && item.value_min == null && item.value_max == null))
      if (invalidProperty >= 0) {
        issues.push({
          stateIndex,
          field: `material_states[${stateIndex}].properties`,
          message: t('upload.propertyIncomplete', { label, n: invalidProperty + 1 }),
        })
      }
    })
    return issues
  }

  // 把出错位置暴露给用户：展开可能被折叠的卡片（MaterialStatesEditor 收到 issues 后展开），
  // 再滚动并聚焦到第一个出错字段
  const revealIssues = (nextIssues: ValidationIssue[]) => {
    setIssues(nextIssues)
    const first = nextIssues[0]
    if (!first) return
    // 等展开后的 DOM 就绪再定位，否则折叠中的字段无法滚动到位
    window.setTimeout(() => {
      const anchor = document.querySelector<HTMLElement>(`[data-issue-field="${first.field}"]`)
      if (!anchor) return
      // 少数旧浏览器与内嵌 WebView 没有 scrollIntoView；缺失时仅聚焦，不能让定位逻辑抛错
      anchor.scrollIntoView?.({ block: 'center', behavior: 'smooth' })
      const focusable = anchor.matches('input,textarea,select')
        ? anchor
        : anchor.querySelector<HTMLElement>('input,textarea,select,[tabindex]')
      focusable?.focus()
    }, 0)
  }

  const submit = async () => {
    const validationIssues = validate()
    if (validationIssues.length > 0) {
      setError(validationIssues.map(item => item.message).join(t('upload.sentenceSeparator')))
      revealIssues(validationIssues)
      return
    }
    setIssues([])
    setSubmitting(true)
    try {
      if (!(await saveDraft(false))) return
      let response: SubmitResponse | { data: SubmitResponse }
      try {
        response = await api.post<SubmitResponse | { data: SubmitResponse }>(`/api/rag/upload-tasks/${taskId}/submit`)
      } catch (reason) {
        const apiError = reason as ApiError
        if (apiError.code !== 'consistency_ack_required' || !window.confirm(t('upload.consistencyConfirm'))) throw reason
        response = await api.post<SubmitResponse | { data: SubmitResponse }>(
          `/api/rag/upload-tasks/${taskId}/submit`,
          { consistency_acknowledged: true },
        )
      }
      onSubmitted(unwrapData(response).paper_id)
    } catch (reason) {
      const apiError = reason as ApiError
      if (apiError.status === 409 && apiError.existingPaperId) {
        setError(t('upload.doiExists', { id: apiError.existingPaperId }))
      } else {
        setError(failureMessage(t, 'submit', reason, t('upload.submitReviewFailed')))
        // 后端独有的校验规则（材料家族、压强区间等）也要能定位到卡片
        const backendReason = apiError.status === 400 ? backendErrorReason(reason) : null
        const backendStateIndex = backendReason ? stateIndexFromMessage(backendReason.message) : undefined
        if (backendStateIndex != null) {
          revealIssues([{
            stateIndex: backendStateIndex,
            field: `material_states[${backendStateIndex}].material`,
            message: backendReason!.message,
          }])
        }
      }
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}><CircularProgress /></Box>
  }
  if (!draft) return <Alert severity="error">{error || t('upload.draftMissing')}</Alert>

  const ai = draft.ai_original || {}
  const aiPaper = ai.paper || {}

  // 统一给出错字段加定位锚点、错误态与说明文字，避免每处重复拼装
  const issueOf = (field: string) => issues.find(item => item.field === field)
  const hasIssue = (field: string) => Boolean(issueOf(field))
  const issueProps = (field: string) => {
    const issue = issueOf(field)
    return {
      'data-issue-field': field,
      error: Boolean(issue),
      helperText: issue?.message,
    }
  }
  // Select/复合区域用不了 TextField 的 helperText，单独渲染说明文字
  const IssueText: React.FC<{ field: string }> = ({ field }) => {
    const issue = issueOf(field)
    if (!issue) return null
    return <FormHelperText error>{issue.message}</FormHelperText>
  }
  const classificationEvidence = draft.classification_evidence || []

  return (
    <Box sx={{ mt: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="h6" fontWeight={700}>{readOnly ? t('upload.aiDraftTitle') : t('upload.checkAiDraftTitle')}</Typography>
          <Typography variant="body2" color="text.secondary">
            {readOnly ? (statusNote || t('upload.defaultNote')) : t('upload.editorSubtitle')}
          </Typography>
        </Box>
        {readOnly ? (
          <Chip size="small" color="info" label={t('upload.readOnlyBadge')} />
        ) : (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="caption" color={error ? 'error' : 'text.secondary'}>
            {saving ? t('common.saving') : dirty ? t('upload.autoSaveHint') : lastSavedAt ? t('upload.savedAt', { time: lastSavedAt }) : t('upload.draftLoaded')}
          </Typography>
          <Button variant="outlined" startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
            disabled={saving || submitting} onClick={() => void saveDraft(true)}>{t('upload.saveNow')}</Button>
          <Button variant="contained" startIcon={submitting ? <CircularProgress size={16} /> : <SendIcon />}
            disabled={saving || submitting} onClick={() => void submit()}>{t('upload.submitReview')}</Button>
        </Box>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Box sx={readOnly ? { pointerEvents: 'none', '& .MuiButton-root': { display: 'none' } } : undefined}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, '& > *': { minWidth: 0 } }}>
        <Box>
          <TextField fullWidth label={t('upload.title')} value={draft.paper.title || ''}
            {...issueProps('paper.title')}
            onChange={event => setPaperField('title', event.target.value)} />
          <EvidenceNotes label={t('upload.title')} aiValue={aiPaper.title} />
        </Box>
        <Box>
          <TextField fullWidth label="DOI" value={draft.paper.doi || ''}
            {...issueProps('paper.doi')}
            onChange={event => setPaperField('doi', event.target.value.trim())} />
          <EvidenceNotes label="DOI" aiValue={aiPaper.doi} />
        </Box>
        <Box>
          <Autocomplete
            multiple
            freeSolo
            forcePopupIcon={false}
            options={draft.paper.authors || []}
            value={draft.paper.authors || []}
            inputValue={authorInput}
            onInputChange={(_, value, reason) => { if (reason !== 'reset') setAuthorInput(value) }}
            onClose={(_, reason) => { if (reason === 'blur') commitAuthorInput() }}
            onChange={(_, values) => { setAuthors(values); setAuthorInput('') }}
            renderTags={(values, getTagProps) => values.map((author, index) => {
              const { key, ...tagProps } = getTagProps({ index })
              const roles = [
                draft.paper.corresponding_authors?.includes(author) ? t('upload.correspondingAuthor') : '',
                draft.paper.co_first_authors?.includes(author) ? t('upload.coFirstAuthor') : '',
              ].filter(Boolean)
              return (
                <Chip
                  {...tagProps}
                  key={key}
                  label={[author, ...roles].join(' · ')}
                  title={t('upload.setAuthorRoleTitle')}
                  onClick={event => setAuthorMenu({ author, anchorEl: event.currentTarget })}
                  onDelete={() => setAuthors(values.filter(item => item !== author))}
                />
              )
            })}
            renderInput={params => (
              <TextField {...params} label={t('upload.authorsField')} placeholder={(draft.paper.authors || []).length ? '' : t('upload.authorPlaceholder')} onKeyDown={event => { if ((event.key === 'Enter' || event.key === ',' || event.key === '，') && authorInput.trim()) { event.preventDefault(); commitAuthorInput() } }} />
            )}
            sx={{
              '& .MuiOutlinedInput-root': {
                flexWrap: 'nowrap',
                overflowX: 'auto',
                overflowY: 'hidden',
                scrollbarWidth: 'thin',
              },
              '& .MuiAutocomplete-tag': { flexShrink: 0 },
              '& .MuiAutocomplete-input': { minWidth: '10ch !important' },
            }}
          />
          <Menu anchorEl={authorMenu?.anchorEl} open={Boolean(authorMenu)} onClose={() => setAuthorMenu(null)}>
            {authorMenu && ([
              ['corresponding_authors', t('upload.correspondingAuthor')],
              ['co_first_authors', t('upload.coFirstAuthor')],
            ] as const).map(([field, label]) => (
              <MenuItem key={field} onClick={() => toggleAuthorRole(field, authorMenu.author)}>
                <Checkbox checked={(draft.paper[field] || []).includes(authorMenu.author)} />
                <ListItemText primary={label} />
              </MenuItem>
            ))}
          </Menu>
          <EvidenceNotes label={t('upload.authorsField')} aiValue={aiPaper.authors} />
        </Box>
        <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr 1fr', sm: '2fr 1fr 1fr 1fr' }, gap: 1 }}>
          <TextField label={t('upload.journal')} value={draft.paper.journal || ''}
            onChange={event => setPaperField('journal', event.target.value)} />
          <TextField label={t('upload.year')} type="number" value={draft.paper.year ?? ''}
            onChange={event => setPaperField('year', event.target.value ? Number(event.target.value) : null)} />
          <TextField label={t('upload.volume')} value={draft.paper.volume || ''}
            onChange={event => setPaperField('volume', event.target.value)} />
          <TextField label={t('upload.pages')} value={draft.paper.pages || ''}
            onChange={event => setPaperField('pages', event.target.value)} />
          <Box sx={{ gridColumn: '1 / -1' }}>
            <EvidenceNotes label={t('upload.journalInfo')} aiValue={[aiPaper.journal, aiPaper.year, aiPaper.volume, aiPaper.pages].filter(Boolean).join(' · ')} />
          </Box>
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2, '& > *': { minWidth: 0 } }}>
        <FormControl fullWidth error={hasIssue('paper.paper_type')} data-issue-field="paper.paper_type">
          <InputLabel>{t('upload.paperTypeField')}</InputLabel>
          <Select label={t('upload.paperTypeField')} value={draft.paper.paper_type || 'unknown'}
            onChange={event => setPaperField('paper_type', event.target.value)}>
            {PAPER_TYPE_VALUES.map(value => <MenuItem key={value} value={value}>{dict.enums.paperType[value]}</MenuItem>)}
          </Select>
          <IssueText field="paper.paper_type" />
          <EvidenceNotes label={t('upload.paperTypeField')} aiValue={aiPaper.paper_type} evidence={classificationEvidence} />
        </FormControl>
        <FormControl fullWidth disabled={draft.paper.paper_type !== 'theoretical'}
          error={hasIssue('paper.theoretical_subtype')} data-issue-field="paper.theoretical_subtype">
          <InputLabel>{t('upload.theoreticalSubtypeField')}</InputLabel>
          <Select label={t('upload.theoreticalSubtypeField')} value={draft.paper.theoretical_subtype || ''}
            onChange={event => setPaperField('theoretical_subtype', event.target.value || null)}>
            <MenuItem value="calculation">{dict.enums.theoreticalSubtype.calculation}</MenuItem>
            <MenuItem value="method">{dict.enums.theoreticalSubtype.method}</MenuItem>
            <MenuItem value="theory">{dict.enums.theoreticalSubtype.theory}</MenuItem>
          </Select>
          <IssueText field="paper.theoretical_subtype" />
          <EvidenceNotes label={t('upload.theoreticalSubtypeField')} aiValue={aiPaper.theoretical_subtype} />
        </FormControl>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2, '& > *': { minWidth: 0 } }}>
        {[
          ['keywords_tags', t('upload.keywordsLabel')],
          ['methodology', t('upload.methodologyLabel')],
        ].map(([field, label]) => (
          <Box key={field}>
            <TextField fullWidth label={label} multiline minRows={3}
              value={toLines(draft.paper[field as keyof UploadDraft['paper']] as string[] | undefined)}
              onChange={event => setPaperField(field as keyof UploadDraft['paper'], fromLines(event.target.value))} />
            <EvidenceNotes
              label={label}
              aiValue={aiPaper[field as keyof typeof aiPaper]}
              evidence={draft.field_evidence?.[field]}
            />
          </Box>
        ))}
      </Box>

      {[
        ['abstract', t('upload.abstractLabel'), 4],
        ['summary', t('upload.summaryLabel'), 3],
        ['key_finding', t('upload.keyFindingLabel'), 3],
      ].map(([field, label, rows]) => (
        <Box key={String(field)} sx={{ mt: 2 }}>
          <TextField fullWidth label={String(label)} multiline minRows={Number(rows)}
            value={String(draft.paper[field as keyof UploadDraft['paper']] || '')}
            onChange={event => setPaperField(field as keyof UploadDraft['paper'], event.target.value)} />
          <EvidenceNotes label={String(label)} aiValue={aiPaper[field as keyof typeof aiPaper]} />
        </Box>
      ))}

      <Box sx={{ mt: 2 }}>
        <TextField fullWidth label={t('upload.researchMotivationLabel')} multiline minRows={3}
          value={draft.research_motivation || ''}
          onChange={event => setDraftField('research_motivation', event.target.value)} />
        <EvidenceNotes label={t('upload.researchMotivationLabel')} aiValue={ai.research_motivation} evidence={classificationEvidence} />
      </Box>

      <MaterialStatesEditor
        states={draft.material_states}
        onChange={nextStates => setDraftField('material_states', nextStates)}
        catalogs={catalogs}
        catalogLoading={catalogLoading}
        catalogError={catalogError}
        readOnly={readOnly}
        issues={issues}
        structureCandidates={draft.structure_candidates || []}
        onStructureCandidatesChange={next => setDraftField('structure_candidates', next)}
        spaceGroups={spaceGroups}
        aiMaterialStates={ai.material_states}
        taskId={taskId}
        paperType={draft.paper.paper_type}
        onError={setError}
      />
    </Box>
    </Box>
  )
}

export default UploadTaskEditor
