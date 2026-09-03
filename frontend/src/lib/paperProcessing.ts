import type {
  FamilySelection,
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

export type CitationExtractionStatus = 'succeeded' | 'partial' | 'failed' | 'unavailable'

export interface CitationReference {
  reference_index: number
  raw_citation: string
  doi?: string | null
  title?: string | null
  authors?: string[] | null
  year?: number | null
}

export interface CitationExtraction {
  status: CitationExtractionStatus
  parser_name: string
  parser_version?: string | null
  error_message?: string | null
  references: CitationReference[]
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
  structure_families?: StructureFamilySelection[]
  crystal_system?: CrystalSystem
  element_count?: number | null
  element_count_locked?: boolean
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
  material_families?: FamilySelection[]
  superconductor_kind?: 'conventional' | 'unconventional' | 'unknown'
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
  citation_extraction?: CitationExtraction | null
  structure_candidates?: StructureCandidate[]
  research_motivation?: string
  classification_evidence?: SourceEvidence[]
  classification_migration_warnings?: string[]
  field_evidence?: Record<string, SourceEvidence[]>
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
      material_families: [], superconductor_kind: 'unknown',
      keywords_tags: [], methodology: [], key_finding: '', research_motivation: '',
      research_materials: [], material_relations: [], builds_on: [],
    },
    material_states: [],
    structure_candidates: [],
    research_motivation: '',
    classification_evidence: [],
    field_evidence: {},
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

function normalizeCitationExtraction(value: unknown): CitationExtraction | null {
  if (!value || typeof value !== 'object') return null
  const raw = value as Record<string, unknown>
  const statuses: CitationExtractionStatus[] = ['succeeded', 'partial', 'failed', 'unavailable']
  const status = statuses.includes(raw.status as CitationExtractionStatus)
    ? raw.status as CitationExtractionStatus
    : null
  if (!status) return null
  const references = Array.isArray(raw.references)
    ? raw.references.flatMap((item, index) => {
      if (!item || typeof item !== 'object') return []
      const reference = item as Record<string, unknown>
      const rawCitation = String(reference.raw_citation || '').trim()
      if (!rawCitation) return []
      const authors = Array.isArray(reference.authors)
        ? reference.authors.map(author => String(author).trim()).filter(Boolean)
        : null
      return [{
        reference_index: Number.isSafeInteger(reference.reference_index)
          ? Number(reference.reference_index)
          : index,
        raw_citation: rawCitation,
        doi: reference.doi ? String(reference.doi) : null,
        title: reference.title ? String(reference.title) : null,
        authors,
        year: Number.isInteger(reference.year) ? Number(reference.year) : null,
      }]
    })
    : []
  return {
    status,
    parser_name: String(raw.parser_name || 'grobid'),
    parser_version: raw.parser_version ? String(raw.parser_version) : null,
    error_message: raw.error_message ? String(raw.error_message) : null,
    references,
  }
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
  const materialFamilies = (Array.isArray(paper.material_families) ? paper.material_families : [])
    .filter((item): item is FamilySelection => Boolean(item && typeof item === 'object' && item.name?.trim()))
    .filter((item, index, all) => all.findIndex(candidate => (
      item.id != null && candidate.id != null
        ? item.id === candidate.id
        : item.name.trim().toLocaleLowerCase() === candidate.name.trim().toLocaleLowerCase()
    )) === index)
  return {
    ...empty,
    ...paper,
    authors,
    corresponding_authors: normalizeRoles(paper.corresponding_authors),
    co_first_authors: normalizeRoles(paper.co_first_authors),
    material_families: materialFamilies,
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
    citation_extraction: normalizeCitationExtraction(raw.citation_extraction),
    paper: normalizePaperFields({
      ...rawPaper,
      material_families: [
        ...(Array.isArray(rawPaper.material_families) ? rawPaper.material_families : []),
        ...(Array.isArray(raw.material_states)
          ? raw.material_states.map(state => (state as DraftMaterialState & { material_family?: unknown }).material_family).filter(Boolean)
          : []),
      ],
      superconductor_kind: normalizePaperSuperconductorKind(rawPaper, raw.material_states),
    }),
    material_states: Array.isArray(raw.material_states) ? raw.material_states.map(state => {
      const normalizedState = { ...state }
      delete (normalizedState as { phase_label?: unknown }).phase_label
      delete (normalizedState as { material_family?: unknown }).material_family
      delete (normalizedState as { superconductor_kind?: unknown }).superconductor_kind
      const rawCrystalSystem = String(state.crystal_system || 'unknown')
      return {
        ...normalizedState,
        structure_families: Array.isArray(state.structure_families) ? state.structure_families : [],
        crystal_system: (CRYSTAL_SYSTEM_VALUES as readonly string[]).includes(rawCrystalSystem)
          ? rawCrystalSystem as CrystalSystem
          : 'unknown',
        element_count: state.element_count ?? null,
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
  }
}

function normalizePaperSuperconductorKind(rawPaper: Record<string, any>, rawStates: unknown): 'conventional' | 'unconventional' | 'unknown' {
  const paperKind = rawPaper.superconductor_kind
  if (paperKind === 'conventional' || paperKind === 'unconventional' || paperKind === 'unknown') {
    return paperKind
  }
  if (!Array.isArray(rawStates)) return 'unknown'

  const legacyKinds = new Set(rawStates
    .map(state => (state as DraftMaterialState & { superconductor_kind?: unknown }).superconductor_kind)
    .filter(kind => kind === 'conventional' || kind === 'unconventional'))
  return legacyKinds.size === 1 ? [...legacyKinds][0] as 'conventional' | 'unconventional' : 'unknown'
}

export function evidenceList(value: SourceEvidence | SourceEvidence[] | null | undefined): SourceEvidence[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}
