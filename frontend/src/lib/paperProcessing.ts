export type ProcessingStage = 'saving_file' | 'extracting' | 'reading' | 'summarizing' | 'ready'
export type ProcessingStatus = 'processing' | 'succeeded' | 'failed'

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
  referenced_materials?: string[]
  material_relations?: unknown[]
  builds_on?: unknown[]
}

export interface UploadDraft {
  paper: PaperDraftFields
  key_properties: DraftKeyProperty[]
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
  duplicate?: boolean
  paper_id?: number | null
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
      research_materials: [], referenced_materials: [], material_relations: [], builds_on: [],
    },
    key_properties: [],
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
  const paper = value && typeof value === 'object' ? value as PaperDraftFields : {}
  return {
    ...empty,
    ...paper,
    authors: normalizeTextItems(paper.authors, ['name', 'value']),
    keywords_tags: normalizeTextItems(paper.keywords_tags, ['keyword', 'value', 'name']),
    methodology: normalizeTextItems(paper.methodology, ['method', 'value', 'name']),
    research_materials: normalizeTextItems(paper.research_materials, ['material', 'value', 'name']),
    referenced_materials: normalizeTextItems(paper.referenced_materials, ['material', 'value', 'name']),
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
  for (const field of ['keywords_tags', 'methodology', 'research_materials', 'referenced_materials']) {
    if (!fieldEvidence[field]) {
      const evidence = embeddedEvidence(rawPaper[field as keyof PaperDraftFields])
      if (evidence.length) fieldEvidence[field] = evidence
    }
  }
  return {
    ...empty,
    ...raw,
    paper: normalizePaperFields(rawPaper),
    key_properties: Array.isArray(raw.key_properties) ? raw.key_properties.map(item => ({
      ...item,
      value_raw: item.value_raw ?? (item.value == null ? '' : String(item.value)),
    })) : [],
    classification_evidence: Array.isArray(raw.classification_evidence)
      ? raw.classification_evidence
      : [],
    field_evidence: fieldEvidence,
    ai_original: aiRaw ? {
      ...aiRaw,
      paper: normalizePaperFields(aiRaw.paper),
      key_properties: Array.isArray(aiRaw.key_properties) ? aiRaw.key_properties.map(item => ({
        ...item,
        value_raw: item.value_raw ?? (item.value == null ? '' : String(item.value)),
      })) : [],
    } : null,
  }
}

export function evidenceList(value: SourceEvidence | SourceEvidence[] | null | undefined): SourceEvidence[] {
  if (!value) return []
  return Array.isArray(value) ? value : [value]
}
