import React, { useState, useEffect } from 'react'
import {
  Box, Typography, Paper, Tabs, Tab, IconButton, Chip, Drawer,
} from '@mui/material'
import DownloadIcon from '@mui/icons-material/Download'
import RestartAltIcon from '@mui/icons-material/RestartAlt'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, Line,
} from 'recharts'
import { api } from '../lib/api'

interface ChartPoint {
  x: number; y: number; type: string; label: string; year?: number
  formula?: string; space_group?: string; doi?: string; sc_type?: string
}

const SC_TYPES: Record<string, string> = {
  h: '高压氢化物', c: '碳基', cb: '铜基', ot: '其他超导',
  cuprate: '铜基', iron_based: '铁基', nickel_based: '镍基',
  hydride: '高压氢化物', carbon: '碳基', organic: '有机', others: '其他',
}
const SC_COLORS: Record<string, string> = {
  cuprate: '#ff6384', iron_based: '#4bc0c0', nickel_based: '#4bef3a',
  hydride: '#9966ff', carbon: '#36a2eb', organic: '#ffce56', others: '#cc4646',
}

const ChartsPage: React.FC = () => {
  const [tab, setTab] = useState(0)
  const [data, setData] = useState<ChartPoint[]>([])
  const [selected, setSelected] = useState<ChartPoint | null>(null)

  useEffect(() => {
    const endpoint = tab === 0 ? '/api/papers/stats/tc-pressure' : '/api/papers/stats/tc-year'
    api.get<ChartPoint[]>(endpoint).then(setData).catch(() => setData([]))
  }, [tab])

  const expData = data.filter((d) => d.type === 'experimental')
  const theoData = data.filter((d) => d.type === 'theoretical')

  // s-factor curves for Tc-pressure chart
  const sCurves = Array.from({ length: 10 }, (_, i) => {
    const s = i + 1
    const points = []
    for (let p = 0; p <= 300; p += 10) {
      points.push({ x: p, y: s * Math.sqrt(1521 + p * p) })
    }
    return { s, points }
  })

  // Generate per-type scatter series
  const byType: Record<string, ChartPoint[]> = {}
  data.forEach((d) => {
    const key = d.sc_type || 'others'
    if (!byType[key]) byType[key] = []
    byType[key].push(d)
  })

  const handleExportCSV = () => {
    const header = 'formula,pressure,year,tc,doi,type\n'
    const rows = data.map((d) => `${d.formula || d.label},${tab === 0 ? d.x : '-'},${tab === 1 ? d.x : d.year || '-'},${d.y},${d.doi || '-'},${d.type}`).join('\n')
    const blob = new Blob([header + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `sc-wiki-chart.csv`; a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 3, alignItems: 'end', mb: 3 }}>
        <Box>
          <Typography variant="overline">Research Community Charts</Typography>
          <Typography variant="h1">超导热点图表</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            每张图表独立配置，切换标签查看 Tc-压强 和 Tc-年份 分布。
          </Typography>
        </Box>
      </Box>

      <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3 }}>
        <Tab label="Tc vs Pressure" />
        <Tab label="Tc vs Year" />
      </Tabs>

      <Paper sx={{ p: 2.5, borderRadius: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h2">{tab === 0 ? 'Tc-Pressure 分布' : 'Tc-Year 演变'}</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <IconButton size="small" onClick={handleExportCSV} title="导出 CSV"><DownloadIcon /></IconButton>
            <IconButton size="small" onClick={() => setData([])} title="刷新"><RestartAltIcon /></IconButton>
          </Box>
        </Box>

        <ResponsiveContainer width="100%" height={500}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name={tab === 0 ? 'Pressure' : 'Year'}
              label={{ value: tab === 0 ? 'Pressure (GPa)' : 'Year', position: 'bottom' }}
              domain={tab === 0 ? [0, 'auto'] : [1900, 'auto']}
            />
            <YAxis type="number" dataKey="y" name="Tc" label={{ value: 'Tc (K)', angle: -90, position: 'insideLeft' }} domain={[0, 'auto']} />
            <Tooltip
              formatter={(value: number, name: string) => [name === 'y' ? `${value} K` : `${value}`, name === 'y' ? 'Tc' : name]}
              labelFormatter={(v: number) => tab === 0 ? `${v} GPa` : `Year ${v}`}
            />
            <Legend />

            {/* s-factor curves (Tc-pressure only) */}
            {tab === 0 && sCurves.map(({ s, points }) => (
              <Line key={`s${s}`} data={points} dataKey="y" stroke="rgba(0,0,0,0.06)" strokeDasharray="3 3" dot={false} legendType="none" />
            ))}

            {/* Experimental */}
            <Scatter name="实验" data={expData} fill="#4f46e5" shape="square" onClick={(p: any) => setSelected(p)} />
            {/* Theoretical */}
            <Scatter name="理论" data={theoData} fill="#82ca9d" shape="triangle" onClick={(p: any) => setSelected(p)} />

            {/* Per-type legend only */}
            {Object.entries(byType).map(([type, _points]) => (
              <Scatter key={type} name={SC_TYPES[type] || type} data={[]} fill={SC_COLORS[type] || '#888'} legendType="rect" />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </Paper>

      {/* Point Detail Drawer */}
      <Drawer anchor="right" open={!!selected} onClose={() => setSelected(null)} PaperProps={{ sx: { width: 360, p: 3 } }}>
        {selected && (
          <Box>
            <Typography variant="h3" gutterBottom>{selected.label || selected.formula}</Typography>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Typography variant="body2">Tc: {selected.y} K</Typography>
              <Typography variant="body2">{tab === 0 ? `压强: ${selected.x} GPa` : `年份: ${selected.x}`}</Typography>
              <Typography variant="body2">类型: {selected.type === 'experimental' ? '实验' : '理论'}</Typography>
              <Typography variant="body2">超导分类: {SC_TYPES[selected.sc_type || ''] || '未知'}</Typography>
              <Typography variant="body2">空间群: {selected.space_group || '-'}</Typography>
              {selected.doi && <Typography variant="body2">DOI: {selected.doi}</Typography>}
            </Box>
          </Box>
        )}
      </Drawer>
    </Box>
  )
}

export default ChartsPage
