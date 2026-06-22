import React, { useState, useCallback } from 'react'
import { Container, Row, Col, Card, Form, Button, InputGroup } from 'react-bootstrap'
import { useNavigate } from 'react-router-dom'
import NavBar from '../components/NavBar'
import PeriodicTable from '../components/PeriodicTable'

const ELEMENT_CATEGORIES: Record<string, { name: string; color: string }> = {
  'alkali-metal': { name: '碱金属', color: '#f4bcc2' },
  'alkaline-earth': { name: '碱土金属', color: '#e3bd91' },
  'transition-metal': { name: '过渡金属', color: '#edcda9' },
  'post-transition': { name: '后过渡金属', color: '#ededab' },
  'metalloid': { name: '类金属', color: '#9cd5a8' },
  'nonmetal': { name: '非金属', color: '#a3d7dc' },
  'halogen': { name: '卤素', color: '#b7a0db' },
  'noble-gas': { name: '稀有气体', color: '#cfb5d6' },
  'lanthanide': { name: '镧系', color: '#cea1ce' },
  'actinide': { name: '锕系', color: '#c782ab' },
}

const searchSuggestions = ['LaH10', 'H3S', 'CaH6', 'YBCO', '高温超导', '氢化物', '铁基超导']

const HomePage: React.FC = () => {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')

  const handleSearch = useCallback((e: React.FormEvent) => {
    e.preventDefault()
    const q = query.trim()
    if (!q) return
    if (/^[A-Z][a-z]?(-[A-Z][a-z]?)+$/.test(q)) {
      navigate(`/compound/${q}?mode=elements_contained_search`)
    } else {
      navigate(`/rag?q=${encodeURIComponent(q)}`)
    }
  }, [query, navigate])

  return (
    <>
      <NavBar />
      <Container className="py-5">
        <div className="text-center mb-5">
          <h1 className="display-4 fw-bold mb-3">超导文献数据库</h1>
          <p className="lead text-muted mb-4">探索超导材料的知识边界</p>

          <Form onSubmit={handleSearch} className="mx-auto mb-4" style={{ maxWidth: 560 }}>
            <InputGroup>
              <Form.Control
                size="lg"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="搜索化学式、元素体系或关键词..."
                style={{ borderRadius: '24px 0 0 24px', borderRight: 0, boxShadow: 'none' }}
              />
              <Button type="submit" size="lg" variant="primary" style={{ borderRadius: '0 24px 24px 0' }}>
                🔍
              </Button>
            </InputGroup>
          </Form>

          <div className="d-flex justify-content-center flex-wrap gap-2 mb-5">
            {searchSuggestions.map((s) => (
              <Button
                key={s}
                variant="outline-secondary"
                size="sm"
                style={{ borderRadius: 20 }}
                onClick={() => { setQuery(s); navigate(s.includes('基') ? `/rag?q=${encodeURIComponent(s)}` : `/compound/${s}?mode=elements_contained_search`) }}
              >
                {s}
              </Button>
            ))}
          </div>
        </div>

        <Row className="g-3 mb-5 text-center">
          {[
            { label: '论文', value: '638' },
            { label: '超导体', value: '1,012' },
            { label: '实验数据', value: '4,709' },
            { label: '文本片段', value: '29,369' },
          ].map((s) => (
            <Col key={s.label} xs={6} md={3}>
              <Card className="shadow-sm h-100 border-0 bg-light">
                <Card.Body className="py-3">
                  <div className="fs-3 fw-bold text-primary">{s.value}</div>
                  <small className="text-muted">{s.label}</small>
                </Card.Body>
              </Card>
            </Col>
          ))}
        </Row>

        <div className="mb-5">
          <h5 className="text-center mb-3 text-muted">元素周期表</h5>
          <PeriodicTable onElementClick={(symbols) => {
            if (symbols.length > 0) {
              navigate(`/compound/${symbols.join('-')}?mode=elements_contained_search`)
            }
          }} />
        </div>

        <Row className="g-3 mb-4">
          <Col md={6}>
            <Card className="shadow-sm h-100 cursor-pointer" style={{ cursor: 'pointer' }} onClick={() => navigate('/rag')}>
              <Card.Body className="text-center py-4">
                <div className="fs-1 mb-2">💬</div>
                <h5>AI 文献助手</h5>
                <p className="text-muted small mb-0">基于 RAG 的流式问答，知识图谱 + 文献检索</p>
              </Card.Body>
            </Card>
          </Col>
          <Col md={6}>
            <a href="/tc-pre" className="text-decoration-none">
              <Card className="shadow-sm h-100">
                <Card.Body className="text-center py-4">
                  <div className="fs-1 mb-2">🔮</div>
                  <h5 className="text-dark">Tc 预测</h5>
                  <p className="text-muted small mb-0">上传晶体结构文件，预测超导转变温度</p>
                </Card.Body>
              </Card>
            </a>
          </Col>
        </Row>

        <div className="text-center mt-4">
          <small className="text-muted">
            图例：{' '}
            {Object.entries(ELEMENT_CATEGORIES).map(([key, cat]) => (
              <span key={key} className="me-2">
                <span style={{ display: 'inline-block', width: 12, height: 12, borderRadius: 2, backgroundColor: cat.color, verticalAlign: 'middle' }} />{' '}
                {cat.name}
              </span>
            ))}
          </small>
        </div>
      </Container>
    </>
  )
}

export default HomePage
