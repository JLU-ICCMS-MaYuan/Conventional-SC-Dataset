export default {
  title: 'Superconductivity Citation Development Graph', description: 'Arrows point from a citing paper to its cited paper. Larger circles have more approved SC-Wiki citations.',
  mysqlSource: 'SC-Wiki citation facts', materialFamily: 'Material family', superconductorKind: 'Superconductor type', allKinds: 'All types', conventional: 'Conventional', unconventional: 'Unconventional', applyFilters: 'Apply filters', familyOption: '{name}',
  searchPaper: 'Search title or DOI', searchAction: 'Search papers', citationEdge: 'Citation',
  selectHint: 'Select a paper', selectDescription: 'Select a circle for details. Upstream papers are cited sources; downstream papers cite this work.', selectedPaper: 'Current paper',
  yearUnknown: 'Year unknown', citationCount: '{count} in-library citations', expandHint: 'Each request shows up to five papers. Continue loading to explore further.',
  loadUpstream: 'Show upstream papers', loadDownstream: 'Show downstream papers', moreUpstream: 'More upstream ({count} remaining)', moreDownstream: 'More downstream ({count} remaining)', noMoreUpstream: 'No more upstream papers', noMoreDownstream: 'No more downstream papers',
  origin: 'Origin', breakthrough: 'Breakthrough', milestone: 'Field milestones', saveMarks: 'Save milestones',
  catalogLoadFailed: 'Could not load material-family catalog', graphLoadFailed: 'Could not load citation graph', searchFailed: 'Could not search papers', neighborLoadFailed: 'Could not load related papers', markSaveFailed: 'Could not save milestones',
} as const
