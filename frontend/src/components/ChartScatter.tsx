import React from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ZAxis, ReferenceLine, LabelList, Customized,
} from 'recharts'
import { Box, Typography } from '@mui/material'
import { useLanguage } from '../context/LanguageContext'
import {
  FamilyStyle, familyStyleOf,
  QUALITY_FACTOR_BAND_COLORS, QUALITY_FACTOR_BAND_OPACITY,
  QUALITY_FACTOR_LEVELS, qualityFactorTc,
  TEMPERATURE_BAND_OPACITY, TEMPERATURE_HIGH_COLOR,
  TEMPERATURE_LOW_COLOR, TEMPERATURE_MID_COLOR,
} from '../lib/scatterConfig'

// 图例区定高：家族项数随可见性变化会改变行数，进而把两张卡片的底边推错位。
// 定高让行数变化被容器吸收（与控件区定高同理，见 share.tsx 的 CHART_CONTROLS_HEIGHT）。
const LEGEND_AREA_HEIGHT = 92

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

interface Props {
  data: DataPoint[]
  xLabel: string
  yLabel: string
  xDomain: [number, number | 'auto']
  yDomain: [number, number | 'auto']
  familyStyles: Map<number, FamilyStyle>
  legendFamilies: FamilyStyle[]
  visibleFamilies: Set<number>
  onToggleFamily: (familyId: number) => void
  tooltipFormatter?: (point: DataPoint) => React.ReactNode
  onPointClick?: (point: DataPoint) => void
  tcFieldLabel?: string
  qualityFactorContours?: boolean
  temperatureBands?: boolean
  referenceLines?: boolean
  emptyHint?: string
  minHeight?: number
}

const CustomTooltip: React.FC<{ active?: boolean; payload?: any[]; xLabel: string; tooltipFormatter?: (point: DataPoint) => React.ReactNode }> = ({ active, payload, xLabel, tooltipFormatter }) => {
  const { t } = useLanguage()
  if (!active || !payload?.[0]?.payload) return null
  const d = payload[0].payload as DataPoint
  if (!d.material) return null
  if (tooltipFormatter) return <>{tooltipFormatter(d)}</>
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1, fontSize: 12, minWidth: 160 }}>
      <Typography variant="body2" fontWeight={700}>{d.material}</Typography>
      <Typography variant="caption" color="text.secondary">Tc: {d.y} K · {xLabel}: {d.x}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {t('share.familyLabel', { name: d.familyName })}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        {t('share.dataTypeLabel', { type: d.articleType === 'e' ? t('share.typeExperimental') : t('share.typeComputed') })}
      </Typography>
      {d.year && <Typography variant="caption" color="text.secondary"> · {d.year}</Typography>}
      {d.doi && <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>{d.doi}</Typography>}
    </Box>
  )
}

// 品质因子色带。ReferenceArea 只能画轴对齐矩形，跟不了 Tc = S×sqrt(39²+P²) 这条曲线，
// 所以用 Customized 拿到 recharts 内部的比例尺，直接在数据空间画多边形。
interface QualityBandsProps {
  xAxisMap?: Record<string, any>
  yAxisMap?: Record<string, any>
}

const QualityFactorBands: React.FC<QualityBandsProps> = ({ xAxisMap, yAxisMap }) => {
  const xAxis = xAxisMap && Object.values(xAxisMap)[0]
  const yAxis = yAxisMap && Object.values(yAxisMap)[0]
  if (!xAxis?.scale || !yAxis?.scale) return null

  const [xMin, xMax] = xAxis.scale.domain() as [number, number]
  const [yMin, yMax] = yAxis.scale.domain() as [number, number]
  if (![xMin, xMax, yMin, yMax].every(Number.isFinite) || xMax <= xMin || yMax <= yMin) return null

  const SAMPLES = 64
  const pressures = Array.from(
    { length: SAMPLES + 1 },
    (_, index) => xMin + (xMax - xMin) * index / SAMPLES,
  )
  const clampY = (value: number) => Math.min(yMax, Math.max(yMin, value))
  const px = (value: number) => xAxis.scale(value)
  const py = (value: number) => yAxis.scale(clampY(value))

  // 每条边界曲线：最低档下方是第 0 个色带，最高档上方是最后一个色带。
  const boundaries: Array<(pressure: number) => number> = [
    () => yMin,
    ...QUALITY_FACTOR_LEVELS.map(s => (pressure: number) => qualityFactorTc(s, pressure)),
    () => yMax,
  ]

  const bands = boundaries.slice(0, -1).map((lower, index) => {
    const upper = boundaries[index + 1]
    const lowerEdge = pressures.map(pressure => `${px(pressure)},${py(lower(pressure))}`)
    const upperEdge = [...pressures].reverse().map(pressure => `${px(pressure)},${py(upper(pressure))}`)
    return {
      key: `band-${index}`,
      points: [...lowerEdge, ...upperEdge].join(' '),
      fill: QUALITY_FACTOR_BAND_COLORS[index % QUALITY_FACTOR_BAND_COLORS.length],
    }
  })

  return (
    <g aria-hidden="true">
      {bands.map(band => (
        <polygon key={band.key} points={band.points}
          fill={band.fill} fillOpacity={QUALITY_FACTOR_BAND_OPACITY} stroke="none" />
      ))}
    </g>
  )
}

// Tc-Year 的温度背景。分区边界只依赖 Tc（水平线），所以用单个矩形沿 Y 轴渐变即可，
// 不必像品质因子那样逐段采样——后者的边界是 Tc = S×sqrt(39²+P²) 曲线。
const TemperatureBands: React.FC<QualityBandsProps> = ({ xAxisMap, yAxisMap }) => {
  const xAxis = xAxisMap && Object.values(xAxisMap)[0]
  const yAxis = yAxisMap && Object.values(yAxisMap)[0]
  if (!xAxis?.scale || !yAxis?.scale) return null

  const [xMin, xMax] = xAxis.scale.domain() as [number, number]
  const [yMin, yMax] = yAxis.scale.domain() as [number, number]
  if (![xMin, xMax, yMin, yMax].every(Number.isFinite)) return null

  const left = xAxis.scale(xMin)
  const right = xAxis.scale(xMax)
  const top = yAxis.scale(yMax)
  const bottom = yAxis.scale(yMin)
  const width = Math.abs(right - left)
  const height = Math.abs(bottom - top)
  if (width <= 0 || height <= 0) return null

  return (
    <g aria-hidden="true">
      <defs>
        {/* y1=0 是矩形顶边（高温），y2=1 是底边（低温）；中段过渡色避免蓝红直接对撞 */}
        <linearGradient id="tc-temperature-gradient" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={TEMPERATURE_HIGH_COLOR} />
          <stop offset="50%" stopColor={TEMPERATURE_MID_COLOR} />
          <stop offset="100%" stopColor={TEMPERATURE_LOW_COLOR} />
        </linearGradient>
      </defs>
      <rect
        x={Math.min(left, right)} y={Math.min(top, bottom)}
        width={width} height={height}
        fill="url(#tc-temperature-gradient)"
        fillOpacity={TEMPERATURE_BAND_OPACITY}
        stroke="none"
      />
    </g>
  )
}

const ChartScatter: React.FC<Props> = ({
  data, xLabel, yLabel, xDomain, yDomain,
  familyStyles, legendFamilies, visibleFamilies, onToggleFamily,
  tooltipFormatter, onPointClick,
  tcFieldLabel, qualityFactorContours = false, temperatureBands = false,
  referenceLines = true,
  emptyHint, minHeight = 320,
}) => {
  const { t } = useLanguage()
  const visibleData = data.filter(d => visibleFamilies.has(d.familyId))

  // 每个 (家族 × 实验/计算) 组合一条 Scatter：家族定形状与描边色，实验/计算定实心或空心。
  //
  // 曾按「组合内点 / 背景点」分成两组样式（后者半透明），但社区页的组合入口已移除，
  // 不再产生组合点，两条分支恒等价，故收敛为单一前景样式。
  const familyIds = Array.from(new Set(visibleData.map(p => p.familyId)))
  const series = familyIds.flatMap(familyId => {
    const style = familyStyleOf(familyStyles, familyId)
    const typed = visibleData.filter(p => p.familyId === familyId)
    const exp = typed.filter(p => p.articleType === 'e')
    const th = typed.filter(p => p.articleType !== 'e')
    return [
      ...(exp.length > 0 ? [{
        key: `${familyId}-exp`, shape: style.symbol,
        fill: style.color, stroke: style.color, data: exp,
      }] : []),
      ...(th.length > 0 ? [{
        key: `${familyId}-th`, shape: style.symbol,
        fill: '#fff', stroke: style.color, data: th,
      }] : []),
    ]
  })

  // 等值线覆盖整个横轴显示域，因此空数据时也能画满背景。
  const xUpper = typeof xDomain[1] === 'number' ? xDomain[1] : Math.max(400, ...visibleData.map(p => p.x).filter(Number.isFinite))
  const yUpper = typeof yDomain[1] === 'number' ? yDomain[1] : Math.max(300, ...visibleData.map(p => p.y).filter(Number.isFinite))
  const contours = qualityFactorContours
    ? QUALITY_FACTOR_LEVELS.map(s => ({
      s,
      points: Array.from({ length: 81 }, (_, index) => {
        const x = xDomain[0] + (xUpper - xDomain[0]) * index / 80
        return { x, y: qualityFactorTc(s, x) }
      }).filter(point => point.y <= yUpper * 1.05).map((point, index, points) => ({
        ...point,
        sLabel: index === points.length - 1 ? `S=${s}` : '',
      })),
    })).filter(contour => contour.points.length > 1)
    : []

  return (
    <Box>
      {tcFieldLabel && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          {t('share.yAxisCaption', { field: tcFieldLabel })}
        </Typography>
      )}
      <Box sx={{ position: 'relative' }}>
        <ResponsiveContainer width="100%" height={minHeight}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 30, left: 0 }}
            onClick={(e: any) => {
              if (e?.activePayload?.[0]?.payload?.material) {
                onPointClick?.(e.activePayload[0].payload as DataPoint)
              }
            }}>
            {/* 分区在网格之下，避免色带盖住刻度线 */}
            {qualityFactorContours && <Customized component={QualityFactorBands} />}
            {temperatureBands && <Customized component={TemperatureBands} />}
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" dataKey="x" domain={xDomain} allowDataOverflow
              label={{ value: xLabel, position: 'bottom', offset: -5 }} />
            <YAxis type="number" dataKey="y" domain={yDomain} allowDataOverflow
              label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
            <ZAxis range={[60, 60]} />
            <Tooltip content={<CustomTooltip xLabel={xLabel} tooltipFormatter={tooltipFormatter} />} />

            {/* 不能用 Fragment 包裹：recharts 按子元素类型分派渲染，
                包在 Fragment 里的 ReferenceLine 不会被识别，参考线会静默消失。 */}
            {referenceLines && <ReferenceLine y={77} stroke="#d81b60" strokeDasharray="5 4" label={{ value: t('share.liquidNitrogen', { temp: 77 }), position: 'insideTopRight', fill: '#ad1457' }} />}
            {referenceLines && <ReferenceLine y={300} stroke="#d81b60" strokeDasharray="5 4" label={{ value: t('share.roomTemperature', { temp: 300 }), position: 'insideTopRight', fill: '#ad1457' }} />}
            {contours.map(contour => (
              <Scatter key={`quality-${contour.s}`} name={`S=${contour.s}`} data={contour.points}
                line={{ stroke: '#4f6f52', strokeWidth: 1, strokeDasharray: '4 4' }}
                shape={() => <g />} isAnimationActive={false} legendType="none">
                <LabelList dataKey="sLabel" position="right" fill="#4f6f52" fontSize={11} />
              </Scatter>
            ))}

            {series.map(s => (
              <Scatter key={s.key} name={s.key} data={s.data}
                fill={s.fill} stroke={s.stroke} opacity={0.9} shape={s.shape} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
        {/* 空数据不隐藏坐标系与分区背景，只在图内提示 */}
        {visibleData.length === 0 && (
          <Typography
            variant="body2" color="text.secondary"
            sx={{
              position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
              pointerEvents: 'none', fontWeight: 600,
            }}
          >
            {emptyHint ?? t('share.emptyChartHint')}
          </Typography>
        )}
      </Box>

      {/* 图例 — 家族可点击切换可见性。
          定高：家族项数变化会改变行数，否则两张卡片底边错位。 */}
      <Box sx={{
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        gap: 1.5, flexWrap: 'wrap', mt: 1, fontSize: 13,
        height: LEGEND_AREA_HEIGHT, overflow: 'hidden',
      }}>
        {legendFamilies.map(style => {
          const isVisible = visibleFamilies.has(style.id)
          return (
            <Box
              key={style.id}
              role="button"
              aria-pressed={isVisible}
              onClick={() => onToggleFamily(style.id)}
              sx={{
                display: 'flex', alignItems: 'center', gap: 0.5,
                cursor: 'pointer', opacity: isVisible ? 1 : 0.35,
                userSelect: 'none',
              }}
            >
              <Box component="span" sx={{ fontSize: 14, lineHeight: 1, color: style.color }}>{style.icon}</Box>
              <Typography variant="body2" fontSize="inherit">{style.name}</Typography>
            </Box>
          )
        })}
        <Box sx={{ width: 1, display: 'flex', justifyContent: 'center', gap: 1.5, mt: 0.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box component="span" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: 'text.primary', display: 'inline-block' }} />
            <Typography variant="body2" fontSize="inherit">{t('share.legendExperimental')}</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box component="span" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#fff', border: '2px solid', borderColor: 'text.primary', display: 'inline-block' }} />
            <Typography variant="body2" fontSize="inherit">{t('share.legendComputed')}</Typography>
          </Box>
        </Box>
      </Box>

      {/* 背景色图例。两图背景语义不同，各自说明，避免把「暖色」误读成同一含义。 */}
      {qualityFactorContours && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, flexWrap: 'wrap', mt: 1, fontSize: 12 }}>
          <Typography variant="caption" color="text.secondary">{t('share.qualityFactorLegend')}</Typography>
          {['<0.2', '0.2–0.5', '0.5–1', '1–2', '2–3', '>3'].map((label, index) => (
            <Box key={label} sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <Box component="span" sx={{
                width: 14, height: 10, display: 'inline-block',
                bgcolor: QUALITY_FACTOR_BAND_COLORS[index],
                border: '1px solid', borderColor: 'divider',
              }} />
              <Typography variant="caption" color="text.secondary">{label}</Typography>
            </Box>
          ))}
        </Box>
      )}

      {temperatureBands && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1, flexWrap: 'wrap', mt: 1, fontSize: 12 }}>
          <Typography variant="caption" color="text.secondary">{t('share.temperatureLegend')}</Typography>
          <Typography variant="caption" color="text.secondary">{t('share.temperatureLow')}</Typography>
          <Box
            data-testid="temperature-legend-bar"
            component="span"
            sx={{
              width: 96, height: 10, display: 'inline-block',
              border: '1px solid', borderColor: 'divider',
              // 图例色条方向与图上一致：左（低温蓝）→ 右（高温红）
              background: `linear-gradient(to right, ${TEMPERATURE_LOW_COLOR}, ${TEMPERATURE_MID_COLOR}, ${TEMPERATURE_HIGH_COLOR})`,
            }}
          />
          <Typography variant="caption" color="text.secondary">{t('share.temperatureHigh')}</Typography>
        </Box>
      )}
    </Box>
  )
}

export default ChartScatter
