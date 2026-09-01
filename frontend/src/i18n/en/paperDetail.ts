// 英文论文详情与编辑页文案。键集必须与 zh/paperDetail.ts 完全一致——字典类型由
// 中文侧推导，缺键或多键会在 `tsc -b` 阶段报错，不会静默回退。
//
// 六个叙述字段的内容是英文数据，渲染时原样展示，不随界面语言变化（FR-014）。
export default {
  // ── Page frame ──
  backToUpload: 'Back to upload list',
  myPapers: 'My papers',
  readOnlyMode: 'Read-only mode',
  paperDetailTitle: 'Paper Details',
  submittedNotice: 'This paper has been submitted for review. Regular users cannot edit the official record here.',

  // ── Load failure branches (PaperDetailPage) ──
  failure: {
    invalid: 'Invalid paper ID',
    forbidden: 'You do not have permission to view this paper',
    missing: 'Paper not found',
    error: 'Failed to load paper',
  },

  // ── Basic information ──
  basicInfo: 'Basic Information',
  fieldTitle: 'Title',
  fieldYear: 'Year',
  fieldJournal: 'Journal',
  fieldAuthors: 'Authors',
  fieldAbstract: 'Abstract',
  fieldSummary: 'Paper summary (LLM)',
  fieldKgTitle: 'Knowledge graph title (LLM)',
  reviewStatus: 'Review status',
  dataSource: 'Data source',

  // ── Material states ──
  materialStates: 'Material States',
  materialStateFallback: 'Material state #{n}',
  fieldMaterialFamily: 'Material family',
  fieldElementCount: 'Number of distinct elements',
  fieldDimensionality: 'Material dimensionality',
  fieldCrystalSystem: 'Crystal system',
  fieldSpaceGroupSymbol: 'Space group symbol',
  fieldSpaceGroupNumber: 'Space group number',
  fieldSuperconductorKind: 'Superconductor kind',
  structureFamiliesLabel: 'Structure family tags',
  noMaterialStates: 'This paper has no material state data yet',

  // ── Pressure conditions ──
  pressureSection: 'Pressure conditions',
  pressureValue: 'Pressure: {value} GPa',
  rawText: 'Raw: {value}',
  pressureMin: 'Pressure min: {value} GPa',
  pressureMax: 'Pressure max: {value} GPa',

  // ── Tc results ──
  tcSection: 'Critical temperature Tc',
  tcKind: 'Type: {value}',
  tcValue: 'Tc: {value} K',
  tcRange: 'Tc range: {min} ~ {max} K',
  tcMethod: 'Determination method: {value}',
  tcMethodCustom: 'Custom method: {value}',

  // ── Calculation contexts ──
  calculationContexts: 'Calculation context',
  epcStrength: 'Electron-phonon coupling λ: {value}',
  omegaLog: 'Logarithmic phonon frequency ωlog: {value} K',
  muStar: 'Coulomb pseudopotential μ*: {value}',
  calcMethod: 'Calculation method: {value}',
  noValues: '(All values empty)',

  // ── Other properties ──
  otherProperties: 'Other Properties',
  unnamedProperty: 'Unnamed property',
  rawValue: 'Raw value: {value}',
  parsedValue: 'Parsed value: {value}',
  unitLabel: 'Unit: {value}',
  conditionNote: 'Condition note: {value}',

  // ── Research methods & findings ──
  methodsFindings: 'Research Methods & Findings',
  methodology: 'Research methodology',
  keyFinding: 'Key finding',
  researchMotivation: 'Research motivation',

  // ── Sidebar ──
  formulaLabel: 'Chemical formula',
  keywordsLabel: 'Keywords',
  structureIndex: 'Structure #{n}',
  noStructure: 'This record has no structure data yet',

  // ── 3D structure viewer ──
  renderFailed: '3D rendering failed',
  renderFailedDetail: '3D structure rendering failed: {error}',

  // ── My papers list (MyPapersList) ──
  loadMyPapersFailed: 'Failed to load my papers',
  emptyMyPapers: 'You have not submitted any papers yet. Once uploaded and submitted for review, your papers will appear here and can be reviewed in read-only mode at any time.',
  paperIndexFallback: 'Paper #{n}',

  // ── lib/paperDetailView table labels ──
  // Experimental measurement methods. Proprietary method names (Allen-Dynes,
  // McMillan, Eliashberg, …) stay as-is in both languages.
  tcMethods: {
    experimental: 'Experimental measurement',
    resistivity: 'Resistivity',
    magnetization: 'Magnetization',
    specific_heat: 'Specific heat',
    calculated: 'Theoretical calculation',
  },
  epcLambda: 'λ (electron-phonon coupling)',
} as const
