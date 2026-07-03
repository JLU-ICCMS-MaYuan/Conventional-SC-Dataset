import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { Button, Input, Spinner } from '@heroui/react'
import { useLocation, useParams } from 'react-router-dom'
import { getToken, postJson, requestJson } from '../lib/apiClient'

/* ── types ── */
interface Record {
  id?: number; chemical_formula?: string
  mcmillan_tc?: number; allen_dynes_tc?: number; experimental_tc?: number
  pressure_gpa?: number; article_type?: string
  space_group_symbol?: string; space_group_number?: number
  crystal_structure?: string; note?: string; method?: string
}
interface Paper {
  id?: number; title?: string; doi?: string; year?: number
  journal?: string; abstract?: string; review_status?: string
  records?: Record[]; chemical_formula?: string
}
const PAGE_SIZE = 30

/* ── helpers ── */
function tcVal(r: Record): string {
  const v = r.experimental_tc ?? r.allen_dynes_tc ?? r.mcmillan_tc
  return v != null ? `${Number(v).toFixed(0)} K` : '-'
}
function atLabel(t?: string) { return t === 'e' ? '实验' : t === 't' ? '理论' : t || '-' }
const statusBadge = (s?: string) => s === 'approved' ? '已通过' : s === 'pending' ? '未审核' : s === 'rejected' ? '已拒绝' : ''

/* ── page ── */
const CompoundPage: React.FC = () => {
  const { elementSymbols = '' } = useParams()
  const loc = useLocation()
  const params = new URLSearchParams(loc.search)
  const urlMode = params.get('mode') || 'elements_combination_search'
  const urlFormula = params.get('formula') || ''
  const elements = useMemo(() => elementSymbols.split('-').filter(Boolean), [elementSymbols])

  const [papers, setPapers] = useState<Paper[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [alexResults, setAlex] = useState<any[]>([])
  const [alexTab, setAlexTab] = useState(false)
  const [reviewFilter, setReviewFilter] = useState('all')
  const [paperFilter, setPaperFilter] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadMsg, setUploadMsg] = useState('')

  /* ── local search ── */
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

  /* ── alex / htsc ── */
  async function loadAlex() {
    setStatus('加载 Alexandria...')
    try {
      const r = await postJson<any>('/api/alexandria/search', { elements, mode: urlMode, page: 1, page_size: 20 })
      setAlex(r?.results || r?.data || [])
      setAlexTab(true)
      setStatus(`${r?.results?.length || 0} 候选`)
    } catch (e: any) { setStatus(`错误: ${e.message}`) }
  }
  async function loadHtsc() {
    setStatus('加载 HTSC-2025...')
    try {
      const r = await postJson<any>('/api/htsc2025/search', { elements, mode: urlMode, page: 1, page_size: 20 })
      setAlex(r?.results || r?.data || [])
      setAlexTab(true)
      setStatus(`${r?.results?.length || 0} 候选`)
    } catch (e: any) { setStatus(`错误: ${e.message}`) }
  }

  /* ── upload ── */
  async function handleUpload() {
    if (!uploadFile) return
    if (!getToken()) { setUploadMsg('请先登录'); return }
    const form = new FormData(); form.append('file', uploadFile)
    try {
      await requestJson('/api/papers/', { method: 'POST', body: form })
      setUploadMsg('上传成功'); setUploadFile(null)
    } catch (e: any) { setUploadMsg(`失败: ${e.message}`) }
  }

  /* ── filter ── */
  const filtered = papers
    .filter(p => reviewFilter === 'all' || p.review_status === reviewFilter)
    .filter(p => !paperFilter || (p.title || '').toLowerCase().includes(paperFilter.toLowerCase()))

  return (
    <section className="compound-page">
      {/* header */}
      <div className="compound-page-header">
        <div>
          <div className="kicker">Compound</div>
          <h1>{urlFormula || elementSymbols}</h1>
        </div>
        <div className="toolbar">
          <Button size="sm" variant="outline" onPress={loadAlex}>Alexandria</Button>
          <Button size="sm" variant="outline" onPress={loadHtsc}>HTSC-2025</Button>
        </div>
      </div>

      {status && <div className="muted" style={{marginBottom:12}}>{status}</div>}

      {/* review filter + paper search */}
      <div className="filter-row">
        <div className="filter-group">
          {['all','approved','pending'].map(v => (
            <button key={v} className={`filter-btn ${reviewFilter===v?'active':''}`}
              onClick={()=>setReviewFilter(v)}>
              {{all:'全部',approved:'已通过',pending:'未审核'}[v]}
            </button>
          ))}
        </div>
        <Input size="sm" placeholder="筛选论文标题..." value={paperFilter}
          onChange={e => setPaperFilter(e.target.value)} style={{width:220}} />
        <span className="muted" style={{marginLeft:'auto'}}>{total} 篇</span>
      </div>

      {loading && <Spinner />}

      {/* two-column: local + external */}
      <div className="compound-grid">
        {/* left: local papers */}
        <div className="card compound-card">
          <div className="card-header"><h2>本地文献与超导记录</h2></div>
          <div className="card-body-list">
            {(!alexTab ? filtered : []).map(p => (
              <details key={p.id} className="paper-detail">
                <summary className="paper-summary">
                  <div>
                    <strong>{p.title || `PID_${p.id}`}</strong>
                    <div className="meta">
                      {[p.journal, p.year].filter(Boolean).join(' · ')}
                      {p.review_status && <span className={`badge badge-${p.review_status}`}> {statusBadge(p.review_status)}</span>}
                    </div>
                  </div>
                </summary>
                {p.records && p.records.length > 0 && (
                  <table className="data-table">
                    <thead><tr><th>化合物</th><th>Tc</th><th>压力</th><th>类型</th><th>空间群</th><th>方法</th></tr></thead>
                    <tbody>
                      {p.records.map((r,i) => (
                        <tr key={i}>
                          <td><strong>{r.chemical_formula || '-'}</strong></td>
                          <td>{tcVal(r)}</td>
                          <td>{r.pressure_gpa != null ? `${r.pressure_gpa} GPa` : '-'}</td>
                          <td>{atLabel(r.article_type)}</td>
                          <td>{r.space_group_symbol || '-'}</td>
                          <td className="muted">{r.method || ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </details>
            ))}
            {!alexTab && filtered.length === 0 && !loading && <p className="muted p-16">暂无本地文献结果</p>}
          </div>
        </div>

        {/* right: external */}
        <div className="card compound-card">
          <div className="card-header"><h2>{alexTab ? '外部候选材料' : '外部候选材料'}</h2></div>
          <div className="card-body">
            {alexTab ? (
              <table className="data-table">
                <thead><tr><th>材料</th><th>Tc</th><th>空间群</th><th>状态</th></tr></thead>
                <tbody>
                  {alexResults.map((item:any,i:number) => (
                    <tr key={i}><td>{item.formula||item.mat_id||'-'}</td><td>{item.tc??'-'}</td><td>{item.spacegroup||'-'}</td><td>{item.stable?'稳定':'不稳定'}</td></tr>
                  ))}
                  {alexResults.length===0 && <tr><td colSpan={4}>暂无结果</td></tr>}
                </tbody>
              </table>
            ) : <p className="muted p-16">点击上方 Alexandria / HTSC-2025 按钮加载外部数据库</p>}
          </div>
        </div>
      </div>

      {/* pagination */}
      {total > PAGE_SIZE && (
        <div className="pagination-row">
          <Button size="sm" variant="outline" isDisabled={page<=1} onPress={()=>setPage(p=>p-1)}>上一页</Button>
          <span className="muted">{page} / {Math.ceil(total/PAGE_SIZE)}</span>
          <Button size="sm" variant="outline" isDisabled={page>=Math.ceil(total/PAGE_SIZE)} onPress={()=>setPage(p=>p+1)}>下一页</Button>
        </div>
      )}

      {/* upload */}
      <div className="card upload-card">
        <div className="card-header"><h2>上传文献</h2></div>
        <div className="upload-body">
          <Input size="sm" type="file" accept=".pdf" onChange={e => setUploadFile((e.target as HTMLInputElement).files?.[0] || null)} />
          <Button size="sm" variant="outline" onPress={handleUpload} isDisabled={!uploadFile}>上传</Button>
          {uploadMsg && <span className="muted">{uploadMsg}</span>}
        </div>
      </div>
    </section>
  )
}

export default CompoundPage
