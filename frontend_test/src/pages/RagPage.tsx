import React, { useState, useRef, useEffect } from 'react'
import { api } from '../lib/api'

interface RagMessage {
  role: 'user' | 'assistant'
  content: string
}

const VITE_LOGO = `data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E⚛️%3C/text%3E%3C/svg%3E`

const RagPage: React.FC = () => {
  const [messages, setMessages] = useState<RagMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [showEmpty, setShowEmpty] = useState(true)
  const chatBoxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight)
  }, [messages])

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    const userMsg: RagMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setShowEmpty(false)
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

      setMessages((prev) => [...prev, { role: 'assistant', content: '' }])

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
          } catch { /* skip */ }
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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div style={styles.wrapper}>
      {/* Header */}
      <header style={styles.header}>
        <a href="/" style={styles.logoLink}>
          <img src={VITE_LOGO} alt="SC-Wiki" style={styles.logo} />
          <span style={styles.brand}>SC-Wiki AI</span>
        </a>
        <span style={styles.headerTag}>超导文献助手</span>
      </header>

      {/* Chat area */}
      <div ref={chatBoxRef} style={styles.chatArea}>
        <div style={styles.chatInner}>
          {showEmpty && (
            <div style={styles.emptyState}>
              <div style={styles.emptyTitle}>⚛️ 氢化物超导文献助手</div>
              <div style={styles.emptySubtitle}>
                基于 638 篇超导论文、1012 种超导体、4709 条数据记录<br />
                可以问任何关于超导材料的问题
              </div>
              <div style={styles.suggestions}>
                {[
                  'LaH10 的超导温度是多少？',
                  'Tc 超过 200K 的超导体有哪些？',
                  '介绍一下笼状氢化物的结构特征',
                ].map((s) => (
                  <button
                    key={s}
                    style={styles.suggestionBtn}
                    onClick={() => { setInput(s); handleSend(); }}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} style={msg.role === 'user' ? styles.userRow : styles.assistantRow}>
              <div style={msg.role === 'user' ? styles.userBubble : styles.assistantBubble}>
                {msg.role === 'user' ? (
                  msg.content
                ) : (
                  <div
                    style={styles.answer}
                    dangerouslySetInnerHTML={{
                      __html: msg.content
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\[来源(\d+)\]/g, '<sup class="text-primary">[$1]</sup>')
                        .replace(/\n/g, '<br/>')
                    }}
                  />
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div style={styles.assistantRow}>
              <div style={styles.assistantBubble}>
                <div style={styles.typing}>
                  <span style={{ ...styles.dot, animationDelay: '0s' }} />
                  <span style={{ ...styles.dot, animationDelay: '0.2s' }} />
                  <span style={{ ...styles.dot, animationDelay: '0.4s' }} />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input area */}
      <div style={styles.inputArea}>
        <div style={styles.inputWrapper}>
          <input
            ref={inputRef}
            style={styles.input}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="问一个超导问题..."
            disabled={loading}
          />
          <button
            style={{ ...styles.sendBtn, opacity: input.trim() && !loading ? 1 : 0.4 }}
            onClick={handleSend}
            disabled={!input.trim() || loading}
          >
            ↑
          </button>
        </div>
        <div style={styles.disclaimer}>
          SC-Wiki AI 基于 RAG 检索，回答仅供参考
        </div>
      </div>

      {/* CSS keyframes */}
      <style>{`
        @keyframes blink {
          0%, 60%, 100% { opacity: 0.3; transform: scale(0.8); }
          30% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  wrapper: {
    display: 'flex', flexDirection: 'column', height: '100vh',
    backgroundColor: '#fafafa', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '12px 20px', backgroundColor: '#fff',
    borderBottom: '1px solid #f0f0f0',
  },
  logoLink: {
    display: 'flex', alignItems: 'center', gap: 8, textDecoration: 'none', color: '#1a1a1a',
  },
  logo: { width: 28, height: 28 },
  brand: { fontSize: 16, fontWeight: 600 },
  headerTag: { fontSize: 12, color: '#999' },
  chatArea: {
    flex: 1, overflowY: 'auto', padding: '20px 0',
  },
  chatInner: {
    maxWidth: 720, margin: '0 auto', padding: '0 20px',
  },
  emptyState: {
    textAlign: 'center', paddingTop: '16vh',
  },
  emptyTitle: {
    fontSize: 24, fontWeight: 600, color: '#1a1a1a', marginBottom: 12,
  },
  emptySubtitle: {
    fontSize: 14, color: '#999', lineHeight: 1.8, marginBottom: 32,
  },
  suggestions: {
    display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 8,
  },
  suggestionBtn: {
    padding: '8px 16px', borderRadius: 20, border: '1px solid #e5e5e5',
    backgroundColor: '#fff', color: '#666', fontSize: 13, cursor: 'pointer',
  },
  userRow: {
    display: 'flex', justifyContent: 'flex-end', marginBottom: 16,
  },
  assistantRow: {
    display: 'flex', justifyContent: 'flex-start', marginBottom: 16,
  },
  userBubble: {
    maxWidth: '75%', padding: '12px 18px', borderRadius: 18,
    backgroundColor: '#4d6bfe', color: '#fff', fontSize: 14, lineHeight: 1.7,
  },
  assistantBubble: {
    maxWidth: '85%', padding: '12px 18px', borderRadius: 18,
    backgroundColor: '#fff', color: '#1a1a1a', fontSize: 14, lineHeight: 1.9,
    border: '1px solid #f0f0f0',
  },
  answer: {},
  typing: {
    display: 'flex', gap: 4, padding: '4px 0',
  },
  dot: {
    width: 6, height: 6, borderRadius: '50%', backgroundColor: '#999',
    animation: 'blink 1.2s infinite',
  },
  inputArea: {
    padding: '16px 20px 24px', backgroundColor: '#fafafa',
  },
  inputWrapper: {
    maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'center',
    backgroundColor: '#fff', borderRadius: 24, border: '1px solid #e5e5e5',
    padding: '4px 4px 4px 18px', boxShadow: '0 2px 8px rgba(0,0,0,0.04)',
  },
  input: {
    flex: 1, border: 'none', outline: 'none', fontSize: 14, padding: '8px 0',
    backgroundColor: 'transparent', color: '#1a1a1a',
  },
  sendBtn: {
    width: 36, height: 36, borderRadius: '50%', border: 'none',
    backgroundColor: '#4d6bfe', color: '#fff', fontSize: 18, cursor: 'pointer',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    transition: 'all 0.2s', flexShrink: 0,
  },
  disclaimer: {
    textAlign: 'center', fontSize: 11, color: '#bbb', marginTop: 12,
  },
}

export default RagPage
