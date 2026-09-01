import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Checkbox, Chip, CircularProgress, Collapse,
  FormControl, FormHelperText, InputLabel, ListItemText, Menu, MenuItem, Select, TextField, Typography,
  useMediaQuery,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import SaveIcon from '@mui/icons-material/Save'
import SendIcon from '@mui/icons-material/Send'
import { api, ApiError } from '../lib/api'
import {
  ClassificationCatalogs,
  ClassificationTerm,
  DEFAULT_MATERIAL_DIMENSIONALITIES,
  familyName,
  loadClassificationCatalogs,
  pendingSelection,
  selectionForTerm,
} from '../lib/classifications'
import { useLanguage } from '../context/LanguageContext'
import ClassificationAutocomplete from './ClassificationAutocomplete'
import StructureCandidatePanel from './StructureCandidatePanel'
import {
  CRYSTAL_SYSTEM_VALUES, CrystalSystem, DraftKeyProperty, DraftMaterialState, DraftTcResult, SourceEvidence, StructureCandidate, UploadDraft,
  evidenceList, normalizeUploadDraft, unwrapData,
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

const SUPERCONDUCTOR_KIND_VALUES = ['conventional', 'unconventional'] as const

const TC_METHOD_VALUES = [
  'unknown', 'experimental', 'mcmillan', 'allen_dynes',
  'isotropic_eliashberg', 'anisotropic_eliashberg', 'scdft', 'other',
] as const

const ENERGY_ABOVE_HULL_NAME = 'energy above hull'

interface SpaceGroupOption {
  number: number
  symbol: string
}

// 晶系↔群号静态范围表（与 backend/services/space_groups.py 一致；群号是晶系的权威来源）
const CRYSTAL_SYSTEM_NUMBER_RANGES: Array<{ value: Exclude<CrystalSystem, 'unknown'>; min: number; max: number }> = [
  { value: 'triclinic', min: 1, max: 2 },
  { value: 'monoclinic', min: 3, max: 15 },
  { value: 'orthorhombic', min: 16, max: 74 },
  { value: 'tetragonal', min: 75, max: 142 },
  { value: 'trigonal', min: 143, max: 167 },
  { value: 'hexagonal', min: 168, max: 194 },
  { value: 'cubic', min: 195, max: 230 },
]

const crystalSystemForNumber = (value: number): CrystalSystem => (
  CRYSTAL_SYSTEM_NUMBER_RANGES.find(range => value >= range.min && value <= range.max)?.value ?? 'unknown'
)

const toLines = (value: string[] | undefined) => (value || []).join('\n')
const fromLines = (value: string) => value.split(/[\n,，]/).map(item => item.trim()).filter(Boolean)

// 默认折叠规则：卡片数 ≤2 全部展开，否则仅第一张展开
const defaultCollapsedStates = (count: number): Record<number, boolean> => (
  count > 2
    ? Object.fromEntries(Array.from({ length: count }, (_, index) => [index, index !== 0]))
    : {}
)

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

// 一条校验问题。stateIndex 为空表示论文级问题；field 用于在 DOM 中定位出错输入框
interface ValidationIssue {
  stateIndex?: number
  field: string
  message: string
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

const COLLAPSED_EVIDENCE_HEIGHT = 120
// AI 建议折叠后仅保留单行（MUI caption 行高约 20px），完整文本仍保留在草稿数据中
const COLLAPSED_AI_LINE_HEIGHT = 20

const EvidenceNotes: React.FC<{
  label: string
  aiValue?: unknown
  evidence?: SourceEvidence | SourceEvidence[] | null
}> = ({ label, aiValue, evidence }) => {
  const { t } = useLanguage()
  const items = evidenceList(evidence)
  const contentId = useId()
  const contentRef = useRef<HTMLDivElement>(null)
  const overflowRef = useRef(false)
  const [isOverflowing, setIsOverflowing] = useState(false)
  const [expanded, setExpanded] = useState(false)
  const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')

  const displayValue = (value: unknown) => {
    if (value == null || value === '') return t('common.notProvided')
    if (Array.isArray(value)) return value.join(t('upload.listSeparator')) || t('common.notProvided')
    if (typeof value === 'object') return JSON.stringify(value)
    return String(value)
  }

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
        collapsedSize={isOverflowing ? COLLAPSED_AI_LINE_HEIGHT : 0}
        timeout={prefersReducedMotion ? 0 : 180}
      >
        <Box id={contentId} ref={contentRef} sx={{ minWidth: 0 }}>
          {aiValue !== undefined && (
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              style={isOverflowing && !expanded
                ? { whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }
                : { whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}
            >
              {t('upload.aiSuggestion', { value: displayValue(aiValue) })}
            </Typography>
          )}
          {items.map((item, index) => (
            <Typography key={index} variant="caption" color="text.secondary" display="block" sx={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>
              {[item.section, item.page ? t('upload.pageRef', { page: item.page }) : ''].filter(Boolean).join(' · ') || t('upload.originalText')}
              {item.quote ? t('upload.quoteSuffix', { quote: item.quote }) : ''}
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
            aria-label={t('upload.toggleAiExplainAria', {
              action: expanded ? t('upload.collapse') : t('upload.expand'),
              label,
            })}
            onClick={() => setExpanded(value => !value)}
            endIcon={<ExpandMoreIcon sx={{
              transform: expanded ? 'rotate(180deg)' : 'none',
              transition: prefersReducedMotion ? 'none' : 'transform 180ms ease',
            }} />}
            sx={{ minHeight: 28, px: 1 }}
          >
            {expanded ? t('upload.collapseAiExplain') : t('upload.expandAiExplain')}
          </Button>
        </Box>
      )}
    </Box>
  )
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
  const [structureUploading, setStructureUploading] = useState<Record<number, boolean>>({})
  const [authorInput, setAuthorInput] = useState('')
  const [catalogs, setCatalogs] = useState<ClassificationCatalogs | null>(null)
  const [catalogLoading, setCatalogLoading] = useState(true)
  const [catalogError, setCatalogError] = useState('')
  // 折叠状态仅存在浏览器会话内，不写入草稿、不参与自动保存
  const [collapsedStates, setCollapsedStates] = useState<Record<number, boolean>>({})
  const [elementCountEdits, setElementCountEdits] = useState<Record<number, { text: string; invalid: boolean }>>({})
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
      setCollapsedStates(defaultCollapsedStates(normalized.material_states.length))
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
      setCollapsedStates(defaultCollapsedStates(normalized.material_states.length))
      setDirty(false)
      setError('')
    }).catch((reason: Error) => {
      if (reason.name !== 'AbortError') setError(reason.message || t('upload.draftLoadFailed'))
    }).finally(() => setLoading(false))
    return () => controller.abort()
  }, [taskId, draftOverride])

  // 材料状态数组变化时调和折叠状态：保留已有卡片的手动选择，新卡片按默认规则初始化
  const materialStateCount = draft?.material_states.length ?? 0
  useEffect(() => {
    setCollapsedStates(current => {
      const next: Record<number, boolean> = {}
      for (let index = 0; index < materialStateCount; index += 1) {
        next[index] = current[index] ?? (materialStateCount > 2 && index !== 0)
      }
      return next
    })
    setElementCountEdits(current => {
      const kept = Object.entries(current).filter(([key]) => Number(key) < materialStateCount)
      return kept.length === Object.keys(current).length ? current : Object.fromEntries(kept)
    })
  }, [materialStateCount])

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

  const updateMaterialState = (index: number, field: keyof DraftMaterialState, value: unknown) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) =>
        itemIndex === index ? { ...item, [field]: value } : item),
    }))
  }

  // 群号合法（1–230）时按标准表反查符号并按范围表改写晶系（群号权威）；非法输入只保存原值不联动
  const changeSpaceGroupNumber = (index: number, raw: string) => {
    const trimmed = raw.trim()
    const parsed = trimmed === '' ? null : Number(trimmed)
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) => {
        if (itemIndex !== index) return item
        if (parsed != null && Number.isInteger(parsed) && parsed >= 1 && parsed <= 230) {
          return {
            ...item,
            reported_space_group_number: parsed,
            reported_space_group_symbol: spaceGroups.find(option => option.number === parsed)?.symbol
              ?? item.reported_space_group_symbol ?? null,
            crystal_system: crystalSystemForNumber(parsed),
          }
        }
        return { ...item, reported_space_group_number: Number.isNaN(parsed) ? null : parsed }
      }),
    }))
  }

  const applyClassificationToSameMaterial = (sourceIndex: number) => {
    changeDraft(current => {
      const source = current.material_states[sourceIndex]
      const material = source.material?.trim().toLocaleLowerCase()
      if (!material) return current
      return {
        ...current,
        material_states: current.material_states.map((state, index) => (
          index !== sourceIndex && state.material?.trim().toLocaleLowerCase() === material
            ? {
                ...state,
                material_family: source.material_family ? { ...source.material_family } : null,
                structure_families: (source.structure_families || []).map(item => ({ ...item })),
                material_dimensionality: source.material_dimensionality || 'unknown',
              }
            : state
        )),
      }
    })
  }

  const uploadStructureForState = async (stateIndex: number, file: File) => {
    setStructureUploading(current => ({ ...current, [stateIndex]: true }))
    try {
      const body = new FormData()
      body.append('material_state_index', String(stateIndex))
      body.append('file', file)
      const response = await api.post<{ ok: boolean; data: StructureCandidate }>(
        `/api/rag/upload-tasks/${taskId}/structure-candidates`, body,
      )
      const candidate = unwrapData(response)
      changeDraft(current => ({
        ...current,
        structure_candidates: [...(current.structure_candidates || []).filter(item => item.candidate_id !== candidate.candidate_id), candidate],
      }))
      setError('')
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : t('upload.structureUploadFailed')
      setError(message)
    } finally {
      setStructureUploading(current => ({ ...current, [stateIndex]: false }))
    }
  }

  const setAllCollapsed = (value: boolean) => {
    setCollapsedStates(value
      ? Object.fromEntries((draft?.material_states || []).map((_, index) => [index, true]))
      : {})
  }

  // 元素种类数：仅接受 1–118 的整数，非法输入即时提示且不写入草稿；手动编辑后锁定，清空则恢复服务端自动计算
  const changeElementCount = (index: number, raw: string) => {
    const trimmed = raw.trim()
    if (trimmed === '') {
      setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: false } }))
      changeDraft(current => ({
        ...current,
        material_states: current.material_states.map((item, itemIndex) =>
          itemIndex === index ? { ...item, element_count: null, element_count_locked: false } : item),
      }))
      return
    }
    const parsed = Number(trimmed)
    if (!/^\d+$/.test(trimmed) || parsed < 1 || parsed > 118) {
      setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: true } }))
      return
    }
    setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: false } }))
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) =>
        itemIndex === index ? { ...item, element_count: parsed, element_count_locked: true } : item),
    }))
  }

  const updateTcCalculationContext = (
    stateIndex: number,
    resultIndex: number,
    field: 'lambda_ep' | 'omega_log_k' | 'mu_star',
    value: number | null,
  ) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((state, index) => index === stateIndex ? {
        ...state,
        tc_results: (state.tc_results || []).map((item, itemIndex) =>
          itemIndex === resultIndex
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
      } : state),
    }))
  }

  // 常规 (BCS) 类型的 Tc 条目带独立计算上下文；首个条目用状态级旧值一次性预填 λ/ωlog
  const addTcResult = (index: number) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) => {
        if (itemIndex !== index) return item
        const isConventional = (item.superconductor_kind || 'unknown') === 'conventional'
        const legacy = item.calculation_context
        const prefillLegacy = isConventional
          && (legacy?.lambda_ep != null || legacy?.omega_log_k != null)
          && !(item.tc_results || []).some(entry => entry.calculation_context)
        const entry: DraftTcResult = {
          result_kind: item.state_kind === 'experimental' ? 'experimental' : 'theoretical',
          tc_method: item.state_kind === 'experimental' ? 'experimental' : 'unknown',
          tc_value_k: null, tc_min_k: null, tc_max_k: null, value_raw: '', unit_raw: 'K',
        }
        if (isConventional) {
          entry.calculation_context = {
            phonon_nuclear_treatment: 'unknown',
            lambda_ep: prefillLegacy ? legacy?.lambda_ep ?? null : null,
            omega_log_k: prefillLegacy ? legacy?.omega_log_k ?? null : null,
            mu_star: null,
          }
        }
        return { ...item, tc_results: [...(item.tc_results || []), entry] }
      }),
    }))
  }

  const removeTcResult = (stateIndex: number, resultIndex: number) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) => itemIndex === stateIndex ? {
        ...item, tc_results: (item.tc_results || []).filter((_, tcIndex) => tcIndex !== resultIndex),
      } : item),
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

  const addEnergyAboveHull = (index: number) => {
    changeDraft(current => ({
      ...current,
      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
        ...item,
        properties: [...(item.properties || []), {
          name: ENERGY_ABOVE_HULL_NAME, name_raw: ENERGY_ABOVE_HULL_NAME, value_raw: '', unit: 'eV/atom',
        }],
      } : item),
    }))
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

  // 把出错位置暴露给用户：展开可能被折叠的卡片，再滚动并聚焦到第一个出错字段
  const revealIssues = (nextIssues: ValidationIssue[]) => {
    setIssues(nextIssues)
    const first = nextIssues[0]
    if (!first) return
    if (first.stateIndex != null) {
      setCollapsedStates(current => ({ ...current, [first.stateIndex as number]: false }))
    }
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

      <Box sx={{ mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" fontWeight={700}>{t('upload.materialStatesTitle')}</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            {draft.material_states.length > 0 && (
              <>
                <Button size="small" onClick={() => setAllCollapsed(true)}>{t('common.collapseAll')}</Button>
                <Button size="small" onClick={() => setAllCollapsed(false)}>{t('common.expandAll')}</Button>
              </>
            )}
            <Button startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
            ...current,
            material_states: [...current.material_states, {
              material: '',
              material_family: null,
              structure_families: [],
              element_count: null,
              element_count_locked: false,
              material_dimensionality: 'unknown',
              pressure_value_gpa: null,
              state_kind: current.paper.paper_type === 'experimental' ? 'experimental' : 'theoretical',
              superconductor_kind: 'unknown',
              crystal_system: 'unknown',
              reported_space_group_symbol: null,
              reported_space_group_number: null,
              calculation_context: current.paper.paper_type === 'experimental' ? null : {
                phonon_nuclear_treatment: 'unknown', lambda_ep: null, omega_log_k: null, mu_star: null,
              },
              experimental_context: current.paper.paper_type === 'experimental' ? { tc_criterion: 'unknown' } : null,
              tc_results: [],
              properties: [],
            }],
            }))}>{t('upload.addMaterialState')}</Button>
          </Box>
        </Box>

      <Box data-testid="material-states-list" sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 1.5, mt: 1.5 }}>
        {draft.material_states.map((state, index) => {
          const aiState = ai.material_states?.[index]
          const stateCandidates = (draft.structure_candidates || []).filter(candidate => candidate.material_state_ref === `material_states[${index}]`)
          const isCollapsed = !readOnly && Boolean(collapsedStates[index])
          const isConventional = (state.superconductor_kind || 'unknown') === 'conventional'
          // 晶系未知时显示全部 230 条空间群，否则仅显示该晶系群号范围内的符号
          const crystalSystem = state.crystal_system || 'unknown'
          const spaceGroupOptions = crystalSystem === 'unknown'
            ? spaceGroups
            : spaceGroups.filter(option => crystalSystemForNumber(option.number) === crystalSystem)
          const hasEnergyAboveHull = (state.properties || []).some(item =>
            [item.name, item.name_raw].some(value => String(value || '').trim().toLowerCase() === ENERGY_ABOVE_HULL_NAME))
          return (
            <Card key={index} variant="outlined" sx={{ width: '100%' }}>
              <CardContent>
                <Box
                  role="button"
                  aria-expanded={!isCollapsed}
                  aria-controls={`material-state-${index}-content`}
                  onClick={() => setCollapsedStates(current => ({ ...current, [index]: !current[index] }))}
                  sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: isCollapsed ? 0 : 1.5, cursor: 'pointer', userSelect: 'none' }}
                >
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', minWidth: 0 }}>
                    <ExpandMoreIcon fontSize="small" sx={{
                      transform: isCollapsed ? 'none' : 'rotate(180deg)',
                      transition: 'transform 180ms ease',
                    }} />
                    <Typography variant="subtitle2" fontWeight={700}>{t('upload.materialStateNumber', { index: index + 1 })}</Typography>
                    {state.material?.trim() && (
                      <Typography variant="body2" color="text.secondary" noWrap>{state.material}</Typography>
                    )}
                    {state.material_family && draft.material_states.some((item, itemIndex) => (
                      itemIndex !== index
                      && item.material?.trim().toLocaleLowerCase() === state.material?.trim().toLocaleLowerCase()
                    )) && (
                      <Button size="small" onClick={event => {
                        event.stopPropagation()
                        applyClassificationToSameMaterial(index)
                      }}>{t('upload.applyToSameMaterial')}</Button>
                    )}
                  </Box>
                  <Button size="small" color="error" startIcon={<DeleteIcon />}
                    onClick={event => {
                      event.stopPropagation()
                      changeDraft(current => ({
                        ...current,
                        material_states: current.material_states.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }}>{t('common.delete')}</Button>
                </Box>
                <Collapse in={!isCollapsed} timeout="auto" id={`material-state-${index}-content`}>
                <Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1.5 }}>
                  <TextField label={t('upload.materialField')} value={state.material || ''}
                    {...issueProps(`material_states[${index}].material`)}
                    onChange={event => updateMaterialState(index, 'material', event.target.value)} />
                  <ClassificationAutocomplete
                    label={t('upload.materialFamilyField')}
                    options={catalogs?.material_families || []}
                    value={state.material_family}
                    loading={catalogLoading}
                    error={catalogError}
                    onChange={value => updateMaterialState(index, 'material_family', value)}
                  />
                  <TextField
                    label={t('upload.elementCountField')}
                    value={elementCountEdits[index]?.text ?? (state.element_count ?? '')}
                    error={Boolean(elementCountEdits[index]?.invalid)}
                    helperText={elementCountEdits[index]?.invalid ? t('upload.elementCountInvalid') : t('upload.elementCountAuto')}
                    onChange={event => changeElementCount(index, event.target.value)}
                  />
                  <FormControl fullWidth>
                    <InputLabel id={`material-dimensionality-${index}-label`}>{t('upload.materialDimensionalityField')}</InputLabel>
                    <Select
                      labelId={`material-dimensionality-${index}-label`}
                      label={t('upload.materialDimensionalityField')}
                      value={state.material_dimensionality || 'unknown'}
                      onChange={event => updateMaterialState(index, 'material_dimensionality', event.target.value)}
                    >
                      {(catalogs?.material_dimensionalities || DEFAULT_MATERIAL_DIMENSIONALITIES).map(option => (
                        <MenuItem key={option.value} value={option.value}>{dict.enums.materialDimensionality[option.value]}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Autocomplete<ClassificationTerm | string, true, false, true>
                    multiple
                    freeSolo
                    options={catalogs?.structure_families || []}
                    loading={catalogLoading}
                    value={(state.structure_families || []).map(selection => {
                      if (selection.id == null) return selection.name
                      const option = catalogs?.structure_families.find(item => item.id === selection.id)
                      return option || selection.name
                    })}
                    getOptionLabel={option => typeof option === 'string' ? option : familyName(option, lang)}
                    isOptionEqualToValue={(option, value) => (
                      typeof option !== 'string' && typeof value !== 'string' && option.id === value.id
                    )}
                    onChange={(_, values) => {
                      // D4：编辑器不再写入主项标记，新写入的 is_primary 一律为 false
                      updateMaterialState(index, 'structure_families', values.map(value => {
                        const selection = typeof value === 'string' ? pendingSelection(value) : selectionForTerm(value)
                        return selection ? { ...selection, is_primary: false } : null
                      }).filter(Boolean))
                    }}
                    renderInput={params => <TextField {...params} label={t('upload.structureFamiliesField')} error={Boolean(catalogError)} />}
                  />
                  <TextField label={t('upload.pressureField')} type="number" value={state.pressure_value_gpa ?? ''} helperText={state.pressure_value_gpa == null && state.pressure_raw ? t('upload.pressureRaw', { raw: state.pressure_raw, unit: state.pressure_unit_raw || '' }) : undefined}
                    onChange={event => updateMaterialState(index, 'pressure_value_gpa', event.target.value ? Number(event.target.value) : null)} />
                  <FormControl fullWidth>
                    <InputLabel id={`crystal-system-${index}-label`}>{t('upload.crystalSystemField')}</InputLabel>
                    <Select
                      labelId={`crystal-system-${index}-label`}
                      label={t('upload.crystalSystemField')}
                      value={crystalSystem}
                      onChange={event => updateMaterialState(index, 'crystal_system', event.target.value)}
                    >
                      {CRYSTAL_SYSTEM_VALUES.map(value => (
                        <MenuItem key={value} value={value}>{dict.enums.crystalSystem[value]}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Autocomplete<SpaceGroupOption | string, false, false, true>
                    freeSolo
                    options={spaceGroupOptions}
                    getOptionLabel={option => (typeof option === 'string' ? option : option.symbol)}
                    value={state.reported_space_group_symbol || ''}
                    onChange={(_, value) => {
                      if (value && typeof value !== 'string') {
                        changeDraft(current => ({
                          ...current,
                          material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                            ...item,
                            reported_space_group_symbol: value.symbol,
                            reported_space_group_number: value.number,
                            crystal_system: crystalSystemForNumber(value.number),
                          } : item),
                        }))
                        return
                      }
                      updateMaterialState(index, 'reported_space_group_symbol', value || null)
                    }}
                    onInputChange={(_, value, reason) => {
                      if (reason === 'input' || reason === 'clear') {
                        updateMaterialState(index, 'reported_space_group_symbol', value || null)
                      }
                    }}
                    renderInput={params => <TextField {...params} label={t('upload.spaceGroupSymbolField')} />}
                  />
                  <TextField label={t('upload.spaceGroupNumberField')} type="number" value={state.reported_space_group_number ?? ''}
                    {...issueProps(`material_states[${index}].reported_space_group_number`)}
                    onChange={event => changeSpaceGroupNumber(index, event.target.value)}
                    slotProps={{ htmlInput: { min: 1, max: 230 } }} />
                  <FormControl fullWidth>
                    <InputLabel id={`superconductor-kind-${index}-label`}>{t('upload.superconductorKindField')}</InputLabel>
                    <Select
                      labelId={`superconductor-kind-${index}-label`}
                      label={t('upload.superconductorKindField')}
                      value={state.superconductor_kind === 'conventional' || state.superconductor_kind === 'unconventional'
                        ? state.superconductor_kind
                        : ''}
                      displayEmpty
                      renderValue={value => value
                        ? dict.enums.superconductorKind[value as 'conventional' | 'unconventional'] || t('upload.selectPlaceholder')
                        : <Box component="span" sx={{ color: 'text.secondary' }}>{t('upload.selectPlaceholder')}</Box>}
                      onChange={event => updateMaterialState(index, 'superconductor_kind', event.target.value)}
                    >
                      {SUPERCONDUCTOR_KIND_VALUES.map(value => (
                        <MenuItem key={value} value={value}>{dict.enums.superconductorKind[value]}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
                <EvidenceNotes
                  label={t('upload.materialStateNumber', { index: index + 1 })}
                  aiValue={aiState ? `${aiState.material || ''} ${aiState.pressure_value_gpa ?? ''} GPa`.trim() : undefined}
                  evidence={state.space_group_evidence || aiState?.space_group_evidence}
                />

                <Box data-issue-field={`material_states[${index}].calculation_context`}
                  sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>{t('upload.criticalTempTitle')}</Typography>
                  <Button size="small" startIcon={<AddIcon />} onClick={() => addTcResult(index)}>{t('upload.addTc')}</Button>
                </Box>
                <IssueText field={`material_states[${index}].calculation_context`} />
                <Box data-issue-field={`material_states[${index}].tc_results`}>
                  <IssueText field={`material_states[${index}].tc_results`} />
                </Box>
                {(state.tc_results || []).map((result, resultIndex) => (
                  isConventional ? (
                    <Box key={resultIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1, mt: 1 }}>
                      <TextField size="small" label={t('upload.lambdaLabel')} type="number" value={result.calculation_context?.lambda_ep ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'lambda_ep', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label={t('upload.omegaLogLabel')} type="number" value={result.calculation_context?.omega_log_k ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'omega_log_k', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label={t('upload.muStarLabel')} type="number" value={result.calculation_context?.mu_star ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'mu_star', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label={t('upload.tcValueLabel')} type="number" value={result.tc_value_k ?? ''}
                        onChange={event => updateTcResult(index, resultIndex, 'tc_value_k', event.target.value ? Number(event.target.value) : null)} />
                      <FormControl size="small">
                        <InputLabel id={`tc-method-${index}-${resultIndex}-label`}>{t('upload.tcMethodField')}</InputLabel>
                        <Select
                          labelId={`tc-method-${index}-${resultIndex}-label`}
                          label={t('upload.tcMethodField')}
                          value={result.tc_method || 'unknown'}
                          onChange={event => updateTcResult(index, resultIndex, 'tc_method', event.target.value)}
                        >
                          {TC_METHOD_VALUES.map(value => <MenuItem key={value} value={value}>{dict.enums.tcMethod[value]}</MenuItem>)}
                        </Select>
                      </FormControl>
                      {result.tc_method === 'other' && (
                        <TextField size="small" label={t('upload.tcMethodCustomField')} value={result.tc_method_custom || ''}
                          onChange={event => updateTcResult(index, resultIndex, 'tc_method_custom', event.target.value || null)} />
                      )}
                      <Button size="small" color="error" onClick={() => removeTcResult(index, resultIndex)}>{t('common.delete')}</Button>
                    </Box>
                  ) : (
                    <Box key={resultIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr auto' }, gap: 1, mt: 1 }}>
                      <TextField size="small" label={t('upload.tcValueLabel')} type="number" value={result.tc_value_k ?? ''}
                        onChange={event => updateTcResult(index, resultIndex, 'tc_value_k', event.target.value ? Number(event.target.value) : null)} />
                      <Button size="small" color="error" onClick={() => removeTcResult(index, resultIndex)}>{t('common.delete')}</Button>
                    </Box>
                  )
                ))}

                <Box data-issue-field={`material_states[${index}].properties`}
                  sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>{t('upload.otherPropertiesTitle')}</Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button size="small" startIcon={<AddIcon />} disabled={hasEnergyAboveHull}
                      onClick={() => addEnergyAboveHull(index)}>{ENERGY_ABOVE_HULL_NAME}</Button>
                    <Button size="small" startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                        ...item,
                        properties: [...(item.properties || []), { name: '', name_raw: '', value_raw: '', unit: '' }],
                      } : item),
                    }))}>{t('upload.addProperty')}</Button>
                  </Box>
                </Box>
                <IssueText field={`material_states[${index}].properties`} />
                {(state.properties || []).map((property, propertyIndex) => (
                  <Box key={propertyIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 2fr 1fr auto' }, gap: 1, mt: 1 }}>
                    <TextField size="small" label={t('upload.propertyNameLabel', { index: propertyIndex + 1 })} value={property.name_raw || property.name || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'name_raw', event.target.value)} />
                    <TextField size="small" label={t('upload.rawValueField')} value={property.value_raw || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'value_raw', event.target.value)} />
                    <TextField size="small" label={t('upload.unitField')} value={property.unit || ''}
                      onChange={event => updateProperty(index, propertyIndex, 'unit', event.target.value)} />
                    <Button size="small" color="error" onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                        ...item, properties: (item.properties || []).filter((_, propIndex) => propIndex !== propertyIndex),
                      } : item),
                    }))}>{t('common.delete')}</Button>
                  </Box>
                ))}

                <StructureCandidatePanel
                  candidates={stateCandidates}
                  uploading={Boolean(structureUploading[index])}
                  onUpload={file => void uploadStructureForState(index, file)}
                  onChange={(candidateId, changes) => changeDraft(current => ({
                    ...current,
                    structure_candidates: (current.structure_candidates || []).map(candidate =>
                      candidate.candidate_id === candidateId ? { ...candidate, ...changes } : candidate,
                    ),
                  }))}
                />
                </Box>
                </Collapse>
              </CardContent>
            </Card>
          )
        })}
        {draft.material_states.length === 0 && !readOnly && (
          <Alert severity="info">{t('upload.noMaterialStates')}</Alert>
        )}
      </Box>
    </Box>
    </Box>
    </Box>
  )
}

export default UploadTaskEditor
