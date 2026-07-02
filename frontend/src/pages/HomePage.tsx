import React, { useEffect, useState } from 'react'
import { requestJson } from '../lib/apiClient'

interface ChartPoint {
  label?: string
  year?: number
  x?: number
  y?: number
  type?: string
  sc_type?: string
}

const HomePage: React.FC = () => {
  const [points, setPoints] = useState<ChartPoint[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    requestJson<ChartPoint[]>('/api/papers/stats/chart-data')
      .then(setPoints)
      .catch((err) => setError(err.message))
  }, [])

  const top = [...points].sort((a, b) => (b.y || 0) - (a.y || 0)).slice(0, 12)

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="muted">SC-Wiki</p>
          <h1 className="page-title">超导文献数据库</h1>
        </div>
        <p className="muted">围绕元素体系、化学式、论文和结构化物理记录的一站式研究工作台。</p>
      </header>

      <div className="grid two">
        <div className="panel">
          <h2>超导热点</h2>
          <p className="muted">实时读取数据库中的 Tc 与压力数据，用于快速发现高温超导候选体系。</p>
          {error && <div className="status error">{error}</div>}
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>材料</th><th>Tc/K</th><th>压力/GPa</th><th>类型</th></tr></thead>
              <tbody>
                {top.map((item, index) => (
                  <tr key={`${item.label}-${index}`}>
                    <td>{item.label || '-'}</td>
                    <td>{item.y ?? '-'}</td>
                    <td>{item.x ?? '-'}</td>
                    <td>{item.sc_type || item.type || '-'}</td>
                  </tr>
                ))}
                {top.length === 0 && <tr><td colSpan={4} className="muted">暂无图表数据</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="panel">
          <h2>工作流</h2>
          <div className="cards">
            <div className="card-row">选择元素或输入化学式，进入超导体系检索。</div>
            <div className="card-row">在组合页比较本地数据、Alexandria 与 HTSC-2025。</div>
            <div className="card-row">用 RAG 对话助手追问机理、文献和研究灵感。</div>
          </div>
        </div>
      </div>
    </section>
  )
}

export default HomePage
