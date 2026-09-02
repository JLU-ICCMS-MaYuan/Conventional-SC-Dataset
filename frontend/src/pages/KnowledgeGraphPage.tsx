import React, { useCallback, useEffect, useRef, useState } from 'react'
import {
  Alert, Autocomplete, Box, Button, Checkbox, Chip, CircularProgress, Divider,
  FormControl, FormControlLabel, IconButton, InputLabel, MenuItem, Paper, Select, Stack,
  TextField, Tooltip, Typography,
} from '@mui/material'
import AccountTreeIcon from '@mui/icons-material/AccountTree'
import NorthWestIcon from '@mui/icons-material/NorthWest'
import SearchIcon from '@mui/icons-material/Search'
import SouthEastIcon from '@mui/icons-material/SouthEast'
import SaveIcon from '@mui/icons-material/Save'
import { DataSet } from 'vis-data'
import { Network } from 'vis-network'
import 'vis-network/styles/vis-network.css'
import { api } from '../lib/api'
import { loadClassificationCatalogs, type ClassificationTerm } from '../lib/classifications'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

type SuperconductorKind = 'conventional' | 'unconventional' | 'unknown'
type GraphDirection = 'upstream' | 'downstream'

interface GraphNode {
  paper_id: number
  label: string
  title: string
  year: number | null
  material_families: Array<{ id: number; name: string }>
  superconductor_kind: SuperconductorKind
  citation_count: number
  marks: Array<'origin' | 'breakthrough'>
}

interface GraphEdge {
  citing_paper_id: number
  cited_paper_id: number
}

interface GraphOverview {
  nodes: GraphNode[]
  edges: GraphEdge[]
  total_nodes: number
}

interface NeighborResponse {
  center_paper_id: number
  direction: GraphDirection
  nodes: GraphNode[]
  edges: GraphEdge[]
  offset: number
  limit: number
  remaining_count: number
}

const nodeKey = (paperID: number) => `paper:${paperID}`
const edgeKey = (edge: GraphEdge) => `${nodeKey(edge.citing_paper_id)}>${nodeKey(edge.cited_paper_id)}`

function nodeColor(node: GraphNode) {
  if (node.marks.includes('origin')) return { background: '#c62828', border: '#7f1d1d' }
  if (node.marks.includes('breakthrough')) return { background: '#0f766e', border: '#115e59' }
  if (node.superconductor_kind === 'conventional') return { background: '#2563eb', border: '#1d4ed8' }
  if (node.superconductor_kind === 'unconventional') return { background: '#d97706', border: '#b45309' }
  return { background: '#64748b', border: '#475569' }
}

function nodeSize(citationCount: number) {
  return Math.min(42, 12 + Math.sqrt(Math.max(0, citationCount)) * 5)
}

function nodeTooltip(node: GraphNode) {
  const families = node.material_families.map(item => item.name).join('、')
  const marks = node.marks.join('、')
  return [node.title, node.year ? String(node.year) : '', families, `库内被引 ${node.citation_count}`, marks]
    .filter(Boolean)
    .map(value => String(value).replace(/[<>&]/g, character => {
      if (character === '<') return '&lt;'
      if (character === '>') return '&gt;'
      return '&amp;'
    }))
    .join('<br/>')
}

const KnowledgeGraphPage: React.FC = () => {
  const { t } = useLanguage()
  const { user } = useAuth()
  const containerRef = useRef<HTMLDivElement>(null)
  const networkRef = useRef<Network | null>(null)
  const nodesDs = useRef<DataSet<Record<string, unknown>>>(new DataSet([]))
  const edgesDs = useRef<DataSet<Record<string, unknown>>>(new DataSet([]))
  const graphNodes = useRef(new Map<number, GraphNode>())

  const [catalogs, setCatalogs] = useState<ClassificationTerm[]>([])
  const [selectedFamilies, setSelectedFamilies] = useState<number[]>([])
  const [selectedKind, setSelectedKind] = useState<'' | 'conventional' | 'unconventional'>('')
  const [appliedFamilies, setAppliedFamilies] = useState<number[]>([])
  const [appliedKind, setAppliedKind] = useState<'' | 'conventional' | 'unconventional'>('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [searchResults, setSearchResults] = useState<GraphNode[]>([])
  const [searching, setSearching] = useState(false)
  const [remaining, setRemaining] = useState<Record<string, number>>({})
  const [nextOffsets, setNextOffsets] = useState<Record<string, number>>({})
  const [markDraft, setMarkDraft] = useState<Array<'origin' | 'breakthrough'>>([])
  const [savingMarks, setSavingMarks] = useState(false)

  const addNodes = useCallback((items: GraphNode[]) => {
    for (const item of items) {
      graphNodes.current.set(item.paper_id, item)
      const id = nodeKey(item.paper_id)
      const existing = nodesDs.current.get(id)
      nodesDs.current.update({
        id,
        label: item.label.length > 42 ? `${item.label.slice(0, 42)}...` : item.label,
        title: nodeTooltip(item),
        size: nodeSize(item.citation_count),
        color: nodeColor(item),
        borderWidth: item.marks.length ? 3 : 2,
        font: { color: '#172033', size: 12, face: 'Arial' },
        ...(existing ? {} : { x: (Math.random() - 0.5) * 380, y: (Math.random() - 0.5) * 260 }),
      })
    }
  }, [])

  const addEdges = useCallback((items: GraphEdge[]) => {
    for (const item of items) {
      const id = edgeKey(item)
      if (!edgesDs.current.get(id)) {
        edgesDs.current.add({
          id,
          from: nodeKey(item.citing_paper_id),
          to: nodeKey(item.cited_paper_id),
          title: t('kg.citationEdge'),
          arrows: { to: { enabled: true, scaleFactor: 0.55 } },
          color: { color: '#64748b', highlight: '#0f766e', opacity: 0.72 },
          width: 1.4,
        })
      }
    }
  }, [t])

  const selectPaper = useCallback((paperID: number) => {
    const node = graphNodes.current.get(paperID) || null
    setSelectedNode(node)
    setMarkDraft(node?.marks || [])
  }, [])

  useEffect(() => {
    if (!containerRef.current) return undefined
    const network = new Network(containerRef.current, { nodes: nodesDs.current, edges: edgesDs.current }, {
      autoResize: true,
      physics: {
        solver: 'forceAtlas2Based',
        forceAtlas2Based: { gravitationalConstant: -42, centralGravity: 0.008, springLength: 165, springConstant: 0.055 },
        stabilization: { iterations: 140, fit: true },
      },
      edges: { smooth: { enabled: true, type: 'dynamic', roundness: 0.5 } },
      nodes: { shape: 'dot', shadow: { enabled: true, color: 'rgba(15, 23, 42, 0.18)', size: 5, x: 1, y: 2 } },
      interaction: { hover: true, tooltipDelay: 120, zoomView: true, dragView: true },
    })
    network.on('click', event => {
      if (event.nodes.length) {
        const value = String(event.nodes[0])
        const paperID = Number(value.replace('paper:', ''))
        if (Number.isFinite(paperID)) selectPaper(paperID)
      } else {
        setSelectedNode(null)
      }
    })
    networkRef.current = network
    return () => network.destroy()
  }, [selectPaper])

  useEffect(() => {
    let active = true
    loadClassificationCatalogs()
      .then(data => { if (active) setCatalogs(data.material_families || []) })
      .catch(() => { if (active) setError(t('kg.catalogLoadFailed')) })
    return () => { active = false }
  }, [t])

  const loadOverview = useCallback(async () => {
    setLoading(true)
    setError('')
    const params = new URLSearchParams({ limit: '30' })
    appliedFamilies.forEach(id => params.append('material_family_id', String(id)))
    if (appliedKind) params.set('superconductor_kind', appliedKind)
    try {
      const data = await api.get<GraphOverview>(`/api/knowledge-graph/overview?${params}`)
      graphNodes.current.clear()
      nodesDs.current.clear()
      edgesDs.current.clear()
      addNodes(data.nodes)
      addEdges(data.edges)
      setSelectedNode(null)
      setRemaining({})
      setNextOffsets({})
      networkRef.current?.fit({ animation: { duration: 220, easingFunction: 'easeInOutQuad' } })
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('kg.graphLoadFailed'))
    } finally {
      setLoading(false)
    }
  }, [addEdges, addNodes, appliedFamilies, appliedKind, t])

  useEffect(() => { void loadOverview() }, [loadOverview])

  const searchPapers = async () => {
    const query = searchTerm.trim()
    if (!query) return
    setSearching(true)
    try {
      const result = await api.get<{ nodes: GraphNode[] }>(`/api/knowledge-graph/search?q=${encodeURIComponent(query)}&limit=10`)
      setSearchResults(result.nodes)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('kg.searchFailed'))
    } finally {
      setSearching(false)
    }
  }

  const pinSearchResult = (node: GraphNode) => {
    addNodes([node])
    selectPaper(node.paper_id)
    setSearchResults([])
    setSearchTerm('')
    networkRef.current?.focus(nodeKey(node.paper_id), { scale: 1.2, animation: { duration: 260, easingFunction: 'easeInOutQuad' } })
  }

  const loadNeighbors = async (direction: GraphDirection) => {
    if (!selectedNode) return
    const key = `${selectedNode.paper_id}:${direction}`
    const offset = nextOffsets[key] || 0
    setError('')
    try {
      const data = await api.get<NeighborResponse>(
        `/api/knowledge-graph/papers/${selectedNode.paper_id}/neighbors?direction=${direction}&offset=${offset}&limit=5`,
      )
      addNodes(data.nodes)
      addEdges(data.edges)
      setRemaining(current => ({ ...current, [key]: data.remaining_count }))
      setNextOffsets(current => ({ ...current, [key]: data.offset + data.nodes.length }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('kg.neighborLoadFailed'))
    }
  }

  const canManageMarks = Boolean(user?.is_admin || user?.is_superadmin)
  const saveMarks = async () => {
    if (!selectedNode) return
    setSavingMarks(true)
    setError('')
    try {
      const result = await api.put<{ marks: Array<'origin' | 'breakthrough'> }>(
        `/api/admin/papers/${selectedNode.paper_id}/graph-marks`, { marks: markDraft },
      )
      const updated = { ...selectedNode, marks: result.marks }
      graphNodes.current.set(updated.paper_id, updated)
      addNodes([updated])
      setSelectedNode(updated)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : t('kg.markSaveFailed'))
    } finally {
      setSavingMarks(false)
    }
  }

  const familyLabel = (family: ClassificationTerm) => {
    return t('kg.familyOption', { name: family.name })
  }
  const upstreamKey = selectedNode ? `${selectedNode.paper_id}:upstream` : ''
  const downstreamKey = selectedNode ? `${selectedNode.paper_id}:downstream` : ''

  return (
    <Box sx={{ height: 'calc(100vh - 64px)', display: 'flex', flexDirection: 'column', px: { xs: 1.5, md: 3 }, py: 2, gap: 1.5 }}>
      <Box sx={{ display: 'flex', alignItems: { xs: 'flex-start', sm: 'center' }, justifyContent: 'space-between', gap: 1.5, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="overline" color="text.secondary">Citation Graph</Typography>
          <Typography variant="h5" fontWeight={700}>{t('kg.title')}</Typography>
          <Typography variant="body2" color="text.secondary">{t('kg.description')}</Typography>
        </Box>
        <Chip icon={<AccountTreeIcon />} label={t('kg.mysqlSource')} variant="outlined" size="small" />
      </Box>

      <Paper variant="outlined" sx={{ p: 1.25, borderRadius: 1 }}>
        <Stack direction={{ xs: 'column', lg: 'row' }} spacing={1.2} alignItems={{ lg: 'center' }}>
          <FormControl size="small" sx={{ minWidth: { lg: 230 } }}>
            <InputLabel id="graph-family-filter-label">{t('kg.materialFamily')}</InputLabel>
            <Select
              labelId="graph-family-filter-label"
              multiple
              value={selectedFamilies}
              label={t('kg.materialFamily')}
              onChange={event => {
                const value = event.target.value
                setSelectedFamilies(
                  (typeof value === 'string' ? value.split(',') : value as unknown[])
                    .map(item => Number(item))
                    .filter(Number.isSafeInteger),
                )
              }}
              renderValue={selected => (selected as number[]).map(id => catalogs.find(item => item.id === id)?.name || id).join('、')}
            >
              {catalogs.map(family => <MenuItem key={family.id} value={family.id}>{familyLabel(family)}</MenuItem>)}
            </Select>
          </FormControl>
          <FormControl size="small" sx={{ minWidth: { lg: 190 } }}>
            <InputLabel id="graph-kind-filter-label">{t('kg.superconductorKind')}</InputLabel>
            <Select
              labelId="graph-kind-filter-label"
              value={selectedKind}
              label={t('kg.superconductorKind')}
              onChange={event => setSelectedKind(event.target.value as '' | 'conventional' | 'unconventional')}
            >
              <MenuItem value="">{t('kg.allKinds')}</MenuItem>
              <MenuItem value="conventional">{t('kg.conventional')}</MenuItem>
              <MenuItem value="unconventional">{t('kg.unconventional')}</MenuItem>
            </Select>
          </FormControl>
          <Button variant="contained" onClick={() => { setAppliedFamilies(selectedFamilies); setAppliedKind(selectedKind) }} disabled={loading}>{t('kg.applyFilters')}</Button>
          <Box sx={{ flex: 1 }} />
          <Autocomplete
            size="small"
            options={searchResults}
            getOptionLabel={item => item.title}
            filterOptions={options => options}
            loading={searching}
            sx={{ width: { xs: '100%', lg: 360 } }}
            inputValue={searchTerm}
            onInputChange={(_, value) => setSearchTerm(value)}
            onChange={(_, item) => { if (item) pinSearchResult(item) }}
            renderInput={params => (
              <TextField
                {...params}
                label={t('kg.searchPaper')}
                onKeyDown={event => { if (event.key === 'Enter') { event.preventDefault(); void searchPapers() } }}
                InputProps={{
                  ...params.InputProps,
                  endAdornment: <>
                    {searching ? <CircularProgress color="inherit" size={16} /> : (
                      <Tooltip title={t('kg.searchAction')}>
                        <IconButton size="small" onClick={() => void searchPapers()}><SearchIcon fontSize="small" /></IconButton>
                      </Tooltip>
                    )}
                    {params.InputProps.endAdornment}
                  </>,
                }}
              />
            )}
          />
        </Stack>
      </Paper>

      {error && <Alert severity="error" onClose={() => setError('')}>{error}</Alert>}

      <Box sx={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: { xs: 'column', lg: 'row' }, gap: 1.5 }}>
        <Paper variant="outlined" sx={{ position: 'relative', flex: 1, minHeight: { xs: 400, lg: 0 }, borderRadius: 1, overflow: 'hidden' }}>
          {loading && <CircularProgress size={24} sx={{ position: 'absolute', top: 14, right: 14, zIndex: 2 }} />}
          <Box ref={containerRef} sx={{ position: 'absolute', inset: 0 }} />
        </Paper>

        <Paper variant="outlined" sx={{ width: { xs: '100%', lg: 340 }, p: 2, overflow: 'auto', borderRadius: 1 }}>
          {!selectedNode && (
            <>
              <Typography variant="subtitle1" fontWeight={700}>{t('kg.selectHint')}</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.75 }}>{t('kg.selectDescription')}</Typography>
            </>
          )}
          {selectedNode && (
            <Stack spacing={1.1}>
              <Box>
                <Typography variant="overline" color="text.secondary">{t('kg.selectedPaper')}</Typography>
                <Typography variant="subtitle1" fontWeight={700}>{selectedNode.title}</Typography>
                <Typography variant="body2" color="text.secondary">
                  {selectedNode.year || t('kg.yearUnknown')} · {t('kg.citationCount', { count: selectedNode.citation_count })}
                </Typography>
              </Box>
              {selectedNode.material_families.length > 0 && (
                <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                  {selectedNode.material_families.map(family => <Chip key={family.id} label={family.name} size="small" variant="outlined" />)}
                </Stack>
              )}
              {selectedNode.marks.length > 0 && (
                <Stack direction="row" spacing={0.5}>
                  {selectedNode.marks.map(mark => <Chip key={mark} label={mark === 'origin' ? t('kg.origin') : t('kg.breakthrough')} size="small" color={mark === 'origin' ? 'error' : 'success'} />)}
                </Stack>
              )}
              <Divider />
              <Typography variant="caption" color="text.secondary">{t('kg.expandHint')}</Typography>
              <Button size="small" startIcon={<NorthWestIcon />} disabled={remaining[upstreamKey] === 0} onClick={() => void loadNeighbors('upstream')}>
                {remaining[upstreamKey] == null ? t('kg.loadUpstream') : remaining[upstreamKey] > 0
                  ? t('kg.moreUpstream', { count: remaining[upstreamKey] }) : t('kg.noMoreUpstream')}
              </Button>
              <Button size="small" startIcon={<SouthEastIcon />} disabled={remaining[downstreamKey] === 0} onClick={() => void loadNeighbors('downstream')}>
                {remaining[downstreamKey] == null ? t('kg.loadDownstream') : remaining[downstreamKey] > 0
                  ? t('kg.moreDownstream', { count: remaining[downstreamKey] }) : t('kg.noMoreDownstream')}
              </Button>
              {canManageMarks && (
                <>
                  <Divider />
                  <Typography variant="subtitle2">{t('kg.milestone')}</Typography>
                  <FormControlLabel
                    control={<Checkbox checked={markDraft.includes('origin')} onChange={event => setMarkDraft(current => event.target.checked ? Array.from(new Set([...current, 'origin'])) as Array<'origin' | 'breakthrough'> : current.filter(mark => mark !== 'origin'))} />}
                    label={t('kg.origin')}
                  />
                  <FormControlLabel
                    control={<Checkbox checked={markDraft.includes('breakthrough')} onChange={event => setMarkDraft(current => event.target.checked ? Array.from(new Set([...current, 'breakthrough'])) as Array<'origin' | 'breakthrough'> : current.filter(mark => mark !== 'breakthrough'))} />}
                    label={t('kg.breakthrough')}
                  />
                  <Button variant="outlined" size="small" startIcon={<SaveIcon />} disabled={savingMarks} onClick={() => void saveMarks()}>
                    {t('kg.saveMarks')}
                  </Button>
                </>
              )}
            </Stack>
          )}
        </Paper>
      </Box>
    </Box>
  )
}

export default KnowledgeGraphPage
