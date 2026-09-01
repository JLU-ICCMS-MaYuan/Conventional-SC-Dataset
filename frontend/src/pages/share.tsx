import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Box, Typography, Card, CardContent, Button,
  Select, MenuItem, FormControl, InputLabel, IconButton,
  Drawer, CircularProgress, Chip, Alert, Snackbar, Avatar, Divider,
  Checkbox, ListItemText,
} from '@mui/material'
import {
  Close, OpenInNew, Refresh, EmojiEvents,
} from '@mui/icons-material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import {
  buildFamilyStyles, EMPTY_PRESSURE_DOMAIN, EMPTY_TC_DOMAIN, EMPTY_YEAR_DOMAIN,
  FamilyStyle, UNCLASSIFIED_FAMILY_ID,
} from '../lib/scatterConfig'
import { loadClassificationCatalogs } from '../lib/classifications'
import ChartScatter from '../components/ChartScatter'
import StructureViewer3D from '../components/StructureViewer3D'
import { collectPropertyRows, collectStructures, viewerFormat } from '../lib/paperDetailView'
import {
  clearChartPreferences, DEFAULT_CHART_PREFERENCES, FamilySelection, readChartPreferences,
  TC_FIELDS, TC_FIELD_LABELS, TcField, writeChartPreferences,
} from '../lib/chartPreferences'

// ── DataPoint interface (matches ChartScatter) ──
interface DataPoint {
  x: number
  y: number
  material: string
  familyId: number
  familyName: string
  articleType: string | null
  year: number | null
  doi: string | null
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
  account_status: 'active' | 'banned' | 'deactivated'
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

// ── 两图对齐用的固定尺寸 ──
//
// 错位的根因是控件显示文本的长度会影响布局高度：家族多选框文本变长后换行撑高控件，
// 把下方图表整体下推，左右两图坐标系就不在同一水平线。
//
// 「同步两图选择内容」的方案与两图独立选择的设计冲突，因此改为固定容器尺寸，
// 让内容长度变化被容器吸收。固定高度必须与固定宽度 + 超长折叠配套，
// 否则长文本在定高容器里会被裁切。
const TC_FIELD_SELECTOR_WIDTH = 210
const FAMILY_SELECTOR_WIDTH = 190
const FAMILY_SUMMARY_MAX_CHARS = 10
const CHART_CONTROLS_HEIGHT = 56

// ═══════════════════════════════════════════════════════
const SharePage: React.FC = () => {
  const navigate = useNavigate()
  const { user } = useAuth()

  // ── 材料家族目录：分类维度由 material_families 动态决定，含用户自建家族 ──
  const [legendFamilies, setLegendFamilies] = useState<FamilyStyle[]>([])
  const [familyStyles, setFamilyStyles] = useState<Map<number, FamilyStyle>>(new Map())
  // null = 全部可见（跟随目录）；数组 = 用户显式选过的子集
  const [pressureFamilies, setPressureFamilies] = useState<FamilySelection>(null)
  const [yearFamilies, setYearFamilies] = useState<FamilySelection>(null)

  // ── Raw data from APIs ──
  const [pressureData, setPressureData] = useState<any[]>([])
  const [yearData, setYearData] = useState<any[]>([])
  const [pressureTcField, setPressureTcField] = useState<TcField>(DEFAULT_CHART_PREFERENCES.pressureTcField)
  const [yearTcField, setYearTcField] = useState<TcField>(DEFAULT_CHART_PREFERENCES.yearTcField)
  const [pressureLoading, setPressureLoading] = useState(false)
  const [yearLoading, setYearLoading] = useState(false)
  const [pressureError, setPressureError] = useState('')
  const [yearError, setYearError] = useState('')

  const [contributions, setContributions] = useState<ContributionSnapshot | null>(null)
  const [contributionsLoading, setContributionsLoading] = useState(true)
  const [contributionsError, setContributionsError] = useState('')

  // ── Paper detail drawer ──
  const [selectedPaperId, setSelectedPaperId] = useState<number | null>(null)
  const [paperDetail, setPaperDetail] = useState<any>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

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
    setPressureFamilies(preferences.pressureFamilies)
    setYearFamilies(preferences.yearFamilies)
  }, [user?.id])

  // 目录不可用时仍要能画图：至少保留「其他」档位，图表退化为不分家族。
  useEffect(() => {
    loadClassificationCatalogs()
      .then(catalogs => {
        const families = catalogs.material_families ?? []
        const styles = buildFamilyStyles(families)
        setFamilyStyles(styles)
        setLegendFamilies(
          [...families.map(f => styles.get(f.id)!), styles.get(UNCLASSIFIED_FAMILY_ID)!]
            .filter(Boolean),
        )
      })
      .catch(() => {
        const styles = buildFamilyStyles([])
        setFamilyStyles(styles)
        setLegendFamilies([styles.get(UNCLASSIFIED_FAMILY_ID)!])
      })
  }, [])

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

  // Tc 与计算参数不在 key_properties 里，结构也不在 key_properties[].structure_text 里，
  // 两者都须跨材料状态汇总（见 lib/paperDetailView）
  const detailPropertyRows = collectPropertyRows(paperDetail)
  const detailStructures = collectStructures(paperDetail)

  // ── 家族可见集：null 展开为目录全集，因此新增家族默认可见 ──
  const allFamilyIds = legendFamilies.map(style => style.id)
  const resolveVisible = (selection: FamilySelection): Set<number> =>
    new Set(selection ?? allFamilyIds)

  const visiblePressureFamilies = resolveVisible(pressureFamilies)
  const visibleYearFamilies = resolveVisible(yearFamilies)

  // ── Build background DataPoints from API data ──
  const buildBgPoints = (data: any[]): DataPoint[] =>
    (Array.isArray(data) ? data : []).map(d => ({
      x: d.x,
      y: d.y,
      material: d.label || d.formula || '?',
      familyId: d.family_id ?? UNCLASSIFIED_FAMILY_ID,
      familyName: d.family_name || '其他',
      articleType: d.type === 'experimental' ? 'e' : 't',
      year: d.year || null,
      doi: d.doi || null,
      label: d.label || d.formula || '?',
      paperId: d.paper_id || undefined,
    }))

  // ── Chart data composition ──
  const chart1Data: DataPoint[] = buildBgPoints(pressureData)
  const chart2Data: DataPoint[] = buildBgPoints(yearData)

  const renderTcFieldSelector = (
    id: string,
    value: TcField,
    onChange: (field: TcField) => void,
  ) => (
    // labelId 让下拉有可访问名，否则屏幕阅读器只能读到当前值而不知这是什么字段
    <FormControl size="small" sx={{ width: TC_FIELD_SELECTOR_WIDTH, flexShrink: 0 }}>
      <InputLabel id={`${id}-label`}>Tc 字段</InputLabel>
      <Select
        labelId={`${id}-label`}
        value={value}
        label="Tc 字段"
        onChange={event => onChange(event.target.value as TcField)}
      >
        {TC_FIELDS.map(field => (
          <MenuItem key={field} value={field}>{TC_FIELD_LABELS[field]}</MenuItem>
        ))}
      </Select>
    </FormControl>
  )

  const persist = (overrides: Partial<Omit<typeof DEFAULT_CHART_PREFERENCES, 'version'>>) => {
    if (!user) return
    writeChartPreferences(user.id, {
      version: 2,
      pressureTcField, yearTcField, pressureFamilies, yearFamilies,
      ...overrides,
    })
  }

  const changePressureTcField = (field: TcField) => {
    setPressureTcField(field)
    persist({ pressureTcField: field })
  }

  const changeYearTcField = (field: TcField) => {
    setYearTcField(field)
    persist({ yearTcField: field })
  }

  // 全选时存回 null，让后续新增的家族继续自动可见。
  const normalizeSelection = (ids: number[]): FamilySelection =>
    ids.length === allFamilyIds.length ? null : ids

  const changePressureFamilies = (ids: number[]) => {
    const selection = normalizeSelection(ids)
    setPressureFamilies(selection)
    persist({ pressureFamilies: selection })
  }

  const changeYearFamilies = (ids: number[]) => {
    const selection = normalizeSelection(ids)
    setYearFamilies(selection)
    persist({ yearFamilies: selection })
  }

  // 图例点击与多选下拉共享同一份状态，两者天然同步。
  const toggleFamily = (
    current: Set<number>,
    apply: (ids: number[]) => void,
  ) => (familyId: number) => {
    const next = new Set(current)
    if (next.has(familyId)) next.delete(familyId)
    else next.add(familyId)
    apply(Array.from(next))
  }

  const restoreDefaults = () => {
    if (user) clearChartPreferences(user.id)
    setPressureTcField(DEFAULT_CHART_PREFERENCES.pressureTcField)
    setYearTcField(DEFAULT_CHART_PREFERENCES.yearTcField)
    setPressureFamilies(DEFAULT_CHART_PREFERENCES.pressureFamilies)
    setYearFamilies(DEFAULT_CHART_PREFERENCES.yearFamilies)
  }

  const renderFamilySelector = (
    id: string,
    label: string,
    visible: Set<number>,
    apply: (ids: number[]) => void,
  ) => (
    // 固定宽度而非 minWidth：MUI Select 的显示宽度由 renderValue 结果撑开，
    // 只设下限时选中项越多控件越宽，两图控件不等宽且会把图表推错位。
    <FormControl size="small" sx={{ width: FAMILY_SELECTOR_WIDTH, flexShrink: 0 }}>
      <InputLabel id={`${id}-label`}>{label}</InputLabel>
      <Select
        multiple
        // displayEmpty 是必需的：MUI 在值为空时会跳过 renderValue 直接渲染零宽空格，
        // 「未选择」提示就不会出现，用户看到的是一个空控件。
        displayEmpty
        labelId={`${id}-label`}
        value={legendFamilies.filter(style => visible.has(style.id)).map(style => style.id)}
        label={label}
        onChange={event => {
          const value = event.target.value as unknown as number[]
          apply(value.map(Number))
        }}
        renderValue={selected => renderFamilySummary(selected as number[])}
      >
        {legendFamilies.map(style => (
          <MenuItem key={style.id} value={style.id}>
            <Checkbox size="small" checked={visible.has(style.id)} />
            <Box component="span" sx={{ mr: 0.75, color: style.color }}>{style.icon}</Box>
            <ListItemText primary={style.name} />
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  )

  // 选中项名称拼接后常常超出固定宽度。超长时折叠为「已选 N 项」而非截断：
  // 截断会让用户无法得知选了几项，信息量更低。
  const renderFamilySummary = (ids: number[]): string => {
    if (legendFamilies.length > 0 && ids.length === legendFamilies.length) return '全部'
    if (ids.length === 0) return '未选择'
    const names = legendFamilies.filter(style => ids.includes(style.id)).map(style => style.name)
    const joined = names.join('、')
    return joined.length > FAMILY_SUMMARY_MAX_CHARS ? `已选 ${ids.length} 项` : joined
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
                  <Typography
                    noWrap
                    onClick={() => row.account_status !== 'deactivated' && navigate(`/users/${row.username}`)}
                    sx={{ flex: 1, minWidth: 0, fontWeight: 650, cursor: row.account_status === 'deactivated' ? 'default' : 'pointer', '&:hover': row.account_status === 'deactivated' ? undefined : { color: 'primary.main' } }}
                  >{row.username}{row.account_status === 'banned' ? ' · 已封禁' : ''}</Typography>
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
          {/* 定高且不换行：控件内容长度不得影响图表纵向位置（两图对齐） */}
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'nowrap', height: CHART_CONTROLS_HEIGHT, alignItems: 'center' }}>
            {renderTcFieldSelector('pressure-tc-field', pressureTcField, changePressureTcField)}
            {renderFamilySelector('pressure-families', '材料家族', visiblePressureFamilies, changePressureFamilies)}
          </Box>
          <Box sx={{ mt: 1 }}>
            {/* 空数据仍渲染坐标系与品质因子分区，只在图内提示无数据点 */}
            {pressureLoading ? <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}><CircularProgress /></Box>
            : pressureError ? <Alert severity="error">{pressureError}</Alert>
            : <ChartScatter
              data={chart1Data}
              xLabel="Pressure (GPa)"
              yLabel="Tc (K)"
              tcFieldLabel={TC_FIELD_LABELS[pressureTcField]}
              qualityFactorContours
              minHeight={390}
              xDomain={EMPTY_PRESSURE_DOMAIN}
              yDomain={EMPTY_TC_DOMAIN}
              familyStyles={familyStyles}
              legendFamilies={legendFamilies}
              visibleFamilies={visiblePressureFamilies}
              onToggleFamily={toggleFamily(visiblePressureFamilies, changePressureFamilies)}
              emptyHint="当前 Tc 字段暂无可公开数据点"
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
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'nowrap', height: CHART_CONTROLS_HEIGHT, alignItems: 'center' }}>
            {renderTcFieldSelector('year-tc-field', yearTcField, changeYearTcField)}
            {renderFamilySelector('year-families', '材料家族', visibleYearFamilies, changeYearFamilies)}
          </Box>
          <Box sx={{ mt: 1 }}>
            {/* 年份图不画品质因子分区：S 依赖压强，在年份轴上无物理意义 */}
            {yearLoading ? <Box sx={{ display: 'grid', placeItems: 'center', minHeight: 360 }}><CircularProgress /></Box>
            : yearError ? <Alert severity="error">{yearError}</Alert>
            : <ChartScatter
              data={chart2Data}
              xLabel="Year"
              yLabel="Tc (K)"
              tcFieldLabel={TC_FIELD_LABELS[yearTcField]}
              minHeight={390}
              temperatureBands
              xDomain={EMPTY_YEAR_DOMAIN}
              yDomain={EMPTY_TC_DOMAIN}
              familyStyles={familyStyles}
              legendFamilies={legendFamilies}
              visibleFamilies={visibleYearFamilies}
              onToggleFamily={toggleFamily(visibleYearFamilies, changeYearFamilies)}
              emptyHint="当前 Tc 字段暂无可公开数据点"
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
                        <Typography variant="body2" sx={{ fontSize: 12, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{paperDetail.summary}</Typography></Box>
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
                  {detailPropertyRows.length > 0 ? (
                    <Box component="table" sx={{ width: '100%', borderCollapse: 'collapse', fontSize: 12, mt: 1 }}>
                      <Box component="thead">
                        <Box component="tr">
                          {['材料', '物性', '数值', '条件', '备注'].map(h => (
                            <Box key={h} component="th" sx={{ p: '4px 8px', borderBottom: '2px solid', borderColor: 'divider', textAlign: 'left', color: 'text.secondary', fontSize: 11, whiteSpace: 'nowrap' }}>{h}</Box>
                          ))}
                        </Box>
                      </Box>
                      <Box component="tbody">
                        {detailPropertyRows.map(row => (
                          <Box component="tr" key={row.key}>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', fontWeight: 600 }}>{row.material}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap' }}>{row.label}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', fontWeight: 700, color: 'primary.main' }}>{row.value}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', whiteSpace: 'nowrap', color: 'text.secondary' }}>{row.condition}</Box>
                            <Box component="td" sx={{ p: '4px 8px', borderBottom: '1px solid', borderColor: 'divider', color: 'text.secondary', minWidth: 140 }}>{row.note}</Box>
                          </Box>
                        ))}
                      </Box>
                    </Box>
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>该论文暂无结构化物性数据</Typography>
                  )}
                </Box>
              </Box>

              {/* 结构预览：数据源为 material_states[].structures[]（structure_models 表）*/}
              <Box component="details" open sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 1.5, overflow: 'hidden' }}>
                <Box component="summary" sx={{ cursor: 'pointer', p: 2, fontSize: 16, fontWeight: 800 }}>结构预览</Box>
                <Box sx={{ px: 2, pb: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                  {detailStructures.length > 0 ? (
                    detailStructures.map((s, i) => (
                      <Box key={i} sx={{ mt: 1.5 }}>
                        <Typography variant="body2" fontWeight={700}>
                          {s.material}{s.name_note ? ` · ${s.name_note}` : ''}{s.pressure_gpa != null ? ` @ ${s.pressure_gpa} GPa` : ''}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          格式 {s.structure_format} · 拖拽旋转 · 滚轮缩放
                        </Typography>
                        <Box sx={{ mt: 1 }}>
                          <StructureViewer3D data={s.structure_text} format={viewerFormat(s.structure_format)} height={240} />
                        </Box>
                      </Box>
                    ))
                  ) : (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>该论文暂无结构数据</Typography>
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
                              : <Typography variant="body2">-</Typography>
                          } catch { return <Typography variant="body2">{paperDetail?.methodology || '-'}</Typography> }
                        })()}
                      </Box>
                    </Box>
                    <Box>
                      <Typography variant="caption" color="text.secondary">核心发现</Typography>
                      {/* 用户按「一个要点一行」录入，换行是内容结构，须保留。
                          字号字重与同区块的论文总结一致：正文用 body2(13px) 不加粗 */}
                      <Typography variant="body2" sx={{ fontSize: 12, lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>
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

    </Box>
  )
}

export default SharePage
