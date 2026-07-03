import React, { useEffect, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, Separator } from '@heroui/react'
import Chart from 'chart.js/auto'
import type { Chart as ChartInstance, ChartDataset, PointStyle } from 'chart.js'
import { requestJson } from '../lib/apiClient'

interface ChartPoint {
  label?: string
  year?: number
  x?: number
  y?: number
  type?: string
  sc_type?: string
}

interface NobelLaureate {
  name: string
  alt: string
  image: string
}

type ScatterDataset = ChartDataset<'scatter', Array<{ x: number; y: number; label?: string; year?: number; pressure?: number }>>

const laureates: NobelLaureate[] = [
  { name: 'Heike Kamerlingh Onnes', alt: 'Kamerlingh Onnes', image: 'Kamerlingh_portret.jpg' },
  { name: 'John Bardeen', alt: 'John Bardeen', image: 'Bardeen.jpg' },
  { name: 'Leon Cooper', alt: 'Leon Cooper', image: 'Laureate_Leon_Cooper.jpg' },
  { name: 'John Robert Schrieffer', alt: 'John Robert Schrieffer', image: 'John_Robert_Schrieffer.jpg' },
  { name: 'Ivar Giaever', alt: 'Ivar Giaever', image: 'Ivar_Giaever.jpg' },
  { name: 'Brian Josephson', alt: 'Brian Josephson', image: 'Brian_Josephson,_March_2004.jpg' },
  { name: 'Leo Esaki', alt: 'Leo Esaki', image: 'Leo_Esaki_1959.jpg' },
  {
    name: 'Georg Bednorz',
    alt: 'Georg Bednorz',
    image: 'Georg_Bednorz_speaking_at_the_groundbreaking_of_the_new_IBM_and_ETH_Zurich_Nanotech_Exploratory_Technology_Lab.jpg',
  },
  { name: 'Karl Muller', alt: 'Karl Muller', image: 'Karl_Alexander_Mueller.jpg' },
  { name: 'Alexei Abrikosov', alt: 'Alexei Abrikosov', image: 'AA_Abrikosov_ANL1.jpg' },
  { name: 'Vitaly Ginzburg', alt: 'Vitaly Ginzburg', image: 'Ginzburg_in_MSU_opaque.jpg' },
  {
    name: 'Anthony James Leggett',
    alt: 'Anthony James Leggett',
    image: 'Nobel_Laureate_Sir_Anthony_James_Leggett_in_2007.jpg',
  },
]

const chartColors = {
  cuprate: '#f28e8c',
  iron_based: '#f5b56b',
  nickel_based: '#c9b06f',
  hydride: '#279a9f',
  carbon: '#82b984',
  organic: '#b49ad6',
  others: '#9aa6a2',
  unknown: '#9aa6a2',
}

const legendDefs = [
  ['cuprate', 'Cuprate', chartColors.cuprate],
  ['iron_based', 'Iron-based', chartColors.iron_based],
  ['nickel_based', 'Nickel-based', chartColors.nickel_based],
  ['hydride', 'Hydride', chartColors.hydride],
  ['carbon', 'Carbon', chartColors.carbon],
  ['organic', 'Organic', chartColors.organic],
  ['others', 'Others', chartColors.others],
] as const

function formatSubscript(value?: string) {
  if (!value) return ''
  const map: Record<string, string> = {
    '0': '0',
    '1': '1',
    '2': '2',
    '3': '3',
    '4': '4',
    '5': '5',
    '6': '6',
    '7': '7',
    '8': '8',
    '9': '9',
    x: 'x',
    '(': '(',
    ')': ')',
    '[': '(',
    ']': ')',
    '-': '-',
    '+': '+',
  }
  return value.split('').map((char) => map[char] || char).join('')
}

function colorFor(point: ChartPoint) {
  return chartColors[point.sc_type as keyof typeof chartColors] || chartColors.unknown
}

function buildLegendDatasets(): ScatterDataset[] {
  return legendDefs.map(([id, label, color]) => ({
    id,
    label: `Legend: ${label}`,
    data: [],
    backgroundColor: color,
    pointStyle: 'rect' as PointStyle,
  }))
}

function generateSLine(factor: number) {
  const points: Array<{ x: number; y: number }> = []
  for (let pressure = 0; pressure <= 300; pressure += 10) {
    points.push({ x: pressure, y: factor * Math.sqrt(1521 + pressure ** 2) })
  }
  return points
}

function baseLegendOptions(filterSLine = false) {
  return {
    position: 'bottom' as const,
    labels: {
      color: '#666',
      usePointStyle: true,
      boxWidth: 10,
      font: { size: 10 },
      generateLabels: (chart: ChartInstance) => {
        const labels = Chart.defaults.plugins.legend.labels.generateLabels(chart)
        return labels
          .filter((item) => !filterSLine || !item.text.startsWith('s='))
          .map((item) => {
            if (item.text.startsWith('Legend: ')) item.text = item.text.replace('Legend: ', '')
            if (item.text === 'Experiment' || item.text === 'Theory') {
              item.fillStyle = '#6c757d'
              item.strokeStyle = '#6c757d'
            }
            return item
          })
      },
    },
  }
}

function createYearChart(canvas: HTMLCanvasElement) {
  return new Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: [
        {
          label: 'Experiment',
          data: [],
          borderColor: '#fff',
          borderWidth: 1,
          pointRadius: 4,
          pointStyle: 'circle',
          order: 0,
        },
        {
          label: 'Theory',
          data: [],
          borderColor: '#fff',
          borderWidth: 1,
          pointRadius: 5,
          pointStyle: 'triangle',
          order: 0,
        },
        ...buildLegendDatasets(),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 2,
      scales: {
        x: {
          type: 'linear',
          position: 'bottom',
          title: { display: true, text: 'Year' },
          min: 1900,
          max: 2040,
        },
        y: {
          title: { display: true, text: 'Tc (K)' },
          beginAtZero: true,
          max: 400,
        },
      },
      plugins: {
        legend: baseLegendOptions(),
        tooltip: {
          callbacks: {
            label: (context) => {
              const point = context.raw as { label?: string; y?: number; year?: number }
              return `${point.label}: ${point.y} K (${point.year})`
            },
          },
        },
      },
    },
    plugins: [
      {
        id: 'chartCustomizations',
        beforeDraw: (chart) => {
          const { ctx, chartArea, scales } = chart
          const yScale = scales.y
          if (!chartArea || !yScale) return
          ctx.save()
          const drawLine = (value: number, color: string, text: string) => {
            const y = yScale.getPixelForValue(value)
            if (y < chartArea.top || y > chartArea.bottom) return
            ctx.strokeStyle = color
            ctx.setLineDash([5, 5])
            ctx.beginPath()
            ctx.moveTo(chartArea.left, y)
            ctx.lineTo(chartArea.right, y)
            ctx.stroke()
            ctx.setLineDash([])
            ctx.fillStyle = color
            ctx.font = '10px Arial'
            ctx.fillText(text, chartArea.left + 5, y - 5)
          }
          drawLine(77, 'rgba(255, 0, 0, 0.5)', 'Liquid N2')
          drawLine(300, 'rgba(0, 0, 0, 0.3)', 'Room temperature')
          ctx.restore()
        },
        afterDatasetsDraw: (chart) => {
          if (window.innerWidth < 800) return
          const { ctx } = chart
          ctx.save()
          ctx.font = '9px Arial'
          ctx.fillStyle = '#666'
          chart.data.datasets.forEach((dataset, index) => {
            if (index > 1) return
            const meta = chart.getDatasetMeta(index)
            meta.data.forEach((element, pointIndex) => {
              const point = dataset.data[pointIndex] as { label?: string; pressure?: number } | undefined
              if (!point) return
              const text = `${formatSubscript(point.label)} (${point.pressure} GPa)`
              if (element.x > chart.chartArea.left && element.x < chart.chartArea.right) {
                ctx.fillText(text, element.x + 6, element.y - 4)
              }
            })
          })
          ctx.restore()
        },
      },
    ],
  }) as ChartInstance<'scatter'>
}

function createPressureChart(canvas: HTMLCanvasElement) {
  return new Chart(canvas, {
    type: 'scatter',
    data: {
      datasets: [
        { label: 's=1', data: generateSLine(1), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 1, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#f7f0f7', order: 1 },
        { label: 's=2', data: generateSLine(2), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 1, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#e3e0ee', order: 2 },
        { label: 's=3', data: generateSLine(3), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 1, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#c6cce3', order: 3 },
        { label: 's=4', data: generateSLine(4), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 1, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#a1bbda', order: 4 },
        { label: 's=5', data: generateSLine(5), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#73a9cf', order: 5 },
        { label: 's=6', data: generateSLine(6), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#3d93c2', order: 6 },
        { label: 's=7', data: generateSLine(7), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#1077b4', order: 7 },
        { label: 's=8', data: generateSLine(8), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#046198', order: 8 },
        { label: 's=9', data: generateSLine(9), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#03476f', order: 9 },
        { label: 's=10', data: generateSLine(10), borderColor: 'rgba(0,0,0,0.1)', borderWidth: 0, borderDash: [5, 5], showLine: true, pointRadius: 0, fill: 'origin', backgroundColor: '#02304d', order: 10 },
        {
          label: 'Experiment',
          data: [],
          borderColor: '#fff',
          borderWidth: 1,
          pointRadius: 4,
          pointStyle: 'circle',
        },
        {
          label: 'Theory',
          data: [],
          borderColor: '#fff',
          borderWidth: 1,
          pointRadius: 5,
          pointStyle: 'triangle',
        },
        ...buildLegendDatasets(),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 2,
      scales: {
        x: {
          type: 'linear',
          position: 'bottom',
          title: { display: true, text: 'Pressure (GPa)' },
          min: -0.01,
          max: 300,
        },
        y: {
          title: { display: true, text: 'Tc (K)' },
          min: 0,
          max: 350,
        },
      },
      plugins: {
        legend: baseLegendOptions(true),
        tooltip: {
          callbacks: {
            label: (context) => {
              const point = context.raw as { label?: string; x?: number; y?: number }
              if (!point.label) return undefined
              return `${point.label}: ${point.y} K @ ${point.x} GPa`
            },
          },
        },
      },
    },
    plugins: [
      {
        id: 'sLabelPlugin',
        afterDatasetsDraw: (chart) => {
          const { ctx, scales } = chart
          const xScale = scales.x
          const yScale = scales.y
          if (!xScale || !yScale) return

          ctx.save()
          ctx.font = 'bold 10px Arial'
          ctx.fillStyle = 'rgba(0,0,0,0.3)'
          ;[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].forEach((factor) => {
            let pressure = 280
            let tc = factor * Math.sqrt(1521 + pressure ** 2)
            if (tc > 330) {
              const value = (330 / factor) ** 2 - 1521
              pressure = value > 0 ? Math.sqrt(value) : 10
              tc = 335
            }
            const x = xScale.getPixelForValue(pressure)
            const y = yScale.getPixelForValue(tc)
            if (x > chart.chartArea.left && x < chart.chartArea.right && y > chart.chartArea.top && y < chart.chartArea.bottom) {
              if (factor <= 5) ctx.fillText(`s=${factor}`, x, y - 10)
            }
          })

          if (window.innerWidth >= 800) {
            ctx.font = '9px Arial'
            ctx.fillStyle = '#666'
            chart.data.datasets.forEach((dataset, index) => {
              if (index !== 10 && index !== 11) return
              const meta = chart.getDatasetMeta(index)
              meta.data.forEach((element, pointIndex) => {
                const point = dataset.data[pointIndex] as { label?: string; year?: number } | undefined
                if (!point) return
                const text = `${formatSubscript(point.label)} (${point.year})`
                if (element.x > chart.chartArea.left && element.x < chart.chartArea.right) {
                  ctx.fillText(text, element.x + 6, element.y - 4)
                }
              })
            })
          }
          ctx.restore()
        },
      },
    ],
  }) as ChartInstance<'scatter'>
}

function updateCharts(yearChart: ChartInstance<'scatter'>, pressureChart: ChartInstance<'scatter'>, points: ChartPoint[]) {
  const expData = points.filter((point) => point.type === 'experimental')
  const theoData = points.filter((point) => point.type === 'theoretical')

  const expDataYear = expData
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.y))
    .map((point) => ({ x: Number(point.year), y: Number(point.y), label: point.label, year: point.year, pressure: point.x }))
  const theoDataYear = theoData
    .filter((point) => Number.isFinite(point.year) && Number.isFinite(point.y))
    .map((point) => ({ x: Number(point.year), y: Number(point.y), label: point.label, year: point.year, pressure: point.x }))

  const expColors = expData.map(colorFor)
  const theoColors = theoData.map(colorFor)

  yearChart.data.datasets[0].data = expDataYear
  yearChart.data.datasets[0].backgroundColor = expColors
  yearChart.data.datasets[0].pointBackgroundColor = expColors
  yearChart.data.datasets[1].data = theoDataYear
  yearChart.data.datasets[1].backgroundColor = theoColors
  yearChart.data.datasets[1].pointBackgroundColor = theoColors
  yearChart.update()

  pressureChart.data.datasets[10].data = expData.map((point) => ({
    x: Number(point.x),
    y: Number(point.y),
    label: point.label,
    year: point.year,
  }))
  pressureChart.data.datasets[10].backgroundColor = expColors
  pressureChart.data.datasets[10].pointBackgroundColor = expColors
  pressureChart.data.datasets[11].data = theoData.map((point) => ({
    x: Number(point.x),
    y: Number(point.y),
    label: point.label,
    year: point.year,
  }))
  pressureChart.data.datasets[11].backgroundColor = theoColors
  pressureChart.data.datasets[11].pointBackgroundColor = theoColors
  pressureChart.update()
}

const HomePage: React.FC = () => {
  const [points, setPoints] = useState<ChartPoint[]>([])
  const [error, setError] = useState('')
  const yearCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const pressureCanvasRef = useRef<HTMLCanvasElement | null>(null)
  const yearChartRef = useRef<ChartInstance<'scatter'> | null>(null)
  const pressureChartRef = useRef<ChartInstance<'scatter'> | null>(null)

  useEffect(() => {
    requestJson<ChartPoint[]>('/api/papers/stats/chart-data')
      .then((data) => setPoints(Array.isArray(data) ? data : []))
      .catch((err) => setError(err.message))
  }, [])

  useEffect(() => {
    if (!yearCanvasRef.current || !pressureCanvasRef.current) return
    yearChartRef.current = createYearChart(yearCanvasRef.current)
    pressureChartRef.current = createPressureChart(pressureCanvasRef.current)

    return () => {
      yearChartRef.current?.destroy()
      pressureChartRef.current?.destroy()
      yearChartRef.current = null
      pressureChartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (!yearChartRef.current || !pressureChartRef.current) return
    updateCharts(yearChartRef.current, pressureChartRef.current, points)
  }, [points])

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="page-kicker">SC Hotspot</p>
          <h1 className="page-title">超导热点</h1>
        </div>
        <p className="muted">Tc-year、Tc-pressure 与超导诺奖学者。</p>
      </header>

      {error && <div className="status-message error">{error}</div>}

      <div className="stack-lg">
        <Card>
          <CardHeader>
            <h2 className="section-title">超导临界温度 (Tc) 历史演变</h2>
          </CardHeader>
          <Separator />
          <CardContent>
            <div className="chart-panel">
              <canvas ref={yearCanvasRef} aria-label="超导临界温度历史演变图" />
              {points.length === 0 && !error && <div className="chart-empty">暂无图表数据</div>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="section-title">数据库实时 P-Tc 分布</h2>
          </CardHeader>
          <Separator />
          <CardContent>
            <div className="chart-panel">
              <canvas ref={pressureCanvasRef} aria-label="数据库实时 P-Tc 分布图" />
              {points.length === 0 && !error && <div className="chart-empty">暂无图表数据</div>}
            </div>
          </CardContent>
        </Card>

        <section className="nobel-section" aria-labelledby="nobel-title">
          <div>
            <h2 id="nobel-title" className="section-title">超导诺奖学者</h2>
            <p className="section-subtitle">与超导研究历史密切相关的 Nobel laureates。</p>
          </div>
          <div className="nobel-grid">
            {laureates.map((item) => (
              <figure className="nobel-card" key={item.name}>
                <img src={`/img/nobel/${item.image}`} title={item.name} alt={item.alt} loading="lazy" />
                <figcaption>{item.name}</figcaption>
              </figure>
            ))}
          </div>
        </section>
      </div>
    </section>
  )
}

export default HomePage
