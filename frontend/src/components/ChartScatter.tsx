import React from 'react'
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ZAxis, ReferenceLine, LabelList,
} from 'recharts'
import { Box, Typography } from '@mui/material'
import {
  SC_TYPE_CONFIG, EXP_COLOR, THEORY_COLOR,
  BACKGROUND_OPACITY,
} from '../lib/scatterConfig'

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

interface Props {
  title: string
  data: DataPoint[]
  xLabel: string
  yLabel: string
  xDomain?: [number, number | 'auto']
  yDomain?: [number, number | 'auto']
  visibleTypes: Set<string>
  showBackground: boolean
  onToggleType: (scType: string) => void
  tooltipFormatter?: (point: DataPoint) => React.ReactNode
  onPointClick?: (point: DataPoint) => void
  tcFieldLabel?: string
  qualityFactorContours?: boolean
  minHeight?: number
}

const CustomTooltip: React.FC<{ active?: boolean; payload?: any[]; xLabel: string; tooltipFormatter?: (point: DataPoint) => React.ReactNode }> = ({ active, payload, xLabel, tooltipFormatter }) => {
  if (!active || !payload?.[0]?.payload) return null
  const d = payload[0].payload as DataPoint
  if (tooltipFormatter) return <>{tooltipFormatter(d)}</>
  return (
    <Box sx={{ bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', borderRadius: 1, p: 1, fontSize: 12, minWidth: 160 }}>
      <Typography variant="body2" fontWeight={700}>{d.material}</Typography>
      <Typography variant="caption" color="text.secondary">Tc: {d.y} K · {xLabel}: {d.x}</Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
        数据类型：{d.articleType === 'e' ? '实验' : '计算'}
      </Typography>
      {d.year && <Typography variant="caption" color="text.secondary"> · {d.year}</Typography>}
      {d.doi && <Typography variant="caption" color="text.secondary" noWrap sx={{ display: 'block' }}>{d.doi}</Typography>}
    </Box>
  )
}

const SHAPE_MAP: Record<string, 'triangle' | 'square' | 'diamond' | 'circle' | 'wye' | 'cross'> = {
  hydride: 'triangle',
  cuprate: 'square',
  iron_based: 'diamond',
  nickel_based: 'circle',
  carbon: 'wye',
  organic: 'cross',
  others: 'diamond',
}

const SHAPE_ICONS: Record<string, string> = {
  hydride: '▲', cuprate: '■', iron_based: '◆', nickel_based: '●',
  carbon: '▼', organic: '⬢', others: '✚',
}

const ChartScatter: React.FC<Props> = ({
  title, data, xLabel, yLabel, xDomain, yDomain,
  visibleTypes, showBackground, onToggleType,
  tooltipFormatter, onPointClick,
  tcFieldLabel, qualityFactorContours = false, minHeight = 320,
}) => {
  const scTypes = Object.keys(SC_TYPE_CONFIG)

  // Build series arrays: one Scatter per (scType × articleType) for group points
  const visibleData = data.filter(d => visibleTypes.has(d.scType))
  const bgPoints = visibleData.filter(d => !d.isInGroup)
  const groupPoints = visibleData.filter(d => d.isInGroup)

  // Group points by (scType, articleType) → one Scatter per combo
  const groupSeries = scTypes.flatMap(st => {
    const typed = groupPoints.filter(p => p.scType === st)
    const exp = typed.filter(p => p.articleType === 'e')
    const th = typed.filter(p => p.articleType !== 'e')
    return [
      ...(exp.length > 0 ? [{ key: `${st}-exp`, shape: SHAPE_MAP[st], fill: EXP_COLOR, stroke: EXP_COLOR, fillOpacity: 1, data: exp }] : []),
      ...(th.length > 0 ? [{ key: `${st}-th`, shape: SHAPE_MAP[st], fill: '#fff', stroke: THEORY_COLOR, fillOpacity: 1, data: th }] : []),
    ]
  })

  // Background points by (scType, articleType) — 红/蓝半透明
  const bgSeries = scTypes.flatMap(st => {
    const typed = bgPoints.filter(p => p.scType === st)
    const exp = typed.filter(p => p.articleType === 'e')
    const th = typed.filter(p => p.articleType !== 'e')
    return [
      ...(exp.length > 0 ? [{ key: `bg-${st}-exp`, shape: SHAPE_MAP[st], fill: EXP_COLOR, stroke: EXP_COLOR, fillOpacity: 1, data: exp }] : []),
      ...(th.length > 0 ? [{ key: `bg-${st}-th`, shape: SHAPE_MAP[st], fill: '#fff', stroke: THEORY_COLOR, fillOpacity: 1, data: th }] : []),
    ]
  })

  const maxPressure = Math.max(400, ...visibleData.map(point => point.x).filter(Number.isFinite))
  const maxTc = Math.max(300, ...visibleData.map(point => point.y).filter(Number.isFinite))
  const contourLevels = [0.2, 0.5, 1, 2, 3]
  const contours = qualityFactorContours
    ? contourLevels.map(s => ({
      s,
      points: Array.from({ length: 81 }, (_, index) => {
        const x = maxPressure * index / 80
        return { x, y: s * Math.sqrt(39 ** 2 + x ** 2) }
      }).filter(point => point.y <= maxTc * 1.05).map((point, index, points) => ({
        ...point,
        sLabel: index === points.length - 1 ? `S=${s}` : '',
      })),
    })).filter(contour => contour.points.length > 1)
    : []

  return (
    <Box>
      {tcFieldLabel && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          当前纵轴：{tcFieldLabel}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={minHeight}>
        <ScatterChart margin={{ top: 10, right: 10, bottom: 30, left: 0 }}
          onClick={(e: any) => {
            if (e?.activePayload?.[0]?.payload) {
              onPointClick?.(e.activePayload[0].payload as DataPoint)
            }
          }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" dataKey="x" domain={xDomain || [0, 'auto']}
            label={{ value: xLabel, position: 'bottom', offset: -5 }} />
          <YAxis type="number" dataKey="y" domain={yDomain || [0, 'auto']}
            label={{ value: yLabel, angle: -90, position: 'insideLeft' }} />
          <ZAxis range={[60, 60]} />
          <Tooltip content={<CustomTooltip xLabel={xLabel} tooltipFormatter={tooltipFormatter} />} />

          {qualityFactorContours && (
            <>
              <ReferenceLine y={77} stroke="#d81b60" strokeDasharray="5 4" label={{ value: '液氮 77 K', position: 'insideTopRight', fill: '#ad1457' }} />
              <ReferenceLine y={300} stroke="#d81b60" strokeDasharray="5 4" label={{ value: '室温 300 K', position: 'insideTopRight', fill: '#ad1457' }} />
              {contours.map(contour => (
                <Scatter key={`quality-${contour.s}`} name={`S=${contour.s}`} data={contour.points}
                  line={{ stroke: '#4f6f52', strokeWidth: 1, strokeDasharray: '4 4' }}
                  shape={() => <g />} isAnimationActive={false} legendType="none">
                  <LabelList dataKey="sLabel" position="right" fill="#4f6f52" fontSize={11} />
                </Scatter>
              ))}
            </>
          )}

          {/* 背景点（红/蓝半透明） */}
          {showBackground && bgSeries.map(s => (
            <Scatter key={s.key} name={s.key} data={s.data}
              fill={s.fill} opacity={BACKGROUND_OPACITY}
              stroke={s.stroke} fillOpacity={s.fillOpacity} shape={s.shape} />
          ))}

          {/* 组合内点：实验红 / 理论蓝 */}
          {groupSeries.map(s => (
            <Scatter key={s.key} name={s.key} data={s.data}
              fill={s.fill} stroke={s.stroke} fillOpacity={s.fillOpacity} opacity={0.9} shape={s.shape} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>

      {/* 图例 — 同一行，无边框，居中 */}
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 1.5, flexWrap: 'wrap', mt: 1, fontSize: 13 }}>
        {scTypes.map(st => {
          const cfg = SC_TYPE_CONFIG[st]
          const isVisible = visibleTypes.has(st)
          return (
            <Box
              key={st}
              onClick={() => onToggleType(st)}
              sx={{
                display: 'flex', alignItems: 'center', gap: 0.5,
                cursor: 'pointer', opacity: isVisible ? 1 : 0.35,
                userSelect: 'none',
              }}
            >
              <Box component="span" sx={{ fontSize: 14, lineHeight: 1 }}>{SHAPE_ICONS[st]}</Box>
              <Typography variant="body2" fontSize="inherit">{cfg.label}</Typography>
            </Box>
          )
        })}
        <Box sx={{ width: 1, display: 'flex', justifyContent: 'center', gap: 1.5, mt: 0.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box component="span" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: EXP_COLOR, display: 'inline-block' }} />
            <Typography variant="body2" fontSize="inherit">实验</Typography>
          </Box>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <Box component="span" sx={{ width: 10, height: 10, borderRadius: '50%', bgcolor: '#fff', border: `2px solid ${THEORY_COLOR}`, display: 'inline-block' }} />
            <Typography variant="body2" fontSize="inherit">计算</Typography>
          </Box>
        </Box>
      </Box>
    </Box>
  )
}

export default ChartScatter
