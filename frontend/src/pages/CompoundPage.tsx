import React, { useEffect, useMemo, useState } from 'react'
import { useLocation, useParams } from 'react-router-dom'
import { getToken, postJson, requestJson } from '../lib/apiClient'

interface PaperResult {
  id?: number
  title?: string
  doi?: string
  year?: number
  journal?: string
  summary?: string
  records?: Array<{ chemical_formula?: string; tc_value?: number; pressure?: number; space_group?: string }>
}

interface AlexandriaResult {
  mat_id?: string
  formula?: string
  tc?: number
  stable?: boolean
  spacegroup?: string
}

const CompoundPage: React.FC = () => {
  const { elementSymbols = '' } = useParams()
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  const mode = params.get('mode') || 'elements_combination_search'
  const formula = params.get('formula') || ''
  const elements = useMemo(() => elementSymbols.split('-').filter(Boolean), [elementSymbols])

  const [papers, setPapers] = useState<PaperResult[]>([])
  const [materials, setMaterials] = useState<AlexandriaResult[]>([])
  const [status, setStatus] = useState('正在加载本地数据...')
  const [error, setError] = useState('')

  useEffect(() => {
    const body = formula
      ? { mode: 'formula_search', formula, elements }
      : { mode, elements }

    postJson<{ papers?: PaperResult[]; data?: PaperResult[] }>('/api/papers/search-by-mode', body)
      .then((data) => {
        setPapers(data.papers || data.data || [])
        setStatus('本地数据加载完成')
      })
      .catch((err) => {
        setError(err.message)
        setStatus('')
      })
  }, [formula, mode, elements])

  async function loadAlexandria() {
    setStatus('正在加载 Alexandria 数据...')
    try {
      const data = await postJson<{ results?: AlexandriaResult[]; data?: AlexandriaResult[] }>('/api/alexandria/search', {
        elements,
        mode,
        page: 1,
        page_size: 20,
      })
      setMaterials(data.results || data.data || [])
      setStatus('Alexandria 数据加载完成')
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function loadHtsc() {
    setStatus('正在加载 HTSC-2025 数据...')
    try {
      const data = await postJson<{ results?: AlexandriaResult[]; data?: AlexandriaResult[] }>('/api/htsc2025/search', {
        elements,
        mode,
        page: 1,
        page_size: 20,
      })
      setMaterials(data.results || data.data || [])
      setStatus('HTSC-2025 数据加载完成')
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function uploadPaper(file?: File) {
    if (!file) return
    if (!getToken()) {
      setError('请先登录后再上传文献')
      return
    }
    const form = new FormData()
    form.append('file', file)
    try {
      await requestJson('/api/papers/', { method: 'POST', body: form })
      setStatus('上传完成，等待审核')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="muted">Compound</p>
          <h1 className="page-title">{formula || elementSymbols || '材料体系'}</h1>
        </div>
        <div className="toolbar">
          <button className="button secondary" onClick={loadAlexandria}>Alexandria</button>
          <button className="button secondary" onClick={loadHtsc}>HTSC-2025</button>
        </div>
      </header>
      {status && <div className="status">{status}</div>}
      {error && <div className="status error">{error}</div>}

      <div className="grid two" style={{ marginTop: 14 }}>
        <div className="panel">
          <h2>本地文献与超导记录</h2>
          <div className="cards">
            {papers.map((paper, index) => (
              <article className="card-row" key={paper.id || index}>
                <h3>{paper.title || paper.doi || `论文 ${paper.id || index + 1}`}</h3>
                <p className="muted">{[paper.journal, paper.year].filter(Boolean).join(' · ') || '来源信息待补充'}</p>
                {paper.summary && <p>{paper.summary}</p>}
              </article>
            ))}
            {papers.length === 0 && <p className="muted">暂无本地文献结果</p>}
          </div>
        </div>

        <div className="panel">
          <h2>外部候选材料</h2>
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>材料</th><th>Tc</th><th>空间群</th><th>状态</th></tr></thead>
              <tbody>
                {materials.map((item, index) => (
                  <tr key={item.mat_id || index}>
                    <td>{item.formula || item.mat_id || '-'}</td>
                    <td>{item.tc ?? '-'}</td>
                    <td>{item.spacegroup || '-'}</td>
                    <td>{item.stable === undefined ? '-' : item.stable ? '稳定' : '不稳定'}</td>
                  </tr>
                ))}
                {materials.length === 0 && <tr><td colSpan={4} className="muted">点击上方按钮加载外部数据库</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel" style={{ marginTop: 14 }}>
        <h2>上传文献</h2>
        <input className="input" type="file" onChange={(e) => uploadPaper(e.target.files?.[0])} />
      </div>
    </section>
  )
}

export default CompoundPage
