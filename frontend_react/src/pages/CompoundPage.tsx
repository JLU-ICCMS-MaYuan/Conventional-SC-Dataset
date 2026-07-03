import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Input, Spinner } from '@heroui/react'
import { useLocation, useParams } from 'react-router-dom'
import { getToken, postJson, requestJson } from '../lib/apiClient'

interface Record {
  id?: number; chemical_formula?: string
  mcmillan_tc?: number; allen_dynes_tc?: number; experimental_tc?: number
  pressure_gpa?: number; article_type?: string
  space_group_symbol?: string; space_group_number?: number
  crystal_structure?: string; note?: string; method?: string
}

interface Paper {
  id?: number; title?: string; doi?: string; year?: number
  journal?: string; abstract?: string
  review_status?: string; records?: Record[]
  chemical_formula?: string
}

const PAGE_SIZE = 30

const CompoundPage: React.FC = () => {
  const { elementSymbols = '' } = useParams()
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  const urlMode = params.get('mode') || 'elements_combination_search'
  const urlFormula = params.get('formula') || ''
  const elements = useMemo(() => elementSymbols.split('-').filter(Boolean), [elementSymbols])

  const [papers, setPapers] = useState<Paper[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [activeTab, setActiveTab] = useState<'local' | 'alexandria' | 'htsc'>('local')
  const [alexResults, setAlexResults] = useState<any[]>([])
  const [reviewFilter, setReviewFilter] = useState('all')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadMsg, setUploadMsg] = useState('')
  const [paperFilter, setPaperFilter] = useState('')

  // ── search ──
  const search = useCallback(async () => {
    setLoading(true); setStatus('搜索中...')
    try {
      const body = urlFormula
        ? { mode: 'formula_search', formula: urlFormula, elements, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
        : { mode: urlMode, elements, limit: PAGE_SIZE, offset: (page - 1) * PAGE_SIZE }
      const resp = await postJson<any>('/api/papers/search-by-mode', body)
      const list = resp?.items || resp?.data?.items || []
      setPapers(Array.isArray(list) ? list : [])
      setTotal(resp?.total || list.length)
      setStatus(`${list.length} 篇`)
    } catch (e: any) { setStatus(`错误: ${e.message}`) }
    finally { setLoading(false) }
  }, [urlMode, urlFormula, elements, page])

  useEffect(() => { search() }, [search])

  // ── alexandria ──
  async function loadAlex() {
    setStatus('加载 Alexandria...')
    try {
      const r = await postJson<any>('/api/alexandria/search', { elements, mode: urlMode, page: 1, page_size: 20 })
      setAlexResults(r?.results || r?.data || [])
      setActiveTab('alexandria')
      setStatus(`${r?.results?.length || 0} 候选材料`)
    } catch (e: any) { setStatus(`错误: ${e.message}`) }
  }

  async function loadHtsc() {
    setStatus('加载 HTSC-2025...')
    try {
      const r = await postJson<any>('/api/htsc2025/search', { elements, mode: urlMode, page: 1, page_size: 20 })
      setAlexResults(r?.results || r?.data || [])
      setActiveTab('htsc')
      setStatus(`${r?.results?.length || 0} 候选材料`)
    } catch (e: any) { setStatus(`错误: ${e.message}`) }
  }

  async function handleUpload() {
    if (!uploadFile) return
    if (!getToken()) { setUploadMsg('请先登录'); return }
    const form = new FormData(); form.append('file', uploadFile)
    try {
      await requestJson('/api/papers/', { method: 'POST', body: form })
      setUploadMsg('上传成功，等待审核'); setUploadFile(null)
    } catch (e: any) { setUploadMsg(`上传失败: ${e.message}`) }
  }

  // ── render helpers ──
  function tcVal(r: Record): string {
    const v = r.experimental_tc ?? r.allen_dynes_tc ?? r.mcmillan_tc
    return v != null ? `${Number(v).toFixed(1)} K` : '-'
  }
  function atLabel(t?: string) { return t === 'e' ? '实验' : t === 't' ? '理论' : t || '-' }

  const title = urlFormula || elementSymbols

  // ── filter ──
  const filteredPapers = papers
    .filter(p => reviewFilter === 'all' || p.review_status === reviewFilter)
    .filter(p => !paperFilter || (p.title || '').toLowerCase().includes(paperFilter.toLowerCase()))

  return (
    <section className="page compound-page">
      <div className="compound-header">
        <h1>{title}</h1>
        <p className="muted">{elements.join(', ')} · {total} 篇论文</p>
      </div>

      <div className="stack compound-body">
        {/* Toolbar */}
        <div className="compound-toolbar">
          <div className="btn-group tabs">
            <Button size="sm" variant={activeTab === 'local' ? 'secondary' : 'outline'} onPress={() => setActiveTab('local')}>本地</Button>
            <Button size="sm" variant={activeTab === 'alexandria' ? 'secondary' : 'outline'} onPress={loadAlex}>Alexandria</Button>
            <Button size="sm" variant={activeTab === 'htsc' ? 'secondary' : 'outline'} onPress={loadHtsc}>HTSC-2025</Button>
          </div>
          <div className="btn-group review-filter">
            <Button size="sm" variant={reviewFilter==='all'?'secondary':'outline'} onPress={()=>setReviewFilter('all')}>全部</Button>
            <Button size="sm" variant={reviewFilter==='approved'?'secondary':'outline'} onPress={()=>setReviewFilter('approved')}>已通过</Button>
            <Button size="sm" variant={reviewFilter==='pending'?'secondary':'outline'} onPress={()=>setReviewFilter('pending')}>未审核</Button>
          </div>
          <Input size="sm" placeholder="筛选论文..." value={paperFilter} onChange={e => setPaperFilter(e.target.value)} style={{width:200}} />
          <span className="muted">{status}</span>
        </div>

        {/* Upload */}
        <div className="upload-row">
          <input type="file" accept=".pdf" onChange={e => setUploadFile(e.target.files?.[0] || null)} />
          <Button size="sm" variant="outline" onPress={handleUpload} isDisabled={!uploadFile}>上传 PDF</Button>
          {uploadMsg && <span className="muted">{uploadMsg}</span>}
        </div>

        {loading && <Spinner />}

        {/* Alexandria/HTSC table */}
        {activeTab !== 'local' && (
          <table className="data-table">
            <thead><tr><th>材料</th><th>Tc</th><th>空间群</th><th>状态</th></tr></thead>
            <tbody>
              {alexResults.map((item: any, i: number) => (
                <tr key={i}><td>{item.formula || item.mat_id || '-'}</td><td>{item.tc ?? '-'}</td><td>{item.spacegroup || '-'}</td><td>{item.stable ? '稳定' : '不稳定'}</td></tr>
              ))}
            </tbody>
          </table>
        )}

        {/* Paper cards */}
        {activeTab === 'local' && filteredPapers.map(p => (
          <details key={p.id} className="paper-detail">
            <summary className="paper-summary">
              <strong>{p.title || `PID_${p.id}`}</strong>
              <span className="muted">{[p.journal, p.year].filter(Boolean).join(' · ')} · {p.records?.length || 0} 条记录</span>
            </summary>
            {p.records && p.records.length > 0 && (
              <table className="data-table">
                <thead><tr><th>化合物</th><th>Tc</th><th>压力</th><th>类型</th><th>空间群</th><th>方法</th><th>备注</th></tr></thead>
                <tbody>
                  {p.records.map((r, i) => (
                    <tr key={i}>
                      <td><strong>{r.chemical_formula || '-'}</strong></td>
                      <td>{tcVal(r)}</td>
                      <td>{r.pressure_gpa != null ? `${r.pressure_gpa} GPa` : '-'}</td>
                      <td>{atLabel(r.article_type)}</td>
                      <td>{r.space_group_symbol || '-'}</td>
                      <td className="muted">{r.method || ''}</td>
                      <td className="muted">{r.note || ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </details>
        ))}

        {/* Pagination */}
        {activeTab === 'local' && total > PAGE_SIZE && (
          <div className="pagination-row">
            <Button size="sm" variant="outline" isDisabled={page<=1} onPress={()=>setPage(p=>p-1)}>上一页</Button>
            <span className="muted">{page} / {Math.ceil(total/PAGE_SIZE)}</span>
            <Button size="sm" variant="outline" isDisabled={page>=Math.ceil(total/PAGE_SIZE)} onPress={()=>setPage(p=>p+1)}>下一页</Button>
          </div>
        )}
      </div>
    </section>
  )
}

export default CompoundPage
