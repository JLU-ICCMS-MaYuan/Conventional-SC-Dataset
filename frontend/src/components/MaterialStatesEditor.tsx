import React, { useCallback, useEffect, useId, useLayoutEffect, useRef, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Card, CardContent, Chip, Collapse, FormControl,
  FormHelperText, InputLabel, MenuItem, Select, TextField, Typography, useMediaQuery,
} from '@mui/material'
import AddIcon from '@mui/icons-material/Add'
import DeleteIcon from '@mui/icons-material/Delete'
import ExpandMoreIcon from '@mui/icons-material/ExpandMore'
import { api } from '../lib/api'
import {
  ClassificationCatalogs,
  ClassificationTerm,
  DEFAULT_MATERIAL_DIMENSIONALITIES,
  familyName,
  pendingSelection,
  selectionForTerm,
} from '../lib/classifications'
import { useLanguage } from '../context/LanguageContext'
import StructureCandidatePanel from './StructureCandidatePanel'
import {
  CRYSTAL_SYSTEM_VALUES, CrystalSystem, DraftKeyProperty, DraftMaterialState, DraftTcResult, SourceEvidence,
  StructureCandidate, evidenceList, unwrapData,
} from '../lib/paperProcessing'

// 一条校验问题。stateIndex 为空表示论文级问题；field 用于在 DOM 中定位出错输入框
export interface ValidationIssue {
  stateIndex?: number
  field: string
  message: string
}

export interface SpaceGroupOption {
  number: number
  symbol: string
}

const TC_METHOD_VALUES = [
  'unknown', 'experimental', 'mcmillan', 'allen_dynes',
  'isotropic_eliashberg', 'anisotropic_eliashberg', 'scdft', 'other',
] as const

const ENERGY_ABOVE_HULL_NAME = 'energy above hull'

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

const COLLAPSED_EVIDENCE_HEIGHT = 120
// AI 建议折叠后仅保留单行（MUI caption 行高约 20px），完整文本仍保留在草稿数据中
const COLLAPSED_AI_LINE_HEIGHT = 20

// 证据注释：展示 AI 建议与文献出处，溢出时按字段宽度收起并可独立展开
export const EvidenceNotes: React.FC<{
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

interface MaterialStatesEditorProps {
  /** 全部材料状态（受控值） */
  states: DraftMaterialState[]
  /** 材料状态数组整体变更回调：任何编辑都传出完整的新状态数组（T017） */
  onChange: (nextStates: DraftMaterialState[]) => void
  /** 分类目录（材料家族/结构家族/维度），加载中可为 null */
  catalogs: ClassificationCatalogs | null
  /** 只读模式：仍渲染全部内容但不可编辑、不可折叠交互，卡片恒展开 */
  readOnly?: boolean
  /** 校验问题：驱动字段错误态与 data-issue-field 定位锚点 */
  issues?: ValidationIssue[]
  /** draft 顶层的结构候选（不在 states 内，单独进出） */
  structureCandidates?: StructureCandidate[]
  onStructureCandidatesChange?: (next: StructureCandidate[]) => void
  /** 空间群标准表（由父组件加载） */
  spaceGroups?: SpaceGroupOption[]
  /** AI 原始建议中的材料状态，供证据注释展示 */
  aiMaterialStates?: DraftMaterialState[]
  catalogLoading?: boolean
  catalogError?: string
  /** 结构上传所在的上传任务 */
  taskId?: string
  /** 论文类型：决定新增材料状态的默认计算/实验上下文 */
  paperType?: string
  /** 论文级超导类型：统一控制所有材料状态的 Tc 编辑字段 */
  superconductorKind?: 'conventional' | 'unconventional' | 'unknown'
  /**
   * 结构上传回调（论文宿主，管理端编辑弹窗用，T034）。
   * 提供时结构上传改由父组件完成（论文结构端点，候选不落库）；
   * 不提供时回退到上传任务端点（`/api/rag/upload-tasks/{taskId}/structure-candidates`，
   * 校对页既有用法，契约不变）。
   */
  onUploadStructure?: (stateIndex: number, file: File) => Promise<void>
  /** 结构上传结果的横幅消息回调（'' 表示清除横幅） */
  onError?: (message: string) => void
}

/**
 * 材料状态编辑区（受控组件）：上传校对页与管理端编辑弹窗共用。
 * 所有编辑逻辑（化学式、分类、元素种类数、维度、晶系与空间群联动、
 * 压强、Tc 列表、普通物性、结构候选面板）内聚于此，统一通过 onChange 传出完整状态数组。
 */
const MaterialStatesEditor: React.FC<MaterialStatesEditorProps> = ({
  states,
  onChange,
  catalogs,
  readOnly = false,
  issues,
  structureCandidates,
  onStructureCandidatesChange,
  spaceGroups = [],
  aiMaterialStates,
  catalogLoading = false,
  catalogError = '',
  taskId,
  paperType,
  superconductorKind = 'unknown',
  onUploadStructure,
  onError,
}) => {
  const { t, lang, dict } = useLanguage()
  // 折叠状态与元素种类数编辑仅存在于浏览器会话内，不写入草稿、不参与自动保存
  const [collapsedStates, setCollapsedStates] = useState<Record<number, boolean>>({})
  const [elementCountEdits, setElementCountEdits] = useState<Record<number, { text: string; invalid: boolean }>>({})
  const [structureUploading, setStructureUploading] = useState<Record<number, boolean>>({})
  // 未分配候选的目标材料状态下标（纯 UI 态，不写入草稿）
  const [unassignedTarget, setUnassignedTarget] = useState<number | null>(null)

  // 只读模式下任何编辑都不应触达父级：变更函数统一在此拦截
  const emitStates = (nextStates: DraftMaterialState[]) => {
    if (!readOnly) onChange(nextStates)
  }

  const updateMaterialState = (index: number, field: keyof DraftMaterialState, value: unknown) => {
    emitStates(states.map((item, itemIndex) =>
      itemIndex === index ? { ...item, [field]: value } : item))
  }

  // 群号合法（1–230）时按标准表反查符号并按范围表改写晶系（群号权威）；非法输入只保存原值不联动
  const changeSpaceGroupNumber = (index: number, raw: string) => {
    const trimmed = raw.trim()
    const parsed = trimmed === '' ? null : Number(trimmed)
    emitStates(states.map((item, itemIndex) => {
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
    }))
  }

  const uploadStructureForState = async (stateIndex: number, file: File) => {
    if (readOnly) return
    setStructureUploading(current => ({ ...current, [stateIndex]: true }))
    try {
      if (onUploadStructure) {
        // 论文宿主（管理端编辑弹窗，T034）：父组件调用论文结构端点并
        // 把候选并入本地 structureCandidates 状态（不落库，保存时随 C1 提交）。
        await onUploadStructure(stateIndex, file)
      } else {
        // 上传任务宿主（校对页）：沿用上传任务结构端点，候选写入草稿。
        const body = new FormData()
        body.append('material_state_index', String(stateIndex))
        body.append('file', file)
        const response = await api.post<{ ok: boolean; data: StructureCandidate }>(
          `/api/rag/upload-tasks/${taskId}/structure-candidates`, body,
        )
        const candidate = unwrapData(response)
        onStructureCandidatesChange?.([
          ...(structureCandidates || []).filter(item => item.candidate_id !== candidate.candidate_id),
          candidate,
        ])
      }
      onError?.('')
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : t('upload.structureUploadFailed')
      onError?.(message)
    } finally {
      setStructureUploading(current => ({ ...current, [stateIndex]: false }))
    }
  }

  const setAllCollapsed = (value: boolean) => {
    if (readOnly) return
    setCollapsedStates(value
      ? Object.fromEntries(states.map((_, index) => [index, true]))
      : {})
  }

  // 元素种类数：仅接受 1–118 的整数，非法输入即时提示且不写入草稿；手动编辑后锁定，清空则恢复服务端自动计算
  const changeElementCount = (index: number, raw: string) => {
    if (readOnly) return
    const trimmed = raw.trim()
    if (trimmed === '') {
      setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: false } }))
      emitStates(states.map((item, itemIndex) =>
        itemIndex === index ? { ...item, element_count: null, element_count_locked: false } : item))
      return
    }
    const parsed = Number(trimmed)
    if (!/^\d+$/.test(trimmed) || parsed < 1 || parsed > 118) {
      setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: true } }))
      return
    }
    setElementCountEdits(current => ({ ...current, [index]: { text: raw, invalid: false } }))
    emitStates(states.map((item, itemIndex) =>
      itemIndex === index ? { ...item, element_count: parsed, element_count_locked: true } : item))
  }

  const updateTcCalculationContext = (
    stateIndex: number,
    resultIndex: number,
    field: 'lambda_ep' | 'omega_log_k' | 'mu_star',
    value: number | null,
  ) => {
    emitStates(states.map((state, index) => index === stateIndex ? {
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
    } : state))
  }

  // 常规 (BCS) 论文的 Tc 条目带独立计算上下文；首个条目用状态级旧值一次性预填 λ/ωlog
  const addTcResult = (index: number) => {
    emitStates(states.map((item, itemIndex) => {
      if (itemIndex !== index) return item
      const isConventional = superconductorKind === 'conventional'
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
    }))
  }

  const removeTcResult = (stateIndex: number, resultIndex: number) => {
    emitStates(states.map((item, itemIndex) => itemIndex === stateIndex ? {
      ...item, tc_results: (item.tc_results || []).filter((_, tcIndex) => tcIndex !== resultIndex),
    } : item))
  }

  const updateTcResult = (stateIndex: number, resultIndex: number, field: keyof DraftTcResult, value: unknown) => {
    emitStates(states.map((state, index) => index === stateIndex ? {
      ...state,
      tc_results: (state.tc_results || []).map((item, itemIndex) =>
        itemIndex === resultIndex ? { ...item, [field]: value } : item),
    } : state))
  }

  const updateProperty = (stateIndex: number, propertyIndex: number, field: keyof DraftKeyProperty, value: unknown) => {
    emitStates(states.map((state, index) => index === stateIndex ? {
      ...state,
      properties: (state.properties || []).map((item, itemIndex) =>
        itemIndex === propertyIndex ? { ...item, [field]: value } : item),
    } : state))
  }

  const addEnergyAboveHull = (index: number) => {
    emitStates(states.map((item, itemIndex) => itemIndex === index ? {
      ...item,
      properties: [...(item.properties || []), {
        name: ENERGY_ABOVE_HULL_NAME, name_raw: ENERGY_ABOVE_HULL_NAME, value_raw: '', unit: 'eV/atom',
      }],
    } : item))
  }

  const addProperty = (index: number) => {
    emitStates(states.map((item, itemIndex) => itemIndex === index ? {
      ...item,
      properties: [...(item.properties || []), { name: '', name_raw: '', value_raw: '', unit: '' }],
    } : item))
  }

  const removeProperty = (stateIndex: number, propertyIndex: number) => {
    emitStates(states.map((item, itemIndex) => itemIndex === stateIndex ? {
      ...item, properties: (item.properties || []).filter((_, propIndex) => propIndex !== propertyIndex),
    } : item))
  }

  const deleteState = (index: number) => {
    emitStates(states.filter((_, itemIndex) => itemIndex !== index))
  }

  // 新增材料状态：默认上下文取决于论文类型（与上传页原实现一致）
  const addState = () => {
    emitStates([...states, {
      material: '',
      structure_families: [],
      element_count: null,
      element_count_locked: false,
      material_dimensionality: 'unknown',
      pressure_value_gpa: null,
      state_kind: paperType === 'experimental' ? 'experimental' : 'theoretical',
      crystal_system: 'unknown',
      reported_space_group_symbol: null,
      reported_space_group_number: null,
      calculation_context: paperType === 'experimental' ? null : {
        phonon_nuclear_treatment: 'unknown', lambda_ep: null, omega_log_k: null, mu_star: null,
      },
      experimental_context: paperType === 'experimental' ? { tc_criterion: 'unknown' } : null,
      tc_results: [],
      properties: [],
    }])
  }

  const updateStructureCandidate = (candidateId: string, changes: Partial<StructureCandidate>) => {
    if (readOnly) return
    onStructureCandidatesChange?.((structureCandidates || []).map(candidate =>
      candidate.candidate_id === candidateId ? { ...candidate, ...changes } : candidate,
    ))
  }

  // 未分配候选：随任务解析生成、尚未分配到具体材料状态（material_state_ref 以 unassigned: 开头）。
  // 排除的候选不再显示（R4）。
  const unassignedCandidates = (structureCandidates || []).filter(candidate =>
    String(candidate.material_state_ref || '').startsWith('unassigned:')
    && candidate.confirmation !== 'excluded'
  )

  // 分配并确认：把候选的 material_state_ref 改为 material_states[N] 并标记 confirmed，
  // 使提交链路 _confirmed_candidates_by_state 能把它写入 structure_models（R1、FR-002）。
  const assignUnassignedCandidate = (candidate: StructureCandidate) => {
    if (readOnly || unassignedTarget == null) return
    onStructureCandidatesChange?.((structureCandidates || []).map(item =>
      item.candidate_id === candidate.candidate_id
        ? {
            ...item,
            material_state_ref: `material_states[${unassignedTarget}]`,
            confirmation: 'confirmed',
            status: 'confirmed',
          }
        : item,
    ))
    setUnassignedTarget(null)
  }

  // 材料状态数组变化时调和折叠状态：保留已有卡片的手动选择，新卡片按默认规则初始化
  const materialStateCount = states.length
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

  // 校验问题出现时展开对应卡片（与上传页 revealIssues 的「展开首张出错卡片」行为一致）
  useEffect(() => {
    const first = issues?.[0]
    if (!first || first.stateIndex == null) return
    const index = first.stateIndex
    setCollapsedStates(current => (current[index] ? { ...current, [index]: false } : current))
  }, [issues])

  // 统一给出错字段加定位锚点、错误态与说明文字，避免每处重复拼装
  const issueOf = (field: string) => issues?.find(item => item.field === field)
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

  return (
    <Box sx={readOnly ? { pointerEvents: 'none', '& .MuiButton-root': { display: 'none' } } : undefined}>
      <Box sx={{ mt: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, mb: 2, flexWrap: 'wrap' }}>
          <Typography variant="h6" fontWeight={700}>{t('upload.materialStatesTitle')}</Typography>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            {states.length > 0 && (
              <>
                <Button size="small" onClick={() => setAllCollapsed(true)}>{t('common.collapseAll')}</Button>
                <Button size="small" onClick={() => setAllCollapsed(false)}>{t('common.expandAll')}</Button>
              </>
            )}
            <Button startIcon={<AddIcon />} onClick={addState}>{t('upload.addMaterialState')}</Button>
          </Box>
        </Box>

        <Box data-testid="material-states-list" sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 1.5, mt: 1.5 }}>
          {states.map((state, index) => {
            const aiState = aiMaterialStates?.[index]
            const stateCandidates = (structureCandidates || []).filter(candidate => candidate.material_state_ref === `material_states[${index}]`)
            const isCollapsed = !readOnly && Boolean(collapsedStates[index])
            const isConventional = superconductorKind === 'conventional'
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
                    onClick={() => { if (!readOnly) setCollapsedStates(current => ({ ...current, [index]: !current[index] })) }}
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
                    </Box>
                    <Button size="small" color="error" startIcon={<DeleteIcon />}
                      onClick={event => {
                        event.stopPropagation()
                        deleteState(index)
                      }}>{t('common.delete')}</Button>
                  </Box>
                  <Collapse in={!isCollapsed} timeout="auto" id={`material-state-${index}-content`}>
                  <Box>
                  <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', sm: '1fr 1fr', md: 'repeat(3, 1fr)' }, gap: 1.5 }}>
                    <TextField label={t('upload.materialField')} value={state.material || ''}
                      {...issueProps(`material_states[${index}].material`)}
                      onChange={event => updateMaterialState(index, 'material', event.target.value)} />
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
                          emitStates(states.map((item, itemIndex) => itemIndex === index ? {
                            ...item,
                            reported_space_group_symbol: value.symbol,
                            reported_space_group_number: value.number,
                            crystal_system: crystalSystemForNumber(value.number),
                          } : item))
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
                      <Button size="small" startIcon={<AddIcon />} onClick={() => addProperty(index)}>{t('upload.addProperty')}</Button>
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
                      <Button size="small" color="error" onClick={() => removeProperty(index, propertyIndex)}>{t('common.delete')}</Button>
                    </Box>
                  ))}

                  <StructureCandidatePanel
                    candidates={stateCandidates}
                    uploading={Boolean(structureUploading[index])}
                    onUpload={file => void uploadStructureForState(index, file)}
                    onChange={updateStructureCandidate}
                  />
                  </Box>
                  </Collapse>
                </CardContent>
              </Card>
            )
          })}
          {states.length === 0 && !readOnly && (
            <Alert severity="info">{t('upload.noMaterialStates')}</Alert>
          )}

          {!readOnly && unassignedCandidates.length > 0 && (
            <Box data-testid="unassigned-candidates" sx={{ mt: 2 }}>
              <Typography variant="subtitle2" fontWeight={700} sx={{ mb: 1 }}>
                {t('upload.unassignedCandidatesTitle')}
              </Typography>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                {unassignedCandidates.map(candidate => {
                  const blocked = candidate.status === 'blocked'
                  const sourceName = candidate.sources?.find?.(item => item && typeof item === 'object' && 'filename' in item)
                    ?.filename as string | undefined
                  return (
                    <Card key={candidate.candidate_id} variant="outlined" sx={{ p: 1.5 }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                        <Typography variant="body2" fontWeight={600} sx={{ minWidth: 0, flex: '1 1 180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {sourceName || candidate.candidate_id}
                        </Typography>
                        <Chip
                          size="small"
                          label={blocked ? t('upload.structureStatusBlocked') : t('upload.structureStatusValid')}
                          color={blocked ? 'warning' : 'default'}
                        />
                        {blocked && candidate.validation?.message && (
                          <Typography variant="caption" color="warning.main" sx={{ flexBasis: '100%' }}>
                            {t('upload.unassignedValidationFailed', { message: candidate.validation.message })}
                          </Typography>
                        )}
                      </Box>
                      {!blocked && (
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1, flexWrap: 'wrap' }}>
                          <FormControl size="small" sx={{ minWidth: 220, flex: '1 1 220px' }}>
                            <InputLabel id={`unassigned-target-${candidate.candidate_id}-label`}>
                              {t('upload.unassignedTargetLabel')}
                            </InputLabel>
                            <Select
                              labelId={`unassigned-target-${candidate.candidate_id}-label`}
                              label={t('upload.unassignedTargetLabel')}
                              value={unassignedTarget ?? ''}
                              disabled={states.length === 0}
                              onChange={event => setUnassignedTarget(Number(event.target.value))}
                            >
                              {states.map((state, index) => (
                                <MenuItem key={index} value={index}>
                                  {t('upload.materialStateNumber', { index: index + 1 })}
                                  {state.material?.trim() ? ` · ${state.material}` : ''}
                                </MenuItem>
                              ))}
                            </Select>
                            {states.length === 0 && (
                              <FormHelperText>{t('upload.unassignedNeedState')}</FormHelperText>
                            )}
                          </FormControl>
                          <Button
                            size="small"
                            variant="contained"
                            color="success"
                            disabled={states.length === 0 || unassignedTarget == null}
                            onClick={() => assignUnassignedCandidate(candidate)}
                          >
                            {t('upload.adoptStructure')}
                          </Button>
                          <Button
                            size="small"
                            color="inherit"
                            disabled={candidate.confirmation === 'excluded'}
                            onClick={() => updateStructureCandidate(candidate.candidate_id, { confirmation: 'excluded', status: 'excluded' })}
                          >
                            {t('upload.excludeStructure')}
                          </Button>
                        </Box>
                      )}
                    </Card>
                  )
                })}
              </Box>
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  )
}

export default MaterialStatesEditor
