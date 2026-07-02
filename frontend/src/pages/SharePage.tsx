import React, { useState } from 'react'
import { getToken, requestJson } from '../lib/apiClient'

const SharePage: React.FC = () => {
  const [scope, setScope] = useState('formula')
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState('elements_combination_search')
  const [status, setStatus] = useState('')

  function download(format: string) {
    const params = new URLSearchParams({ format })
    if (scope === 'all') {
      params.set('scope', 'all')
    } else if (scope === 'formula') {
      params.set('scope', 'search')
      params.set('mode', 'formula_search')
      params.set('formula', query)
    } else {
      params.set('scope', 'search')
      params.set('mode', mode)
      params.set('elements', query.replace(/[，、\s-]+/g, ','))
    }
    window.location.href = `/api/papers/share-export?${params.toString()}`
  }

  async function uploadPdf(file?: File) {
    if (!file) return
    const token = getToken()
    if (!token) {
      setStatus('请先登录后再上传 PDF')
      return
    }
    const form = new FormData()
    form.append('file', file)
    try {
      const data = await requestJson<{ data?: { title?: string } }>('/api/rag/upload-pdf', { method: 'POST', body: form })
      setStatus(`上传完成：${data.data?.title || file.name}`)
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="muted">Share</p>
          <h1 className="page-title">超导分享</h1>
        </div>
      </header>
      <div className="grid two">
        <div className="panel">
          <h2>获取数据</h2>
          <div className="grid">
            <label className="field">下载方式
              <select className="select" value={scope} onChange={(e) => setScope(e.target.value)}>
                <option value="formula">按化学式检索</option>
                <option value="elements">按元素组合检索</option>
                <option value="all">全库下载</option>
              </select>
            </label>
            {scope !== 'all' && (
              <label className="field">{scope === 'formula' ? '化学式' : '元素'}
                <input className="input" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="LaH10 或 H-La" />
              </label>
            )}
            {scope === 'elements' && (
              <select className="select" value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="elements_combination_search">选择元素的组合</option>
                <option value="elements_exact_search">仅包含选择元素</option>
                <option value="elements_contained_search">包含所选元素</option>
              </select>
            )}
            <div className="toolbar">
              <button className="button" onClick={() => download('json')}>下载 JSON</button>
              <button className="button secondary" onClick={() => download('ris')}>下载 RIS</button>
            </div>
          </div>
        </div>
        <div className="panel">
          <h2>分享进展</h2>
          <p className="muted">上传论文 PDF 进入 RAG 摄入流程；手动结构化录入请进入组合页。</p>
          <input className="input" type="file" accept=".pdf" onChange={(e) => uploadPdf(e.target.files?.[0])} />
          {status && <div className="status">{status}</div>}
        </div>
      </div>
    </section>
  )
}

export default SharePage
