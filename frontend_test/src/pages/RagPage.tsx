import React, { useState, useRef, useEffect } from 'react'
import { Container, Form, Button, Spinner, Alert, Row, Col, Card } from 'react-bootstrap'
import ChatMessage from '../components/ChatMessage'
import NavBar from '../components/NavBar'
import { api } from '../lib/api'

interface RagMessage {
  role: 'user' | 'assistant'
  content: string
}

interface RagStats {
  papers: number
  superconductors: number
  records: number
  chunks: number
  chroma_chunks: number
}

const RagPage: React.FC = () => {
  const [messages, setMessages] = useState<RagMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<RagStats | null>(null)
  const [healthMsg, setHealthMsg] = useState('')
  const chatBoxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/api/rag/health').then((d: any) => {
      setHealthMsg(d.message || '')
    }).catch(() => setHealthMsg('AI 文献助手不可用'))

    api.get('/api/rag/stats').then((d: any) => {
      if (d.data) setStats(d.data)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight)
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    const userMsg: RagMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    let fullAnswer = ''

    try {
      const response = await api.postStream('/api/rag/chat/stream', {
        question,
        top_k: 15,
        rerank_top_k: 5,
        history: messages,
      })

      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const assistantMsg: RagMessage = { role: 'assistant', content: '' }
      setMessages((prev) => [...prev, assistantMsg])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          let eventType = 'message'
          const dataLines: string[] = []
          part.split('\n').forEach((line) => {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
          })
          if (dataLines.length === 0) continue

          try {
            const data = JSON.parse(dataLines.join('\n'))
            if (eventType === 'token') {
              fullAnswer += typeof data === 'string' ? data : String(data || '')
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: fullAnswer }
                return updated
              })
            } else if (eventType === 'error') {
              throw new Error(data.message || 'AI 错误')
            }
          } catch {
            // 跳过无法解析的行
          }
        }
      }

      if (!fullAnswer) {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: '抱歉，未获取到回答。' }
          return updated
        })
      }
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: `❌ ${err.message}` }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <NavBar />
      <Container className="py-4" style={{ maxWidth: 800 }}>
        {healthMsg && (
          <Alert variant={healthMsg.includes('已就绪') ? 'success' : 'warning'} className="mb-3 py-2 text-center small">
            {healthMsg}
          </Alert>
        )}

        {stats && (
          <Row className="g-2 mb-4 text-center">
            {[
              { label: '论文', value: stats.papers },
              { label: '超导体', value: stats.superconductors },
              { label: '记录', value: stats.records },
              { label: '片段', value: stats.chunks },
            ].map((s) => (
              <Col key={s.label} xs={3}>
                <Card className="shadow-sm h-100">
                  <Card.Body className="py-2">
                    <div className="fs-5 fw-bold">{s.value?.toLocaleString() ?? '-'}</div>
                    <small className="text-muted">{s.label}</small>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        <div
          ref={chatBoxRef}
          className="border rounded-3 bg-white p-3 mb-3"
          style={{ minHeight: 400, maxHeight: '60vh', overflowY: 'auto' }}
        >
          {messages.length === 0 && (
            <div className="text-center text-muted py-5">
              <p className="fs-5">💬 AI 文献助手</p>
              <p>基于 638 篇超导论文，问任何关于氢化物超导的问题</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content} />
          ))}
          {loading && (
            <div className="d-flex justify-content-start mb-3">
              <Card bg="light" className="shadow-sm" style={{ borderRadius: 16 }}>
                <Card.Body className="py-2 px-4">
                  <Spinner animation="border" size="sm" className="me-2" />
                  思考中...
                </Card.Body>
              </Card>
            </div>
          )}
        </div>

        <Form
          onSubmit={(e) => { e.preventDefault(); handleSend() }}
          className="d-flex gap-2"
        >
          <Form.Control
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="问一个超导问题，例如「LaH10 的 Tc 是多少？」"
            disabled={loading}
            style={{ borderRadius: 24 }}
          />
          <Button type="submit" disabled={loading || !input.trim()} style={{ borderRadius: 24 }}>
            发送
          </Button>
        </Form>
      </Container>
    </>
  )
}

export default RagPage
