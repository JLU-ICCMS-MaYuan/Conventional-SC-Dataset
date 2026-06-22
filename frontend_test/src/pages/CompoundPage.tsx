import React, { useState, useEffect, useCallback } from 'react'
import { Container, Row, Col, Card, Form, Button, Spinner, Badge, Pagination, ButtonGroup } from 'react-bootstrap'
import { useParams, useSearchParams } from 'react-router-dom'
import NavBar from '../components/NavBar'
import { api } from '../lib/api'

interface PaperItem {
  _type?: string
  _source?: string
  key?: string
  count?: number
  id?: number
  doi?: string
  title?: string
  journal?: string
  year?: number
  authors?: string[] | string
  chemical_formula?: string
  compound_symbols?: string
  elements?: string[]
  tc_max?: number
  tc?: number
  pressure_gpa?: number
  summary?: string
  review_status?: string
  records?: any[]
  abstract?: string
  data_points?: any[]
}

type DatabaseFilter = 'all' | 'local' | 'alexandria' | 'htsc2025'

const DB_LABELS: Record<string, string> = { local: '📚 本地', alexandria: '📖 Alexandria', htsc2025: '📊 HTSC-2025' }

const CompoundPage: React.FC = () => {
  const { elementSymbols: paramSymbols } = useParams<{ elementSymbols?: string }>()
  const [searchParams] = useSearchParams()

  const elements = paramSymbols?.split('-').filter(Boolean) || []
  const mode = searchParams.get('mode') || 'elements_contained_search'

  const [items, setItems] = useState<PaperItem[]>([])
  const [loading, setLoading] = useState(true)
  const [dbFilter, setDbFilter] = useState<DatabaseFilter>('all')
  const [keyword, setKeyword] = useState('')
  const [yearMin, setYearMin] = useState('')
  const [yearMax, setYearMax] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize] = useState(30)

  const fetchPapers = useCallback(async () => {
    if (elements.length === 0) return
    setLoading(true)
    try {
      const body: any = {
        elements,
        mode,
        limit: 200,
        offset: 0,
      }
      if (keyword.trim()) body.keyword = keyword.trim()
      if (yearMin) body.year_min = parseInt(yearMin)
      if (yearMax) body.year_max = parseInt(yearMax)

      const response = await api.post<{ items: PaperItem[]; total: number }>('/api/papers/search/all', body)
      setItems(response.items || [])
    } catch (err: any) {
      console.error('Paper search failed:', err.message)
      setItems([])
    } finally {
      setLoading(false)
    }
  }, [elements.join(','), mode, keyword, yearMin, yearMax])

  useEffect(() => { fetchPapers() }, [fetchPapers])

  const filtered = items.filter((item) => {
    if (item._type === 'section') return true
    if (dbFilter !== 'all' && item._source !== dbFilter) return false
    return true
  })

  const flatPapers = filtered.filter((item) => item._type !== 'section')
  const totalPages = Math.max(1, Math.ceil(flatPapers.length / pageSize))
  const pageItems = flatPapers.slice((page - 1) * pageSize, page * pageSize)

  const handleSearch = (e: React.FormEvent) => { e.preventDefault(); setPage(1); fetchPapers() }
  const handleReset = () => { setKeyword(''); setYearMin(''); setYearMax(''); setDbFilter('all'); setPage(1) }

  const renderItem = (item: PaperItem, index: number) => {
    if (item._type === 'section') {
      return (
        <div key={`section-${item.key || index}`} className="d-flex align-items-center mb-2 mt-3">
          <h6 className="mb-0 me-2">{item.key}</h6>
          <Badge bg="secondary" pill>{item.count}</Badge>
        </div>
      )
    }

    const isLocal = item._source === 'local'
    const isAlex = item._source === 'alexandria'
    const isHtsc = item._source === 'htsc2025'

    let tcVal = item.tc_max || item.tc || 0
    let pressureVal = item.pressure_gpa || 0
    let formula = item.chemical_formula || item.compound_symbols || elements.join('-')

    if (isLocal) {
      const recs = item.records || []
      if (recs.length > 0) {
        tcVal = recs[0].experimental_tc || recs[0].allen_dynes_tc || recs[0].mcmillan_tc || 0
        pressureVal = recs[0].pressure_gpa || 0
      }
    }

    const year = item.year || ''
    const journal = item.journal || ''
    const title = item.title || item.doi || '未命名文献'
    const doi = item.doi || ''
    const authors = Array.isArray(item.authors) ? item.authors.join(', ') : (item.authors || '')

    return (
      <Card key={`paper-${item.id || index}`} className="mb-3 shadow-sm">
        <Card.Body>
          <div className="d-flex justify-content-between align-items-start mb-2">
            <div>
              {isLocal && <Badge bg="primary" className="me-1">📚 本地</Badge>}
              {isAlex && <Badge bg="info" className="me-1">📖 Alexandria</Badge>}
              {isHtsc && <Badge bg="warning" text="dark" className="me-1">📊 HTSC</Badge>}
              <strong className="me-2">{formula}</strong>
              <small className="text-muted">Tc: {typeof tcVal === 'number' ? tcVal.toFixed(1) : tcVal} K</small>
              {pressureVal > 0 && <small className="text-muted ms-2">P: {typeof pressureVal === 'number' ? pressureVal.toFixed(1) : pressureVal} GPa</small>}
            </div>
            <small className="text-muted">{year} {journal}</small>
          </div>

          <h6 className="mb-1">
            {isLocal ? (
              title
            ) : (
              <a href={isAlex ? undefined : `https://doi.org/${doi}`} target="_blank" rel="noreferrer">
                {title}
              </a>
            )}
          </h6>

          {authors && <div className="text-muted small mb-2">{authors}</div>}

          {item.abstract && <div className="text-muted small mb-2" style={{ maxHeight: 60, overflow: 'hidden' }}>{item.abstract}</div>}
          {item.summary && <div className="text-muted small mb-2" style={{ maxHeight: 60, overflow: 'hidden' }}>{item.summary}</div>}

          {isLocal && item.records && item.records.length > 0 && (
            <div className="table-responsive mt-2">
              <table className="table table-sm table-bordered small mb-0">
                <thead className="table-light">
                  <tr>
                    <th>化学式</th>
                    <th>Tc (K)</th>
                    <th>P (GPa)</th>
                    <th>λ</th>
                    <th>空间群</th>
                    <th>类型</th>
                  </tr>
                </thead>
                <tbody>
                  {item.records.slice(0, 3).map((rec: any, ri: number) => (
                    <tr key={ri}>
                      <td>{rec.chemical_formula || formula}</td>
                      <td>{rec.experimental_tc || rec.allen_dynes_tc || rec.mcmillan_tc || '—'}</td>
                      <td>{rec.pressure_gpa || '—'}</td>
                      <td>{rec.lambda_value || '—'}</td>
                      <td>{rec.space_group_symbol || '—'}</td>
                      <td>{rec.article_type === 'e' ? '🔬 实验' : rec.article_type === 't' ? '⚛️ 理论' : '—'}</td>
                    </tr>
                  ))}
                  {item.records.length > 3 && (
                    <tr><td colSpan={6} className="text-center text-muted">+ {item.records.length - 3} 条更多数据</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </Card.Body>
      </Card>
    )
  }

  return (
    <>
      <NavBar />
      <Container className="py-4">
        <div className="text-center mb-4">
          <h4 className="fw-bold">{elements.join(' - ')}</h4>
          <p className="text-muted small">
            {mode === 'elements_exact_search' ? '精确元素体系' : mode === 'elements_combination_search' ? '元素子集组合' : '包含元素'}
            &nbsp;·&nbsp;
            <a href="/" className="text-decoration-none">← 返回元素周期表</a>
          </p>
        </div>

        {/* Filters */}
        <Card className="mb-3 shadow-sm">
          <Card.Body className="py-2">
            <Form onSubmit={handleSearch}>
              <Row className="g-2 align-items-center">
                <Col xs="auto">
                  <Form.Select size="sm" value={dbFilter} onChange={(e) => { setDbFilter(e.target.value as DatabaseFilter); setPage(1) }} style={{ width: 140 }}>
                    <option value="all">全部数据库</option>
                    <option value="local">文献数据库</option>
                    <option value="alexandria">Alexandria</option>
                    <option value="htsc2025">HTSC-2025</option>
                  </Form.Select>
                </Col>
                <Col xs={3}>
                  <Form.Control size="sm" value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="搜索关键词" />
                </Col>
                <Col xs={2}>
                  <Form.Control size="sm" value={yearMin} onChange={(e) => setYearMin(e.target.value)} placeholder="起始年份" type="number" />
                </Col>
                <Col xs={2}>
                  <Form.Control size="sm" value={yearMax} onChange={(e) => setYearMax(e.target.value)} placeholder="截止年份" type="number" />
                </Col>
                <Col xs="auto">
                  <ButtonGroup size="sm">
                    <Button type="submit" variant="primary">搜索</Button>
                    <Button variant="outline-secondary" onClick={handleReset}>重置</Button>
                  </ButtonGroup>
                </Col>
              </Row>
            </Form>
          </Card.Body>
        </Card>

        {/* Results */}
        {loading ? (
          <div className="text-center py-5">
            <Spinner animation="border" />
            <p className="text-muted mt-2">正在加载文献...</p>
          </div>
        ) : (
          <>
            <div className="text-muted small mb-2">共 {flatPapers.length} 条结果</div>
            {pageItems.length === 0 ? (
              <div className="text-center py-5 text-muted">未找到匹配的文献</div>
            ) : (
              pageItems.map((item, i) => renderItem(item, i))
            )}
            {totalPages > 1 && (
              <div className="d-flex justify-content-center mt-3">
                <Pagination>
                  <Pagination.Prev disabled={page <= 1} onClick={() => setPage(page - 1)} />
                  {Array.from({ length: Math.min(totalPages, 10) }, (_, i) => {
                    const start = Math.max(1, Math.min(page - 4, totalPages - 9))
                    const p = start + i
                    if (p > totalPages) return null
                    return <Pagination.Item key={p} active={p === page} onClick={() => setPage(p)}>{p}</Pagination.Item>
                  })}
                  <Pagination.Next disabled={page >= totalPages} onClick={() => setPage(page + 1)} />
                </Pagination>
              </div>
            )}
          </>
        )}
      </Container>
    </>
  )
}

export default CompoundPage
