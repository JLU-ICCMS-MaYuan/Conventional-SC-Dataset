import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Card, CardContent, Button,
  Select, MenuItem, FormControl, InputLabel, IconButton, Tooltip,
} from '@mui/material'
import {
  Edit, ContentCopy, FileDownload,
} from '@mui/icons-material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { SC_TYPE_CONFIG } from '../lib/scatterConfig'
import ChartScatter from '../components/ChartScatter'
import ChartGroupEditor from '../components/ChartGroupEditor'

// ── DataPoint interface (matches ChartScatter) ──
interface DataPoint {
  x: number
  y: number
  material: string
  scType: string
  articleType: string | null
  year: number | null
  doi: string | null
  isInGroup: boolean
  isCustom: boolean
  label: string
}

// ── Constants ──
const ALL_SC_TYPES = [
  'hydride', 'cuprate', 'iron_based', 'nickel_based',
  'carbon', 'organic', 'others',
]

const SC_TYPE_SHAPE_ICONS: Record<string, string> = {
  hydride: '▲', cuprate: '■', iron_based: '◆',
  nickel_based: '●', carbon: '▼', organic: '⬢',
  others: '✚',
}

// ═══════════════════════════════════════════════════════
const SharePage: React.FC = () => {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin'

  const [visibleTypes, setVisibleTypes] = useState<Set<string>>(
    new Set(ALL_SC_TYPES),
  )

  // ── Raw data from APIs ──
  const [pressureData, setPressureData] = useState<any[]>([])
  const [yearData, setYearData] = useState<any[]>([])

  // ── Chart groups ──
  const [groups, setGroups] = useState<any[]>([])

  // ── Each chart has independent group selection ──
  const [chart1, setChart1] = useState<{
    groupId: number | null
    groupName: string
  }>({ groupId: null, groupName: '' })
  const [chart2, setChart2] = useState<{
    groupId: number | null
    groupName: string
  }>({ groupId: null, groupName: '' })

  // ── Editor dialog ──
  const [editorOpen, setEditorOpen] = useState(false)
  const [editingGroupId, setEditingGroupId] = useState<number | null>(null)

  // ── Load data on mount ──
  const loadAllGroups = () => {
    api.get<any[]>('/api/chart-groups')
      .then(remote => {
        const local = JSON.parse(localStorage.getItem('scwiki_local_groups') || '[]')
        setGroups([...local, ...(Array.isArray(remote) ? remote : [])])
      })
      .catch(() => {})
  }

  useEffect(() => {
    loadAllGroups()
    api.get<any[]>('/api/papers/stats/tc-pressure').then(setPressureData).catch(() => {})
    api.get<any[]>('/api/papers/stats/tc-year').then(setYearData).catch(() => {})
  }, [])

  // ── Refresh groups ──
  const refreshGroups = () => { loadAllGroups() }

  // ── Toggle sc type visibility ──
  const toggleType = (st: string) => {
    setVisibleTypes(prev => {
      const next = new Set(prev)
      if (next.has(st)) next.delete(st)
      else next.add(st)
      return next
    })
  }

  // ── Build background DataPoints from API data ──
  const buildBgPoints = (
    data: any[],
    _xKey: 'x',
    _chartKpIds: Set<number>,
  ): DataPoint[] => {
    return data
      .filter(d => {
        const st = d.sc_type || 'others'
        return visibleTypes.has(st)
      })
      .map(d => ({
        x: d.x,
        y: d.y,
        material: d.label || d.formula || '?',
        scType: d.sc_type || 'others',
        articleType:
          d.type === 'experimental' ? 'e'
          : d.type === 'theoretical' ? 't'
          : 't',
        year: d.year || null,
        doi: d.doi || null,
        isInGroup: false,
        isCustom: false,
        label: d.label || d.formula || '?',
      }))
  }

  // ── Build group DataPoints from selected group ──
  const buildGroupPoints = (
    chartState: { groupId: number | null },
    xField: 'pressure' | 'year' = 'pressure',
  ): DataPoint[] => {
    if (!chartState.groupId) return []
    const g = groups.find(gr => gr.id === chartState.groupId)
    if (!g?.items) return []
    return g.items
      .filter((it: any) => visibleTypes.has(it.type || 'others'))
      .map((it: any) => ({
        x: xField === 'year' ? (it.year ?? 0) : (it.pressure ?? 0),
        y: it.tc ?? 0,
        material: it.material,
        scType: it.type || 'others',
        articleType: it.article_type,
        year: it.year,
        doi: it.doi,
        isInGroup: true,
        isCustom: it.source === 'custom',
        label: it.material,
      }))
  }

  // ── Chart data composition ──
  const chart1Data: DataPoint[] = [
    ...buildBgPoints(pressureData, 'x', new Set()),
    ...buildGroupPoints(chart1),
  ]

  const chart2Data: DataPoint[] = [
    ...buildBgPoints(yearData, 'x', new Set()),
    ...buildGroupPoints(chart2, 'year'),
  ]

  // ── Shared group selector UI ──
  const renderGroupSelector = (
    state: { groupId: number | null; groupName: string },
    setState: React.Dispatch<
      React.SetStateAction<{ groupId: number | null; groupName: string }>
    >,
  ) => (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        gap: 1,
        flexWrap: 'wrap',
      }}
    >
      <FormControl size="small" sx={{ minWidth: 200 }}>
        <InputLabel>组合</InputLabel>
        <Select
          value={state.groupId ?? ''}
          label="组合"
          onChange={e => {
            const gid = e.target.value ? Number(e.target.value) : null
            setState({
              groupId: gid,
              groupName:
                groups.find(gr => gr.id === gid)?.name || '',
            })
          }}
        >
          <MenuItem value="">(无组合)</MenuItem>
          {groups.map(g => (
            <MenuItem key={g.id} value={g.id}>
              {g.name}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {isAdmin && (
        <Tooltip title="编辑">
          <IconButton size="small"
            onClick={() => { setEditingGroupId(state.groupId); setEditorOpen(true) }}>
            <Edit />
          </IconButton>
        </Tooltip>
      )}
      {state.groupId && isAdmin && (
        <>
          <Tooltip title="复制">
            <IconButton size="small"
              onClick={async () => { await api.post(`/api/chart-groups/${state.groupId}/copy`); refreshGroups() }}>
              <ContentCopy />
            </IconButton>
          </Tooltip>
          <Tooltip title="导出">
            <IconButton size="small"
              onClick={async () => {
                const d = await api.get<any>(`/api/chart-groups/${state.groupId}/export`)
                const blob = new Blob([JSON.stringify(d, null, 2)], { type: 'application/json' })
                const a = document.createElement('a'); a.href = URL.createObjectURL(blob)
                a.download = `${state.groupName || 'group'}.json`; a.click(); URL.revokeObjectURL(a.href)
              }}>
              <FileDownload />
            </IconButton>
          </Tooltip>
        </>
      )}
      {isAdmin && (
        <Button size="small" variant="outlined"
          onClick={() => { setEditingGroupId(null); setEditorOpen(true) }}>
          + 新建
        </Button>
      )}
    </Box>
  )

  // ═══════════════════════════════════════════════════════
  return (
    <Box>
      <Typography variant="overline">Community</Typography>
      <Typography variant="h1">社区</Typography>

      {/* ═══ Tc-Pressure Scatter ═══ */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Tc-Pressure 分布
          </Typography>
          {renderGroupSelector(chart1, setChart1)}
          <Box sx={{ mt: 1 }}>
            <ChartScatter
              title="Tc-Pressure 分布"
              data={chart1Data}
              xLabel="Pressure (GPa)"
              yLabel="Tc (K)"
              visibleTypes={visibleTypes}
              showBackground={!chart1.groupId}
              onToggleType={toggleType}
            />
          </Box>
        </CardContent>
      </Card>

      {/* ═══ Tc-Year Scatter ═══ */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Tc-Year 演变
          </Typography>
          {renderGroupSelector(chart2, setChart2)}
          <Box sx={{ mt: 1 }}>
            <ChartScatter
              title="Tc-Year 演变"
              data={chart2Data}
              xLabel="Year"
              yLabel="Tc (K)"
              xDomain={[1900, 'auto']}
              visibleTypes={visibleTypes}
              showBackground={!chart2.groupId}
              onToggleType={toggleType}
            />
          </Box>
        </CardContent>
      </Card>

      {/* ═══ Group Editor Dialog ═══ */}
      <ChartGroupEditor
        open={editorOpen}
        groupId={editingGroupId}
        onClose={() => setEditorOpen(false)}
        onSaved={refreshGroups}
      />
    </Box>
  )
}

export default SharePage
