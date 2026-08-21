import React, { useState, useEffect, useCallback } from 'react'
import {
  Box, Typography, Card, CardContent, Button,
  Select, MenuItem, FormControl, InputLabel, IconButton, Tooltip,
  Drawer, CircularProgress, Chip, Alert, Snackbar, Avatar, Divider,
} from '@mui/material'
import {
  Edit, ContentCopy, FileDownload, Close, OpenInNew, Refresh, EmojiEvents,
} from '@mui/icons-material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { SC_TYPE_CONFIG } from '../lib/scatterConfig'
import ChartScatter from '../components/ChartScatter'
import ChartGroupEditor from '../components/ChartGroupEditor'
import {
  clearChartPreferences, DEFAULT_CHART_PREFERENCES, readChartPreferences,
  TC_FIELDS, TC_FIELD_LABELS, TcField, writeChartPreferences,
} from '../lib/chartPreferences'

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
  paperId?: number
}

interface ContributionRank {
  rank: number
  user_id: number
  username: string
  display_name: string
  avatar_text: string
  contribution_count: number
}

interface ContributionSnapshot {
  participant_count: number
  upload_leaderboard: ContributionRank[]
  review_leaderboard: ContributionRank[]
  current_user?: { upload: ContributionRank | null; review: ContributionRank | null }
  generated_at: string
}

const contributionBarWidth = (count: number, maxCount: number): number => {
  if (!Number.isFinite(count) || !Number.isFinite(maxCount) || count <= 0 || maxCount <= 0) return 0
  return Math.min(100, Math.max(0, (count / maxCount) * 100))
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
  const [pressureTcField, setPressureTcField] = useState<TcField>(DEFAULT_CHART_PREFERENCES.pressureTcField)
  const [yearTcField, setYearTcField] = useState<TcField>(DEFAULT_CHART_PREFERENCES.yearTcField)
  const [pressureLoading, setPressureLoading] = useState(false)
  const [yearLoading, setYearLoading] = useState(false)
  const [pressureError, setPressureError] = useState('')
  const [yearError, setYearError] = useState('')

  // ── Chart groups ──
  const [groups, setGroups] = useState<any[]>([])
  const [contributions, setContributions] = useState<ContributionSnapshot | null>(null)
  const [contributionsLoading, setContributionsLoading] = useState(true)
  const [contributionsError, setContributionsError] = useState('')

  // ── Each chart has independent group selection ──
  const [chart1, setChart1] = useState<{
    groupId: number | null
    groupName: string
  }>({ groupId: null, groupName: '' })
  const [chart2, setChart2] = useState<{
    groupId: number | null
    groupName: string
  }>({ groupId: null, groupName: '' })

  // ── Paper detail drawer ──
  const [selectedPaperId, setSelectedPaperId] = useState<number | null>(null)
  const [paperDetail, setPaperDetail] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

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
  }, [])

  const loadContributions = useCallback(async (force = false) => {
    setContributionsLoading(true)
    try {
      const suffix = force ? '?refresh=true' : ''
      setContributions(await api.get<ContributionSnapshot>(`/api/community/contributions${suffix}`))
      setContributionsError('')
    } catch {
      setContributionsError('贡献榜单刷新失败，请稍后重试')
    } finally {
      setContributionsLoading(false)
    }
  }, [])

  useEffect(() => {
    void loadContributions()
    const timer = window.setInterval(() => { void loadContributions() }, 60 * 60 * 1000)
    return () => window.clearInterval(timer)
  }, [user?.id, loadContributions])

  useEffect(() => {
    const preferences = user ? readChartPreferences(user.id) : DEFAULT_CHART_PREFERENCES
    setPressureTcField(preferences.pressureTcField)
    setYearTcField(preferences.yearTcField)
  }, [user?.id])

  useEffect(() => {
    setPressureLoading(true)
    setPressureError('')
    api.get<any>(`/api/papers/stats/tc-pressure?tc_field=${encodeURIComponent(pressureTcField)}`)
      .then(data => setPressureData(Array.isArray(data) ? data : []))
      .catch(() => { setPressureData([]); setPressureError('Tc–Pressure 数据加载失败') })
      .finally(() => setPressureLoading(false))
  }, [pressureTcField])

  useEffect(() => {
    setYearLoading(true)
    setYearError('')
    api.get<any>(`/api/papers/stats/tc-year?tc_field=${encodeURIComponent(yearTcField)}`)
      .then(data => setYearData(Array.isArray(data) ? data : []))
      .catch(() => { setYearData([]); setYearError('Tc–Year 数据加载失败') })
      .finally(() => setYearLoading(false))
  }, [yearTcField])

  // ── Fetch paper detail when paperId changes ──
  useEffect(() => {
    if (!selectedPaperId) return
    setDetailLoading(true)
    setDetailError('')
    setPaperDetail(null)
    api.get<any>(`/api/papers/${selectedPaperId}`)
      .then(data => setPaperDetail(data))
      .catch(() => setDetailError('加载论文详情失败'))
      .finally(() => setDetailLoading(false))
  }, [selectedPaperId])

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
    return (Array.isArray(data) ? data : [])
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
        paperId: d.paper_id || undefined,
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
        paperId: it.paper_id || undefined,
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

  const renderTcFieldSelector = (value: TcField, onChange: (field: TcField) => void) => (
    <FormControl size="small" sx={{ minWidth: 220 }}>
      <InputLabel>Tc 字段</InputLabel>
      <Select value={value} label="Tc 字段" onChange={event => onChange(event.target.value as TcField)}>
        {TC_FIELDS.map(field => (
          <MenuItem key={field} value={field}>{TC_FIELD_LABELS[field]}</MenuItem>
        ))}
      </Select>
    </FormControl>
  )

  const changePressureTcField = (field: TcField) => {
    setPressureTcField(field)
    if (user) writeChartPreferences(user.id, { version: 1, pressureTcField: field, yearTcField })
  }

  const changeYearTcField = (field: TcField) => {
    setYearTcField(field)
    if (user) writeChartPreferences(user.id, { version: 1, pressureTcField, yearTcField: field })
  }

  const restoreDefaults = () => {
    if (user) clearChartPreferences(user.id)
    setPressureTcField(DEFAULT_CHART_PREFERENCES.pressureTcField)
    setYearTcField(DEFAULT_CHART_PREFERENCES.yearTcField)
  }

  const renderLeaderboard = (title: string, rows: ContributionRank[], unit: string) => {
    const maxCount = rows.length > 0 ? Math.max(...rows.map(row => row.contribution_count)) : 0
    return (
      <Card variant="outlined" sx={{ flex: { xs: '1 1 100%', md: 1 }, minWidth: { xs: 0, md: 280 } }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1.5 }}>{title}</Typography>
          {rows.length === 0 ? <Typography color="text.secondary">暂无贡献记录</Typography> : rows.map((row, index) => (
            <React.Fragment key={row.user_id}>
              <Box sx={{ py: 1 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                  <Typography sx={{ width: 28, flexShrink: 0, fontWeight: 800, color: row.rank <= 3 ? 'primary.main' : 'text.secondary' }}>{row.rank}</Typography>
                  <Avatar sx={{ width: 34, height: 34, fontSize: 15 }}>{row.avatar_text}</Avatar>
                  <Typography noWrap sx={{ flex: 1, minWidth: 0, fontWeight: 650 }}>{row.username}</Typography>
                  <Typography fontWeight={800} sx={{ flexShrink: 0 }}>{row.contribution_count} {unit}</Typography>
                </Box>
                <Box sx={{ ml: 7.75, mt: 0.75, height: 8, overflow: 'hidden', borderRadius: 999, bgcolor: 'action.hover' }}>
                  <Box
                    data-testid={`contribution-bar-${row.user_id}`}
                    sx={{
                      width: `${contributionBarWidth(row.contribution_count, maxCount)}%`,
                      height: '100%',
                      borderRadius: 'inherit',
                      bgcolor: row.rank <= 3 ? 'primary.main' : 'primary.light',
                    }}
                  />
                </Box>
              </Box>
              {index < rows.length - 1 && <Divider />}
            </React.Fragment>
          ))}
        </CardContent>
      </Card>
    )
  }

  // ═══════════════════════════════════════════════════════
  return (
    <Box>
      <Typography variant="overline">Community</Typography>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: { xs: 'flex-start', sm: 'center' }, gap: 2, mb: 2, flexDirection: { xs: 'column', sm: 'row' } }}>
        <Box>
          <Typography variant="h1">社区</Typography>
          <Typography color="text.secondary">公共数据，个人图表偏好仅保存在当前浏览器。</Typography>
        </Box>
        <Button variant="outlined" onClick={restoreDefaults}>恢复默认</Button>
      </Box>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2, flexWrap: 'wrap', mb: 2 }}>
            <Box>
              <Typography variant="h5" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}><EmojiEvents color="primary" />贡献排行榜</Typography>
              <Typography color="text.secondary">已有 {contributions?.participant_count ?? '—'} 位研究者参与数据库建设</Typography>
              {contributions?.generated_at && <Typography variant="caption" color="text.secondary">最后更新：{new Date(contributions.generated_at).toLocaleString()}</Typography>}
            </Box>
            <Button variant="outlined" startIcon={contributionsLoading ? <CircularProgress size={16} /> : <Refresh />}
              disabled={contributionsLoading} onClick={() => void loadContributions(true)}>刷新榜单</Button>
          </Box>
          {contributionsError && <Alert severity="warning" sx={{ mb: 2 }}>{contributionsError}</Alert>}
          {contributionsLoading && !contributions ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 5 }}><CircularProgress /></Box>
          ) : contributions && (
            <>
              {user && (
                <Box
                  data-testid="current-user-ranking"
                  sx={{ display: 'flex', alignItems: 'center', gap: 2, flexWrap: { xs: 'wrap', md: 'nowrap' }, p: 2, mb: 2, bgcolor: 'action.hover', borderRadius: 2 }}
                >
                  <Typography fontWeight={800} sx={{ flexShrink: 0 }}>我的排名</Typography>
                  <Chip label={`上传榜：${contributions.current_user?.upload ? `第 ${contributions.current_user.upload.rank} 名 · ${contributions.current_user.upload.contribution_count} 篇` : '暂无排名 · 0 篇'}`} />
                  <Chip label={`审核榜：${contributions.current_user?.review ? `第 ${contributions.current_user.review.rank} 名 · ${contributions.current_user.review.contribution_count} 次` : '暂无排名 · 0 次'}`} />
                </Box>
              )}
              <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                {renderLeaderboard('贡献上传榜 Top 20', contributions.upload_leaderboard, '篇')}
                {renderLeaderboard('贡献审核榜 Top 20', contributions.review_leaderboard, '次')}
              </Box>
            </>
          )}
        </CardContent>
      </Card>

      <Box sx={{ display: 'grid', gridTemplateColumns: { xs: 'minmax(0, 1fr)', lg: 'repeat(2, minmax(0, 1fr))' }, gap: 2.5, alignItems: 'start' }}>

      {/* ═══ Tc-Pressure Scatter ═══ */}
      <Card sx={{ minWidth: 0 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Tc-Pressure 分布
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {renderTcFieldSelector(pressureTcField, changePressureTcField)}
            {renderGroupSelector(chart1, setChart1)}
          </Box>
          <Box sx={{ mt: 1 }}>
            {pressureLoading ? <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}><CircularProgress /></Box>
            : pressureError ? <Alert severity="error">{pressureError}</Alert>
            : pressureData.length === 0 && !chart1.groupId ? <Alert severity="info">当前 Tc 字段暂无可公开数据，请切换字段。</Alert>
            : <ChartScatter
              title="Tc-Pressure 分布"
              data={chart1Data}
              xLabel="Pressure (GPa)"
              yLabel="Tc (K)"
              tcFieldLabel={TC_FIELD_LABELS[pressureTcField]}
              qualityFactorContours
              minHeight={390}
              visibleTypes={visibleTypes}
              showBackground={!chart1.groupId}
              onToggleType={toggleType}
              onPointClick={(p) => { if (p.paperId) setSelectedPaperId(p.paperId) }}
            />}
          </Box>
        </CardContent>
      </Card>

      {/* ═══ Tc-Year Scatter ═══ */}
      <Card sx={{ minWidth: 0 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Tc-Year 演变
          </Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
            {renderTcFieldSelector(yearTcField, changeYearTcField)}
            {renderGroupSelector(chart2, setChart2)}
          </Box>
          <Box sx={{ mt: 1 }}>
            {yearLoading ? <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}><CircularProgress /></Box>
            : yearError ? <Alert severity="error">{yearError}</Alert>
            : yearData.length === 0 && !chart2.groupId ? <Alert severity="info">当前 Tc 字段暂无可公开数据，请切换字段。</Alert>
            : <ChartScatter
              title="Tc-Year 演变"
              data={chart2Data}
              xLabel="Year"
              yLabel="Tc (K)"
              tcFieldLabel={TC_FIELD_LABELS[yearTcField]}
              minHeight={390}
              xDomain={[1900, 'auto']}
              visibleTypes={visibleTypes}
              showBackground={!chart2.groupId}
              onToggleType={toggleType}
              onPointClick={(p) => { if (p.paperId) setSelectedPaperId(p.paperId) }}
            />}
          </Box>
        </CardContent>
      </Card>
      </Box>

      {/* ═══ Paper Detail Drawer ═══ */}
      <Drawer
        anchor="right"
        open={!!selectedPaperId}
        onClose={() => { setSelectedPaperId(null); setPaperDetail(null); setDetailError('') }}
        PaperProps={{ sx: { width: { xs: '100%', sm: 520 } } }}
      >
        <Box sx={{ p: 3, height: '100%', overflow: 'auto' }}>
          {/* Header */}
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Typography variant="h6" fontWeight={700}>论文详情</Typography>
            <IconButton
              onClick={() => { setSelectedPaperId(null); setPaperDetail(null); setDetailError('') }}
            >
              <Close />
            </IconButton>
          </Box>

          {/* Loading */}
          {detailLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
              <CircularProgress />
            </Box>
          )}

          {/* Content */}
          {paperDetail && !detailLoading && (
            <>
              {/* 基础信息 */}
              <Box component="details" open sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden' }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 16, fontWeight: 800 }}>基础信息</Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                  <Box sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 1.5 }}>
                    <Box><Typography variant="caption" color="text.secondary">Formula</Typography>
                      <Typography fontWeight={600}>{paperDetail.key_properties?.[0]?.material || '-'}</Typography></Box>
                    <Box><Typography variant="caption" color="text.secondary">年份</Typography>
                      <Typography fontWeight={600}>{paperDetail.year || '-'}</Typography></Box>
                    <Box><Typography variant="caption" color="text.secondary">DOI</Typography>
                      <Typography fontWeight={600} noWrap>{paperDetail.doi || '-'}</Typography></Box>
                    <Box><Typography variant="caption" color="text.secondary">期刊</Typography>
                      <Typography fontWeight={600}>{paperDetail.journal || '-'}</Typography></Box>
                    <Box sx={{ gridColumn: '1/-1' }}><Typography variant="caption" color="text.secondary">论文标题</Typography>
                      <Typography fontWeight={600}>{paperDetail.title || '-'}</Typography></Box>
                    {paperDetail.summary && (
                      <Box sx={{ gridColumn: '1/-1' }}><Typography variant="caption" color="text.secondary">论文总结</Typography>
                        <Typography variant="body2" sx={{ lineHeight: 1.8 }}>{paperDetail.summary}</Typography></Box>
                    )}
                  </Box>
                  {paperDetail.doi && (
                    <Button size="small" variant="outlined" sx={{ mt: 1.5 }}
                      onClick={() => window.open(`https://doi.org/${paperDetail.doi}`, '_blank')}
                      endIcon={<OpenInNew />}>打开原文</Button>
                  )}
                </Box>
              </Box>

              {/* 关键物性 */}
              <Box component="details" open sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden' }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 16, fontWeight: 800 }}>关键物性</Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider', overflowX: 'auto' }}>
                  {Array.isArray(paperDetail.key_properties) && paperDetail.key_properties.length > 0 ? (
                    <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, mt: 1 }}>
                      <Box component="thead">
                        <Box component="tr">
                          {['材料', '物性', '数值', '条件', '备注'].map(h => (
                            <Box key={h} component="th" sx={{ p: '4px 8px', borderBottom: '2px solid', borderColor: 'divider', textAlign: 'left', color: 'text.secondary', fontSize: 11, whiteSpace: 'nowrap' }}>{h}</Box>
                          ))}
                        </Box>
                      </Box>
                      <Box component="tbody">
                        {paperDetail.key_properties.map((kp: any) => (
                          <Box component="tr" key={kp.id} sx={{ bgcolor: kp.is_primary ? '#eef2ff' : 'transparent' }}>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', fontWeight: 600 }}>{kp.material}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap' }}>
                              {kp.label}{kp.is_primary ? ' ★' : ''}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', fontWeight: 700, color: 'primary.main' }}>
                              {kp.value_min != null
                                ? (kp.value_min !== kp.value_max ? `${kp.value_min}–${kp.value_max}` : `${kp.value_max}`)
                                : (kp.value_raw || '-')}{kp.unit ? ` ${kp.unit}` : ''}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', color: 'text.secondary' }}>
                              {[kp.pressure_gpa != null ? `${kp.pressure_gpa} GPa` : null, kp.temperature_k != null ? `${kp.temperature_k} K` : null].filter(Boolean).join(' · ') || '-'}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', color: 'text.secondary', minWidth: 140 }}>
                              {[kp.name_note, kp.condition_note].filter(Boolean).join('；') || '-'}</Box>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>该论文暂无结构化物性数据</Typography>
                  )}
                </Box>
              </Box>

              {/* 研究方法与发现 */}
              <Box component="details" sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden' }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 16, fontWeight: 800 }}>研究方法与发现</Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                  <Box sx={{ display: 'grid', gap: 1.5, mt: 1 }}>
                    <Box>
                      <Typography variant="caption" color="text.secondary">研究方法</Typography>
                      <Box sx={{ display: 'flex', gap: 0.75, flexWrap: 'wrap', mt: 0.5 }}>
                        {(() => {
                          try {
                            const m = JSON.parse(paperDetail?.methodology || '[]')
                            return Array.isArray(m) && m.length
                              ? m.map((x: string) => <Chip key={x} label={x} size="small" variant="outlined" />)
                              : <Typography fontWeight={600}>-</Typography>
                          } catch { return <Typography fontWeight={600}>{paperDetail?.methodology || '-'}</Typography> }
                        })()}
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">核心发现</Typography>
                      <Typography fontWeight={600} sx={{ lineHeight: 1.8 }}>
                        {(() => {
                          try { return JSON.parse(paperDetail?.key_finding || '""') || '-' }
                          catch { return paperDetail?.key_finding || '-' }
                        })()}
                      </Typography>
                    </Box>
                  </Box>
                </Box>
              </Box>
            </>
          )}
        </Box>
      </Drawer>

      {/* Snackbar */}
      <Snackbar open={!!detailError} autoHideDuration={3000} onClose={() => setDetailError('')}>
        <Alert severity="error" variant="filled" onClose={() => setDetailError('')}>{detailError}</Alert>
      </Snackbar>

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
