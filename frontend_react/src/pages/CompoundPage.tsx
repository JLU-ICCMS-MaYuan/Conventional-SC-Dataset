import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Chip, Input, Spinner } from '@heroui/react'
import { useLocation, useParams } from 'react-router-dom'
import { postJson } from '../lib/apiClient'

interface Record {
  chemical_formula?: string; tc_value?: number; tc?: number
  pressure_gpa?: number; pressure?: number
  article_type?: string; space_group_symbol?: string
  data_source_note?: string
}

interface Paper {
  id?: number; title?: string; doi?: string; year?: number
  journal?: string; summary?: string; records?: Record[]
}

const MODES: Record<string, string> = {
  elements_combination_search: '组合',
  elements_exact_search: '精确',
  elements_contained_search: '包含',
}
const DEFAULT_MODE = 'elements_combination_search'

const CompoundPage: React.FC = () => {
  const { elementSymbols = '' } = useParams()
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  const urlMode = params.get('mode') || DEFAULT_MODE
  const urlFormula = params.get('formula') || ''
  const elements = useMemo(() => elementSymbols.split('-').filter(Boolean), [elementSymbols])

  const [mode, setMode] = useState(urlMode)
  const [papers, setPapers] = useState<Paper[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [expandedPaper, setExpandedPaper] = useState<number | null>(null)

  const search = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const body = urlFormula
        ? { mode: 'formula_search', formula: urlFormula, elements }
        : { mode, elements }
      const data = await postJson<{ papers?: Paper[]; data?: Paper[] }>('/api/papers/search-by-mode', body)
      setPapers(data.papers || data.data || [])
    } catch (err: any) {
      setError(err.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [mode, elements, urlFormula])

  useEffect(() => { search() }, [search])

  function rcTc(rec: Record): string {
    const v = rec.tc_value ?? rec.tc
    return v != null ? `${v} K` : '-'
  }

  function rcPressure(rec: Record): string {
    const v = rec.pressure_gpa ?? rec.pressure
    return v != null ? `${v} GPa` : '-'
  }

  function articleLabel(t: string | undefined): string {
    if (t === 'e') return '实验'
    if (t === 't') return '理论'
    return t || '-'
  }

  const title = urlFormula || elementSymbols

  return (
    <section className="page compound-page">
      <header className="page-header">
        <h1 className="page-title">{title}</h1>
        <p className="muted">{elements.join(', ')} · {papers.length} 篇论文</p>
        {!urlFormula && (
          <div className="toolbar">
            {Object.entries(MODES).map(([k, label]) => (
              <Button key={k} size="sm" variant={mode === k ? 'secondary' : 'outline'} onPress={() => setMode(k)}>
                {label}
              </Button>
            ))}
          </div>
        )}
      </header>

      {error && <div className="status-message error">{error}</div>}
      {loading && <Spinner label="加载中..." />}

      <div className="stack compound-results">
        {papers.map((paper, i) => {
          const pid = paper.id || i
          const isOpen = expandedPaper === pid
          return (
            <article key={pid} className="paper-card">
              <header className="paper-card-header" onClick={() => setExpandedPaper(isOpen ? null : pid)}>
                <div>
                  <h3 className="paper-title">{paper.title || paper.doi || `PID_${pid}`}</h3>
                  <p className="paper-meta">{[paper.journal, paper.year].filter(Boolean).join(' · ')}</p>
                </div>
                <Chip size="sm" variant="flat">{paper.records?.length || 0} 条记录</Chip>
              </header>
              {isOpen && paper.records && paper.records.length > 0 && (
                <div className="paper-records">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>化合物</th><th>Tc</th><th>压力</th><th>类型</th><th>空间群</th><th>备注</th>
                      </tr>
                    </thead>
                    <tbody>
                      {paper.records.map((rec, j) => (
                        <tr key={j}>
                          <td><strong>{rec.chemical_formula || '-'}</strong></td>
                          <td>{rcTc(rec)}</td>
                          <td>{rcPressure(rec)}</td>
                          <td>{articleLabel(rec.article_type)}</td>
                          <td>{rec.space_group_symbol || '-'}</td>
                          <td className="muted">{rec.data_source_note || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
              {isOpen && (!paper.records || paper.records.length === 0) && (
                <p className="muted" style={{ padding: 12 }}>暂无超导记录</p>
              )}
            </article>
          )
        })}
        {!loading && papers.length === 0 && <p className="muted">暂无结果</p>}
      </div>
    </section>
  )
}

export default CompoundPage
