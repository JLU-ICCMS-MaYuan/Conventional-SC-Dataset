import type {
  ClassificationSelection,
  MaterialDimensionality,
  StructureFamilySelection,
} from './classifications'

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
  article_type?: 'e' | 't' | '' | string
  evidence?: SourceEvidence | SourceEvidence[] | null
}

export interface DraftTcResult {
  result_kind?: 'theoretical' | 'experimental' | string
  tc_method?: string
  tc_method_custom?: string | null
  tc_value_k?: number | null
  tc_min_k?: number | null
  tc_max_k?: number | null
  value_raw?: string
  unit_raw?: string
  is_representative?: boolean
  calculation_context?: DraftCalculationContext | null
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

export interface StructureCandidateValidation {
  structure_format?: 'cif' | 'poscar' | string
  structure_hash?: string
  atom_count?: number
  elements?: string[]
  cell_parameters?: Record<string, number>
  volume?: number
  ase_valid?: boolean
  code?: string
  message?: string
}

export interface StructureCandidate {
  candidate_id: string
  material_state_ref?: string | null
  source_kind?: 'attachment' | 'pdf_reported' | 'pdf_derived' | 'merged' | string
  status?: 'needs_review' | 'valid' | 'confirmed' | 'excluded' | 'blocked' | string
  confirmation?: 'unreviewed' | 'confirmed' | 'excluded' | string
  original_format?: 'cif' | 'poscar' | string | null
  original_text?: string | null
  validation?: StructureCandidateValidation
  derivation?: Record<string, unknown> | null
  representations?: Partial<Record<'primitive' | 'conventional', Partial<Record<'cif' | 'poscar', {
    text?: string
    available?: boolean
    format?: string
    cell_kind?: string
    standardization_method?: string
    validation?: StructureCandidateValidation
  }>>>>
  sources?: Array<Record<string, unknown>>
  conflicts?: Array<Record<string, unknown>>
  user_note?: string | null
}

export const CRYSTAL_SYSTEM_VALUES = [
  'triclinic', 'monoclinic', 'orthorhombic', 'tetragonal', 'trigonal', 'hexagonal', 'cubic', 'unknown',
] as const
export type CrystalSystem = typeof CRYSTAL_SYSTEM_VALUES[number]

export interface DraftMaterialState {
  material?: string
  material_family?: ClassificationSelection | null
  structure_families?: StructureFamilySelection[]
  crystal_system?: CrystalSystem
  element_count?: number | null
  element_count_locked?: boolean
  superconductor_kind?: 'conventional' | 'unconventional' | 'unknown'
  material_dimensionality?: MaterialDimensionality
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
  corresponding_authors?: string[]
  co_first_authors?: string[]
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
  research_motivation?: string
  research_materials?: string[]
  material_relations?: unknown[]
  builds_on?: unknown[]
}

export interface UploadDraft {
  paper: PaperDraftFields
  material_states: DraftMaterialState[]
  structure_candidates?: StructureCandidate[]
  research_motivation?: string
  classification_evidence?: SourceEvidence[]
  classification_migration_warnings?: string[]
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

// label 已弃用为机器键，渲染方应使用 t('upload.step.' + key) 取标签（upload 字典由 upload 域提供）。
export const PROCESSING_STAGES: Array<{ key: ProcessingStage; label: string }> = [
  { key: 'saving_file', label: 'saving_file' },
  { key: 'extracting', label: 'extracting' },
  { key: 'reading', label: 'reading' },
  { key: 'summarizing', label: 'summarizing' },
  { key: 'ready', label: 'ready' },
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
      title: '', doi: '', authors: [], corresponding_authors: [], co_first_authors: [],
      journal: '', volume: '', pages: '', year: null,
      abstract: '', summary: '', paper_type: 'unknown', theoretical_subtype: null,
      keywords_tags: [], methodology: [], key_finding: '', research_motivation: '',
      research_materials: [], material_relations: [], builds_on: [],
    },
    material_states: [],
    structure_candidates: [],
    research_motivation: '',
    classification_evidence: [],
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
  const authors = normalizeTextItems(paper.authors, ['name', 'value'])
  const normalizeRoles = (roles: unknown) => {
    const selected = new Set(normalizeTextItems(roles, ['name', 'value']).map(name => name.toLowerCase()))
    return authors.filter(author => selected.has(author.toLowerCase()))
  }
  return {
    ...empty,
    ...paper,
    authors,
    corresponding_authors: normalizeRoles(paper.corresponding_authors),
    co_first_authors: normalizeRoles(paper.co_first_authors),
    keywords_tags: normalizeTextItems(paper.keywords_tags, ['keyword', 'value', 'name']),
    methodology: normalizeTextItems(paper.methodology, ['method', 'value', 'name']),
    research_materials: normalizeTextItems(paper.research_materials, ['material', 'value', 'name']),
  }
}

export function normalizeUploadDraft(value: unknown): UploadDraft {
  const rawWithLegacy = value && typeof value === 'object'
    ? value as Partial<UploadDraft> & { sc_type?: unknown; sc_type_review_status?: unknown }
    : {}
  const raw = { ...rawWithLegacy }
  delete raw.sc_type
  delete raw.sc_type_review_status
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
    material_states: Array.isArray(raw.material_states) ? raw.material_states.map(state => {
      const normalizedState = { ...state }
      delete (normalizedState as { phase_label?: unknown }).phase_label
      const rawCrystalSystem = String(state.crystal_system || 'unknown')
      return {
        ...normalizedState,
        material_family: state.material_family || null,
        structure_families: Array.isArray(state.structure_families) ? state.structure_families : [],
        crystal_system: (CRYSTAL_SYSTEM_VALUES as readonly string[]).includes(rawCrystalSystem)
          ? rawCrystalSystem as CrystalSystem
          : 'unknown',
        element_count: state.element_count ?? null,
        superconductor_kind: state.superconductor_kind || 'unknown',
        material_dimensionality: state.material_dimensionality || 'unknown',
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
      }
    }) : [],
    structure_candidates: Array.isArray(raw.structure_candidates) ? raw.structure_candidates : [],
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
