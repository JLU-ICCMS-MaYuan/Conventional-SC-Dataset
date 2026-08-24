export type ProcessingStage = 'saving_file' | 'queued' | 'extracting' | 'reading' | 'summarizing' | 'ready'
export type ProcessingStatus = 'processing' | 'succeeded' | 'failed' | 'cancelled'
export type UploadTaskStatus = 'uploading' | 'queued' | 'extracting' | 'reading' | 'summarizing' |
  'ready' | 'submitting' | 'submitted' | 'failed' | 'duplicate' | 'cancelling' | 'cancelled'

export interface UploadTaskFile {
  file_id: string
  role: 'main' | 'supplementary' | 'attachment'
  original_filename: string
  size?: number
  upload_status?: string
  extraction_status?: string
  error?: string | null
}

export interface SourceEvidence {
  section?: string | null
  page?: number | null
  quote?: string | null
}

export interface DraftKeyProperty {
  material?: string
  name?: string
  name_raw?: string
  value?: number | string | null
  value_min?: number | null
  value_max?: number | null
  value_raw?: string
  unit?: string
  pressure_gpa?: number | null
  temperature_k?: number | null
  condition?: Record<string, unknown> | string | null
  condition_note?: string
  is_primary?: boolean
  superconductor_type?: string
  article_type?: 'e' | 't' | '' | string
  evidence?: SourceEvidence | SourceEvidence[] | null
}

export interface DraftTcResult {
  result_kind?: 'theoretical' | 'experimental' | string
  tc_method?: string
  tc_value_k?: number | null
  tc_min_k?: number | null
  tc_max_k?: number | null
  value_raw?: string
  unit_raw?: string
  is_representative?: boolean
  evidence?: SourceEvidence | SourceEvidence[] | null
}

export interface DraftCalculationContext {
  phonon_nuclear_treatment?: string
  lambda_ep?: number | null
  omega_log_k?: number | null
  mu_star?: number | null
  evidence?: SourceEvidence | SourceEvidence[] | null
}

export interface DraftExperimentalContext {
  tc_criterion?: string
}

export interface DraftMaterialState {
  material?: string
  phase_label?: string | null
  pressure_value_gpa?: number | null
  pressure_min_gpa?: number | null
  pressure_max_gpa?: number | null
  pressure_raw?: string | null
  pressure_unit_raw?: string | null
  state_kind?: 'theoretical' | 'experimental' | 'mixed' | 'unknown' | string
  reported_space_group_symbol?: string | null
  reported_space_group_number?: number | null
  structure?: Record<string, unknown> | null
  calculation_context?: DraftCalculationContext | null
  experimental_context?: DraftExperimentalContext | null
  tc_results?: DraftTcResult[]
  properties?: DraftKeyProperty[]
  space_group_evidence?: SourceEvidence | SourceEvidence[] | null
}

export interface PaperDraftFields {
  title?: string
  doi?: string
  authors?: string[]
  journal?: string
  volume?: string
  pages?: string
  year?: number | null
  abstract?: string
  summary?: string
  paper_type?: 'theoretical' | 'experimental' | 'review' | 'unknown' | string
  theoretical_subtype?: 'calculation' | 'method' | 'theory' | null | string
  keywords_tags?: string[]
  methodology?: string[]
  key_finding?: string
  rationale?: string
  research_materials?: string[]
  material_relations?: unknown[]
  builds_on?: unknown[]
}

export interface UploadDraft {
  paper: PaperDraftFields
  material_states: DraftMaterialState[]
  classification_reason?: string
  classification_evidence?: SourceEvidence[]
  sc_type?: string
  sc_type_review_status?: 'none' | 'pending' | 'accepted' | 'modified' | 'rejected' | string
  field_evidence?: Record<string, SourceEvidence[]>
  ai_original?: Partial<UploadDraft> | null
}

export interface UploadTaskState {
  task_id: string
  filename?: string
  stage: ProcessingStage
  stage_index: number
  stage_total: number
  processing_status: ProcessingStatus
  processing_error?: string | null
  error_code?: string | null
  completed_chunks: number
  total_chunks: number
  existing_paper_id?: number | null
  existing_paper_status?: string | null
  allowed_actions?: string[]
  duplicate_reason?: string | null
  duplicate?: boolean
  paper_id?: number | null
  status?: UploadTaskStatus
  cleanup_at?: number | null
  updated_at?: number
  files?: UploadTaskFile[]
  revision?: number
}

export interface UploadAcceptedResponse extends Partial<UploadTaskState> {
  ok: boolean
  task_id: string
}

export const PROCESSING_STAGES: Array<{ key: ProcessingStage; label: string }> = [
  { key: 'saving_file', label: '保存原始文件' },
  { key: 'extracting', label: '提取论文正文' },
  { key: 'reading', label: 'AI 分段阅读' },
  { key: 'summarizing', label: 'AI 汇总草稿' },
  { key: 'ready', label: '等待用户校对' },
]

export function unwrapData<T>(response: T | { data: T }): T {
  if (response && typeof response === 'object' && 'data' in response) {
    return (response as { data: T }).data
  }
  return response as T
}

export function emptyUploadDraft(): UploadDraft {
  return {
    paper: {
      title: '', doi: '', authors: [], journal: '', volume: '', pages: '', year: null,
      abstract: '', summary: '', paper_type: 'unknown', theoretical_subtype: null,
      keywords_tags: [], methodology: [], key_finding: '', rationale: '',
      research_materials: [], material_relations: [], builds_on: [],
    },
    material_states: [],
    classification_reason: '',
    classification_evidence: [],
    sc_type: '',
    sc_type_review_status: 'none',
    field_evidence: {},
    ai_original: null,
  }
}

function normalizeTextItems(value: unknown, keys: string[]): string[] {
  const items = Array.isArray(value) ? value : value == null ? [] : [value]
  return items.map(item => {
    if (!item || typeof item !== 'object') return String(item || '').trim()
    const record = item as Record<string, unknown>
    const matched = keys.map(key => record[key]).find(candidate => candidate != null && candidate !== '')
    return String(matched || '').trim()
  }).filter((item, index, all) => Boolean(item) && all.indexOf(item) === index)
}

function embeddedEvidence(value: unknown): SourceEvidence[] {
  if (!Array.isArray(value)) return []
  return value.flatMap(item => {
    if (!item || typeof item !== 'object') return []
    const evidence = (item as Record<string, unknown>).evidence
    return evidence && typeof evidence === 'object' ? [evidence as SourceEvidence] : []
  })
}

function normalizePaperFields(value: unknown): PaperDraftFields {
  const empty = emptyUploadDraft().paper
  const paper = value && typeof value === 'object'
    ? { ...(value as PaperDraftFields & { referenced_materials?: unknown }) }
    : {}
  delete paper.referenced_materials
  return {
    ...empty,
    ...paper,
    authors: normalizeTextItems(paper.authors, ['name', 'value']),
    keywords_tags: normalizeTextItems(paper.keywords_tags, ['keyword', 'value', 'name']),
    methodology: normalizeTextItems(paper.methodology, ['method', 'value', 'name']),
    research_materials: normalizeTextItems(paper.research_materials, ['material', 'value', 'name']),
  }
}

export function normalizeUploadDraft(value: unknown): UploadDraft {
  const raw = value && typeof value === 'object' ? value as Partial<UploadDraft> : {}
  const empty = emptyUploadDraft()
  const rawPaper = raw.paper && typeof raw.paper === 'object' ? raw.paper : {}
  const aiRaw = raw.ai_original && typeof raw.ai_original === 'object' ? raw.ai_original : null
  const existingEvidence = raw.field_evidence && typeof raw.field_evidence === 'object'
    ? raw.field_evidence
    : {}
  const fieldEvidence = { ...existingEvidence }
  delete fieldEvidence.referenced_materials
  for (const field of ['keywords_tags', 'methodology', 'research_materials']) {
    if (!fieldEvidence[field]) {
      const evidence = embeddedEvidence(rawPaper[field as keyof PaperDraftFields])
      if (evidence.length) fieldEvidence[field] = evidence
    }
  }
  return {
    ...empty,
    ...raw,
    paper: normalizePaperFields(rawPaper),
    material_states: Array.isArray(raw.material_states) ? raw.material_states.map(state => ({
      ...state,
      tc_results: Array.isArray(state.tc_results) ? state.tc_results : [],
      properties: Array.isArray(state.properties) ? state.properties.map(item => ({
        ...item,
        value_raw: item.value_raw ?? (item.value == null ? '' : String(item.value)),
      })) : [],
      calculation_context: state.calculation_context ? {
        phonon_nuclear_treatment: 'unknown',
        lambda_ep: null,
        omega_log_k: null,
        mu_star: null,
        ...state.calculation_context,
      } : null,
    })) : [],
    classification_evidence: Array.isArray(raw.classification_evidence)
      ? raw.classification_evidence
      : [],
    field_evidence: fieldEvidence,
    ai_original: aiRaw ? {
      ...aiRaw,
      paper: normalizePaperFields(aiRaw.paper),
      material_states: Array.isArray(aiRaw.material_states) ? aiRaw.material_states : [],
    } : null,
  }
}

export function evidenceList(value: SourceEvidence | SourceEvidence[] | null | undefined): SourceEvidence[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}
