import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Checkbox, Chip, CircularProgress, Collapse,
  FormControl, InputLabel, ListItemText, Menu, MenuItem, Select, TextField, Typography, useMediaQuery,
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
  loadClassificationCatalogs,
  pendingSelection,
  selectionForTerm,
} from '../lib/classifications'
import ClassificationAutocomplete from './ClassificationAutocomplete'
import StructureCandidatePanel from './StructureCandidatePanel'
import {
  CrystalSystem, DraftKeyProperty, DraftMaterialState, DraftTcResult, SourceEvidence, StructureCandidate, UploadDraft,
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

const PAPER_TYPE_OPTIONS = [
  { value: 'theoretical', label: '理论文章' },
  { value: 'experimental', label: '实验文章' },
  { value: 'review', label: '综述文章' },
  { value: 'unknown', label: '暂不确定' },
]

const SUPERCONDUCTOR_KIND_OPTIONS = [
  { value: 'conventional', label: '常规超导体（BCS超导体）' },
  { value: 'unconventional', label: '非常规超导体' },
]

const TC_METHOD_OPTIONS = [
  { value: 'unknown', label: '未知' },
  { value: 'experimental', label: '实验测量' },
  { value: 'mcmillan', label: 'McMillan' },
  { value: 'allen_dynes', label: 'Allen-Dynes-McMillan' },
  { value: 'isotropic_eliashberg', label: 'isotropic Migdal-Eliashberg' },
  { value: 'anisotropic_eliashberg', label: 'anisotropic Migdal-Eliashberg' },
  { value: 'scdft', label: 'SCDFT' },
  { value: 'other', label: '其他' },
]

const ENERGY_ABOVE_HULL_NAME = 'energy above hull'

interface SpaceGroupOption {
  number: number
  symbol: string
}

const CRYSTAL_SYSTEM_OPTIONS: Array<{ value: CrystalSystem; label: string }> = [
  { value: 'triclinic', label: '三斜' },
  { value: 'monoclinic', label: '单斜' },
  { value: 'orthorhombic', label: '正交' },
  { value: 'tetragonal', label: '四方' },
  { value: 'trigonal', label: '三方' },
  { value: 'hexagonal', label: '六方' },
  { value: 'cubic', label: '立方' },
  { value: 'unknown', label: '未知' },
]

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
const displayValue = (value: unknown) => {
  if (value == null || value === '') return '未提供'
  if (Array.isArray(value)) return value.join('、') || '未提供'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value)
}

// 默认折叠规则：卡片数 ≤2 全部展开，否则仅第一张展开
const defaultCollapsedStates = (count: number): Record<number, boolean> => (
  count > 2
    ? Object.fromEntries(Array.from({ length: count }, (_, index) => [index, index !== 0]))
    : {}
)

const COLLAPSED_EVIDENCE_HEIGHT = 120
// AI 建议折叠后仅保留单行（MUI caption 行高约 20px），完整文本仍保留在草稿数据中
const COLLAPSED_AI_LINE_HEIGHT = 20

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

const UploadTaskEditor: React.FC<UploadTaskEditorProps> = ({
  taskId, onSubmitted, draftOverride, readOnly = false, statusNote,
}) => {
  const [draft, setDraft] = useState<UploadDraft | null>(null)
  const [loading, setLoading] = useState(true)
  const [dirty, setDirty] = useState(false)
  const [saving, setSaving] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [lastSavedAt, setLastSavedAt] = useState<string | null>(null)
  const [error, setError] = useState('')
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
        if (active) setCatalogError(reason.message || '分类目录加载失败')
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
      if (reason.name !== 'AbortError') setError(reason.message || '草稿加载失败')
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
      const message = reason instanceof Error ? reason.message : '结构附件上传失败'
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
      setLastSavedAt(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }))
      if (showResult) setError('')
      return true
    } catch (reason) {
      setError((reason as Error).message || '草稿保存失败')
      return false
    } finally {
      setSaving(false)
    }
  }, [dirty, draft, saving, taskId, readOnly])

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
          <Typography variant="h6" fontWeight={700}>{readOnly ? 'AI 草稿（实时生成中）' : '检查 AI 草稿'}</Typography>
          <Typography variant="body2" color="text.secondary">
            {readOnly ? (statusNote || 'AI 正在生成草稿，内容与最终校对表单一致。') : '核对后保存，确认无误再提交管理员审核。'}
          </Typography>
        </Box>
        {readOnly ? (
          <Chip size="small" color="info" label="只读预览" />
        ) : (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          <Typography variant="caption" color={error ? 'error' : 'text.secondary'}>
            {saving ? '保存中…' : dirty ? '有修改，5 秒后自动保存' : lastSavedAt ? `${lastSavedAt} 已保存` : '草稿已加载'}
          </Typography>
          <Button variant="outlined" startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
            disabled={saving || submitting} onClick={() => void saveDraft(true)}>立即保存</Button>
          <Button variant="contained" startIcon={submitting ? <CircularProgress size={16} /> : <SendIcon />}
            disabled={saving || submitting} onClick={() => void submit()}>提交审核</Button>
        </Box>
        )}
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      <Box sx={readOnly ? { pointerEvents: 'none', '& .MuiButton-root': { display: 'none' } } : undefined}>
      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, '& > *': { minWidth: 0 } }}>
        <Box>
          <TextField fullWidth label="标题" value={draft.paper.title || ''}
            onChange={event => setPaperField('title', event.target.value)} />
          <EvidenceNotes label="标题" aiValue={aiPaper.title} />
        </Box>
        <Box>
          <TextField fullWidth label="DOI" value={draft.paper.doi || ''}
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
                draft.paper.corresponding_authors?.includes(author) ? '通讯作者' : '',
                draft.paper.co_first_authors?.includes(author) ? '共同第一作者' : '',
              ].filter(Boolean)
              return (
                <Chip
                  {...tagProps}
                  key={key}
                  label={[author, ...roles].join(' · ')}
                  title="点击设置作者身份"
                  onClick={event => setAuthorMenu({ author, anchorEl: event.currentTarget })}
                  onDelete={() => setAuthors(values.filter(item => item !== author))}
                />
              )
            })}
            renderInput={params => (
              <TextField {...params} label="作者" placeholder={(draft.paper.authors || []).length ? '' : '输入姓名后按 Enter'} onKeyDown={event => { if ((event.key === 'Enter' || event.key === ',' || event.key === '，') && authorInput.trim()) { event.preventDefault(); commitAuthorInput() } }} />
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
              ['corresponding_authors', '通讯作者'],
              ['co_first_authors', '共同第一作者'],
            ] as const).map(([field, label]) => (
              <MenuItem key={field} onClick={() => toggleAuthorRole(field, authorMenu.author)}>
                <Checkbox checked={(draft.paper[field] || []).includes(authorMenu.author)} />
                <ListItemText primary={label} />
              </MenuItem>
            ))}
          </Menu>
          <EvidenceNotes label="作者" aiValue={aiPaper.authors} />
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
            <EvidenceNotes label="期刊信息" aiValue={[aiPaper.journal, aiPaper.year, aiPaper.volume, aiPaper.pages].filter(Boolean).join(' · ')} />
          </Box>
        </Box>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2, '& > *': { minWidth: 0 } }}>
        <FormControl fullWidth>
          <InputLabel>论文整体类型</InputLabel>
          <Select label="论文整体类型" value={draft.paper.paper_type || 'unknown'}
            onChange={event => setPaperField('paper_type', event.target.value)}>
            {PAPER_TYPE_OPTIONS.map(option => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
          </Select>
          <EvidenceNotes label="论文整体类型" aiValue={aiPaper.paper_type} evidence={classificationEvidence} />
        </FormControl>
        <FormControl fullWidth disabled={draft.paper.paper_type !== 'theoretical'}>
          <InputLabel>理论二级类型</InputLabel>
          <Select label="理论二级类型" value={draft.paper.theoretical_subtype || ''}
            onChange={event => setPaperField('theoretical_subtype', event.target.value || null)}>
            <MenuItem value="calculation">计算类</MenuItem>
            <MenuItem value="method">方法类</MenuItem>
            <MenuItem value="theory">理论模型与机制</MenuItem>
          </Select>
          <EvidenceNotes label="理论二级类型" aiValue={aiPaper.theoretical_subtype} />
        </FormControl>
      </Box>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2, mt: 2, '& > *': { minWidth: 0 } }}>
        {[
          ['keywords_tags', '关键词（每行一个）'],
          ['methodology', '研究方法（每行一项）'],
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
        ['abstract', '论文摘要', 4],
        ['summary', '中文总结', 3],
        ['key_finding', '核心发现', 3],
      ].map(([field, label, rows]) => (
        <Box key={String(field)} sx={{ mt: 2 }}>
          <TextField fullWidth label={String(label)} multiline minRows={Number(rows)}
            value={String(draft.paper[field as keyof UploadDraft['paper']] || '')}
            onChange={event => setPaperField(field as keyof UploadDraft['paper'], event.target.value)} />
          <EvidenceNotes label={String(label)} aiValue={aiPaper[field as keyof typeof aiPaper]} />
        </Box>
      ))}

      <Box sx={{ mt: 2 }}>
        <TextField fullWidth label="分类理由" multiline minRows={3}
          value={draft.classification_reason || ''}
          onChange={event => setDraftField('classification_reason', event.target.value)} />
        <EvidenceNotes label="分类理由" aiValue={ai.classification_reason} evidence={classificationEvidence} />
      </Box>

      <Box sx={{ mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" fontWeight={700}>材料状态与计算条件</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            {draft.material_states.length > 0 && (
              <>
                <Button size="small" onClick={() => setAllCollapsed(true)}>全部折叠</Button>
                <Button size="small" onClick={() => setAllCollapsed(false)}>全部展开</Button>
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
            }))}>添加材料状态</Button>
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
                    <Typography variant="subtitle2" fontWeight={700}>材料状态 #{index + 1}</Typography>
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
                      }}>应用到同材料</Button>
                    )}
                  </Box>
                  <Button size="small" color="error" startIcon={<DeleteIcon />}
                    onClick={event => {
                      event.stopPropagation()
                      changeDraft(current => ({
                        ...current,
                        material_states: current.material_states.filter((_, itemIndex) => itemIndex !== index),
                      }))
                    }}>删除</Button>
                </Box>
                <Collapse in={!isCollapsed} timeout="auto" id={`material-state-${index}-content`}>
                <Box>
                <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1.5 }}>
                  <TextField label="材料" value={state.material || ''}
                    onChange={event => updateMaterialState(index, 'material', event.target.value)} />
                  <ClassificationAutocomplete
                    label="材料家族"
                    options={catalogs?.material_families || []}
                    value={state.material_family}
                    loading={catalogLoading}
                    error={catalogError}
                    onChange={value => updateMaterialState(index, 'material_family', value)}
                  />
                  <TextField
                    label="不同元素种类数"
                    value={elementCountEdits[index]?.text ?? (state.element_count ?? '')}
                    error={Boolean(elementCountEdits[index]?.invalid)}
                    helperText={elementCountEdits[index]?.invalid ? '请输入 1–118 的整数' : '自动计算，可手动修改'}
                    onChange={event => changeElementCount(index, event.target.value)}
                  />
                  <FormControl fullWidth>
                    <InputLabel id={`material-dimensionality-${index}-label`}>材料维度</InputLabel>
                    <Select
                      labelId={`material-dimensionality-${index}-label`}
                      label="材料维度"
                      value={state.material_dimensionality || 'unknown'}
                      onChange={event => updateMaterialState(index, 'material_dimensionality', event.target.value)}
                    >
                      {(catalogs?.material_dimensionalities || DEFAULT_MATERIAL_DIMENSIONALITIES).map(option => (
                        <MenuItem key={option.value} value={option.value}>{option.name}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                  <Autocomplete<ClassificationTerm | string, true, false, true>
                    multiple
                    freeSolo
                    options={catalogs?.structure_families || []}
                    loading={catalogLoading}
                    value={(state.structure_families || []).map(selection => (
                      selection.id == null
                        ? selection.name
                        : catalogs?.structure_families.find(option => option.id === selection.id) || selection.name
                    ))}
                    getOptionLabel={option => typeof option === 'string' ? option : option.name}
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
                    renderInput={params => <TextField {...params} label="更多类型标签（可以填写不止一个类型）" error={Boolean(catalogError)} />}
                  />
                  <TextField label="压强 (GPa)" type="number" value={state.pressure_value_gpa ?? ''} helperText={state.pressure_value_gpa == null && state.pressure_raw ? '原文压力：' + state.pressure_raw + ' ' + (state.pressure_unit_raw || '') : undefined}
                    onChange={event => updateMaterialState(index, 'pressure_value_gpa', event.target.value ? Number(event.target.value) : null)} />
                  <FormControl fullWidth>
                    <InputLabel id={`crystal-system-${index}-label`}>晶系</InputLabel>
                    <Select
                      labelId={`crystal-system-${index}-label`}
                      label="晶系"
                      value={crystalSystem}
                      onChange={event => updateMaterialState(index, 'crystal_system', event.target.value)}
                    >
                      {CRYSTAL_SYSTEM_OPTIONS.map(option => (
                        <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
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
                    renderInput={params => <TextField {...params} label="空间群符号" />}
                  />
                  <TextField label="空间群号" type="number" value={state.reported_space_group_number ?? ''}
                    onChange={event => changeSpaceGroupNumber(index, event.target.value)}
                    slotProps={{ htmlInput: { min: 1, max: 230 } }} />
                  <FormControl fullWidth>
                    <InputLabel id={`superconductor-kind-${index}-label`}>超导类型</InputLabel>
                    <Select
                      labelId={`superconductor-kind-${index}-label`}
                      label="超导类型"
                      value={state.superconductor_kind === 'conventional' || state.superconductor_kind === 'unconventional'
                        ? state.superconductor_kind
                        : ''}
                      displayEmpty
                      renderValue={value => SUPERCONDUCTOR_KIND_OPTIONS.find(option => option.value === value)?.label
                        ?? <Box component="span" sx={{ color: 'text.secondary' }}>请选择</Box>}
                      onChange={event => updateMaterialState(index, 'superconductor_kind', event.target.value)}
                    >
                      {SUPERCONDUCTOR_KIND_OPTIONS.map(option => (
                        <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>
                <EvidenceNotes
                  label={`材料状态 #${index + 1}`}
                  aiValue={aiState ? `${aiState.material || ''} ${aiState.pressure_value_gpa ?? ''} GPa`.trim() : undefined}
                  evidence={state.space_group_evidence || aiState?.space_group_evidence}
                />

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>临界温度 Tc</Typography>
                  <Button size="small" startIcon={<AddIcon />} onClick={() => addTcResult(index)}>添加 Tc</Button>
                </Box>
                {(state.tc_results || []).map((result, resultIndex) => (
                  isConventional ? (
                    <Box key={resultIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1, mt: 1 }}>
                      <TextField size="small" label="电声耦合强度 λ" type="number" value={result.calculation_context?.lambda_ep ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'lambda_ep', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label="对数声子频率 ωlog (K)" type="number" value={result.calculation_context?.omega_log_k ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'omega_log_k', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label="库伦屏蔽常数 μ*" type="number" value={result.calculation_context?.mu_star ?? ''}
                        onChange={event => updateTcCalculationContext(index, resultIndex, 'mu_star', event.target.value ? Number(event.target.value) : null)}
                        slotProps={{ htmlInput: { min: 0, step: 'any' } }} />
                      <TextField size="small" label="Tc 数值 (K)" type="number" value={result.tc_value_k ?? ''}
                        onChange={event => updateTcResult(index, resultIndex, 'tc_value_k', event.target.value ? Number(event.target.value) : null)} />
                      <FormControl size="small">
                        <InputLabel id={`tc-method-${index}-${resultIndex}-label`}>Tc 方法</InputLabel>
                        <Select
                          labelId={`tc-method-${index}-${resultIndex}-label`}
                          label="Tc 方法"
                          value={result.tc_method || 'unknown'}
                          onChange={event => updateTcResult(index, resultIndex, 'tc_method', event.target.value)}
                        >
                          {TC_METHOD_OPTIONS.map(option => <MenuItem key={option.value} value={option.value}>{option.label}</MenuItem>)}
                        </Select>
                      </FormControl>
                      {result.tc_method === 'other' && (
                        <TextField size="small" label="自定义 Tc 方法" value={result.tc_method_custom || ''}
                          onChange={event => updateTcResult(index, resultIndex, 'tc_method_custom', event.target.value || null)} />
                      )}
                      <Button size="small" color="error" onClick={() => removeTcResult(index, resultIndex)}>删除</Button>
                    </Box>
                  ) : (
                    <Box key={resultIndex} sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr auto' }, gap: 1, mt: 1 }}>
                      <TextField size="small" label="Tc 数值 (K)" type="number" value={result.tc_value_k ?? ''}
                        onChange={event => updateTcResult(index, resultIndex, 'tc_value_k', event.target.value ? Number(event.target.value) : null)} />
                      <Button size="small" color="error" onClick={() => removeTcResult(index, resultIndex)}>删除</Button>
                    </Box>
                  )
                ))}

                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Typography variant="subtitle2" fontWeight={700}>其他普通物性</Typography>
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button size="small" startIcon={<AddIcon />} disabled={hasEnergyAboveHull}
                      onClick={() => addEnergyAboveHull(index)}>{ENERGY_ABOVE_HULL_NAME}</Button>
                    <Button size="small" startIcon={<AddIcon />} onClick={() => changeDraft(current => ({
                      ...current,
                      material_states: current.material_states.map((item, itemIndex) => itemIndex === index ? {
                        ...item,
                        properties: [...(item.properties || []), { name: '', name_raw: '', value_raw: '', unit: '' }],
                      } : item),
                    }))}>添加普通物性</Button>
                  </Box>
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
          <Alert severity="info">AI 没有提取到材料状态。综述可以直接提交，其他论文请补充后提交。</Alert>
        )}
      </Box>
    </Box>
    </Box>
    </Box>
  )
}

export default UploadTaskEditor
