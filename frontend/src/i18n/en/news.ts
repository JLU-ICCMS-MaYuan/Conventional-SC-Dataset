// 英文快讯域文案。键集必须与 zh/news.ts 完全一致——字典类型由中文侧推导，
// 缺键会在 `tsc -b` 阶段报错，不会静默回退。
export default {
  // Hero
  heroTitle: 'Superconducting Literature Database',
  heroSubtitle: 'A superconductivity-material search platform built around the periodic table. It covers conventional superconductors, cuprates, iron-based and high-pressure hydrides, with literature search, AI Q&A and Tc prediction.',
  startExploring: 'Start Exploring',
  aiAssistant: 'AI Literature Assistant',

  // Feature cards
  featureElementSearch: 'Element Search',
  featureElementSearchDesc: 'Pick elements from the periodic table to search superconductivity records, filterable by Tc, pressure and space group.',
  featureAiQa: 'AI Q&A',
  featureAiQaDesc: 'Ask in natural language; AI answers with streaming output and cited sources.',
  featureTcPredict: 'Tc Prediction',
  featureTcPredictDesc: 'Upload structural files and density of states to estimate the superconducting critical temperature.',

  // Nobel milestones
  nobelMilestones: 'Nobel Prize Milestones',
  // Milestone entries are static site editorial content (not paper data) and follow the UI language.
  nobelMilestoneItems: [
    {
      year: 1913,
      name: 'Heike Kamerlingh Onnes',
      title: 'Liquefaction of helium and the discovery of superconductivity',
      feat: 'In 1908 Onnes first liquefied helium (boiling point 4.2 K); in 1911 he found that mercury\'s resistance suddenly dropped to zero at 4.2 K — the first observation of superconductivity. This not only proved a new state of matter at extremely low temperatures, but also opened a century of superconductivity research. Onnes wrote "Mercury practically zero" in his notebook, a moment engraved in the history of physics.',
    },
    {
      year: 1972,
      name: 'John Bardeen, Leon Cooper, John Schrieffer',
      title: 'The BCS microscopic theory of superconductivity',
      feat: 'In 1957 the three proposed the BCS theory, the first complete quantum-mechanical microscopic explanation of superconductivity: electrons exchange lattice vibrations (phonons) to form Cooper pairs that move in a macroscopic quantum state without resistance. Bardeen remains the only person to have won the Nobel Prize in Physics twice (first in 1956, for the transistor). The BCS theory is still one of the most important cornerstones of condensed matter physics.',
    },
    {
      year: 1973,
      name: 'Leo Esaki, Ivar Giaever, Brian Josephson',
      title: 'Tunneling in semiconductors and superconductors',
      feat: 'Esaki discovered electron tunneling in semiconductors in 1957 (the Esaki diode); Giaever experimentally verified single-electron tunneling in superconductors in 1960; and Josephson, then a 22-year-old graduate student, predicted the tunneling of Cooper pairs across superconducting junctions — the famous Josephson effect. The prediction was later confirmed with high precision (error < 10⁻¹²) and became the physical basis of superconducting electronics, SQUID magnetometers and voltage standards.',
    },
    {
      year: 1987,
      name: 'Georg Bednorz, Alex Müller',
      title: 'Breakthrough of cuprate high-temperature superconductors',
      feat: 'In 1986, Bednorz and Müller at IBM Zurich discovered 35 K superconductivity in the lanthanum barium copper oxide (LaBaCuO) ceramic, breaking the 23 K record held by Nb₃Ge for 13 years. More importantly, this oxide ceramic was a new type of superconductor that conventional BCS theory could not explain. The discovery triggered a global "superconductivity gold rush"; Ching-Wu Chu and Zhongxian Zhao soon pushed Tc above the liquid-nitrogen regime (77 K), dramatically lowering the cost of superconducting applications and reshaping the industry.',
    },
    {
      year: 2003,
      name: 'Alexei Abrikosov, Vitaly Ginzburg, Anthony Leggett',
      title: 'Type-II superconductors and the theory of superfluidity',
      feat: 'Ginzburg and Landau proposed the phenomenological theory of superconducting phase transitions (GL theory) in 1950, describing the macroscopic wavefunction of the superconducting state. In 1957 Abrikosov predicted the magnetic flux vortex lattice in type-II superconductors — the famous Abrikosov vortices — which directly explains how practical superconducting magnets (MRI, particle accelerators) work in high fields. Leggett shared the prize for his theoretical work on superfluid ³He. Together, the three laid the theoretical foundations of modern superconducting applications.',
    },
  ],

  // Feed
  feedTitle: 'Superconductivity News & Latest Papers',
  feedSubtitle: 'Collected daily from official sources · Sorted by publication date',
  kindLabel: 'Content type',
  kindAll: 'All content',
  kindNews: 'News',
  kindPreprint: 'Preprint',
  kindJournalArticle: 'Journal article',
  autoCollected: 'Auto-collected, not reviewed by this site',
  loadingFeed: 'Loading news…',
  feedLoadFailed: 'Failed to load the feed. Please retry. This does not mean there is no news.',
  feedEmpty: 'No news matches the current filter',
  feedEmptyHint: 'Try a different content type, or check whether the sources below have been collected successfully.',
  publishedAt: 'Published: {date}',
  publishedLabel: 'Published: ',
  etAl: ' et al.',
  pageInfo: '{total} items · Page {page} / {pages}',
  prevPage: 'Previous',
  nextPage: 'Next',

  // Source update status
  sourceStatusTitle: 'Source update status',
  sourcesNeedAttention: ' · Some sources need attention',
  sourceItem: '{name}: {status}',
  errorCode: ' ({code})',
  sourceFailed: 'Collection failed; will retry automatically',
  sourceNever: 'Not collected yet',
  sourceStalled: 'Previous collection did not finish; waiting to resume',
  sourceRunning: 'Collecting now',
  sourceStale: 'No update in over {hours} hours',
  sourceUpdated: 'Up to date',
  lastSuccess: 'Last success: {time}',
  noSuccessRecord: 'No successful run yet',
  timeUnknown: 'Time unknown',
  physorgNote: 'Phys.org only covers the current subscription window; historical news removed during downtime may not be recoverable.',

  // Detail drawer
  authorLabel: 'Authors: ',
  journalLabel: 'Journal: ',
  sourceLabel: 'Source: ',
  versionLabel: 'Version: ',
  collectedLabel: 'Collected: ',
  summaryLabel: 'Abstract',
  summarySourceLabel: 'Abstract source: ',
  doiLabel: 'DOI: ',
  originalLinks: 'Original links',

  // Date display
  dateNotProvided: 'Date not provided',
  yearOnly: '{year}',
  monthOnly: '{month} (month only)',

  // Manual news
  manualTitle: 'Manual News',
  loadingManual: 'Loading manual news…',
  retryManual: 'Retry manual news',
  manualLoadFailed: 'Failed to load manual news',
  manualEmpty: 'No manual news has been published yet.',
} as const
