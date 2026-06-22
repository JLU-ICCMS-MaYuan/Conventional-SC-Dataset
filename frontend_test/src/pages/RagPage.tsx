import React, { useState, useRef, useEffect, useCallback } from 'react'
import { api } from '../lib/api'

/* ── types ────────────────────────────────────────────────── */

interface RagMessage {
  role: 'user' | 'assistant'
  content: string
}

interface Conversation {
  id: string
  title: string
  messages: RagMessage[]
  createdAt: number
}

interface PaperInfo {
  title?: string
  doi?: string
  journal?: string
  year?: number
}

/* ── helpers ──────────────────────────────────────────────── */

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6)

const loadConversations = (): Conversation[] => {
  try { return JSON.parse(localStorage.getItem('rag_conversations') || '[]') } catch { return [] }
}
const saveConversations = (list: Conversation[]) => {
  localStorage.setItem('rag_conversations', JSON.stringify(list))
}

/* ── component ────────────────────────────────────────────── */

const RagPage: React.FC = () => {
  const [convs, setConvs] = useState<Conversation[]>(loadConversations)
  const [activeId, setActiveId] = useState<string>(() => convs[0]?.id || '')
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(true)
  const [papers, setPapers] = useState<Record<string, PaperInfo>>({})

  const chatBoxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const streamingElRef = useRef<HTMLDivElement | null>(null)

  const messages = convs.find((c) => c.id === activeId)?.messages || []

  /* auto-scroll */
  useEffect(() => {
    chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight)
  }, [messages, loading])

  /* persist conversations */
  useEffect(() => { saveConversations(convs) }, [convs])

  /* ── actions ──────────────────────────────────────────── */

  const newChat = useCallback(() => {
    const c: Conversation = { id: uid(), title: '新对话', messages: [], createdAt: Date.now() }
    setConvs((prev) => [c, ...prev])
    setActiveId(c.id)
    setPapers({})
  }, [])

  const switchChat = useCallback((id: string) => {
    setActiveId(id)
    setPapers({})
  }, [])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    // ensure active conversation exists
    let cid = activeId
    let history: RagMessage[] = []
    if (!cid) {
      const c: Conversation = { id: uid(), title: question.slice(0, 20), messages: [], createdAt: Date.now() }
      setConvs((prev) => { saveConversations([c, ...prev]); return [c, ...prev] })
      cid = c.id
      setActiveId(cid)
    } else {
      const conv = convs.find((c) => c.id === cid)
      if (!conv) return
      history = conv.messages
    }

    // we must read the fresh conv after potential creation above
    // since React state updates are async, use the values we already have
    const userMsg: RagMessage = { role: 'user', content: question }
    setInput('')
    setLoading(true)
    setStreaming(false)

    setConvs((prev) => prev.map((c) => c.id === cid ? { ...c, messages: [...c.messages, userMsg, { role: 'assistant' as const, content: '' }], title: c.messages.length === 0 ? question.slice(0, 20) : c.title } : c))

    let fullAnswer = ''

    try {
      const response = await api.postStream('/api/rag/chat/stream', { question, top_k: 15, rerank_top_k: 5, history })
      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)
      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

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
              const t = typeof data === 'string' ? data : String(data || '')
              fullAnswer += t
              setStreaming(true)
              // direct DOM update to bypass React 18 batching
              if (streamingElRef.current) {
                streamingElRef.current.textContent += t
              }
              // also update React state in background
              setConvs((prev) => prev.map((c) => {
                if (c.id !== cid) return c
                const msgs = [...c.messages]
                msgs[msgs.length - 1] = { role: 'assistant', content: fullAnswer }
                return { ...c, messages: msgs }
              }))
            } else if (eventType === 'done' && data.papers) {
              setPapers((prev) => ({ ...prev, ...data.papers }))
            } else if (eventType === 'error') {
              throw new Error(data.message || 'AI 错误')
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
      setConvs((prev) => prev.map((c) => {
        if (c.id !== cid) return c
        const msgs = [...c.messages]
        msgs[msgs.length - 1] = { role: 'assistant', content: `❌ ${err.message}` }
        return { ...c, messages: msgs }
      }))
    } finally { setLoading(false); setStreaming(false) }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const citationIds = () => {
    const lastAssistant = [...messages].reverse().find((m) => m.role === 'assistant')
    if (!lastAssistant) return []
    const matches = lastAssistant.content.matchAll(/\[PID_(\d+)\]/g)
    return [...new Set(Array.from(matches, (m) => m[1]))]
  }

  /* ── render ────────────────────────────────────────────── */

  return (
    <div style={s.wrapper}>
      {/* ── top bar ─────────────────────────────────────── */}
      <header style={s.topbar}>
        <a href="/" style={s.brand}>⚛️ 超导文献数据库</a>
        <nav style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
          <a href="/" style={s.navLink}>首页</a>
          <a href="/rag" style={{ ...s.navLink, fontWeight: 600, color: '#4d6bfe' }}>AI 助手</a>
          <a href="/tc-pre" style={s.navLink}>Tc 预测</a>
          <a href="/login" style={s.navLink}>登录</a>
        </nav>
      </header>

      <div style={s.body}>
        {/* ── left: history ──────────────────────────────── */}
        <aside style={s.leftBar}>
          <button style={s.newBtn} onClick={newChat}>+ 新对话</button>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {convs.map((c) => (
              <div
                key={c.id}
                onClick={() => switchChat(c.id)}
                style={{ ...s.historyItem, backgroundColor: c.id === activeId ? '#f0f0f0' : 'transparent' }}
              >
                <div style={s.historyTitle}>{c.title}</div>
                <div style={s.historyDate}>{new Date(c.createdAt).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </aside>

        {/* ── center: chat ───────────────────────────────── */}
        <main style={s.chatMain}>
          <div ref={chatBoxRef} style={s.chatBox}>
            <div style={{ maxWidth: 720, margin: '0 auto', padding: '20px 0' }}>
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', paddingTop: '20vh' }}>
                  <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>⚛️ 氢化物超导文献助手</div>
                  <div style={{ color: '#999', marginBottom: 24 }}>基于 638 篇超导论文，问任何关于氢化物超导的问题</div>
                  {['LaH10 的 Tc 是多少？', '超导温度高于 200K 的有哪些？', '笼状氢化物是什么？'].map((s) => (
                    <button key={s} style={s.chip} onClick={() => { setInput(s); handleSend() }}>{s}</button>
                  ))}
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} style={msg.role === 'user' ? s.rowRight : s.rowLeft}>
                  <div style={msg.role === 'user' ? s.bubbleUser : s.bubbleAI}>
                    {msg.role === 'user' ? msg.content : (
                      <div dangerouslySetInnerHTML={{ __html:
                        msg.content
                          .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                          .replace(/\[PID_(\d+)\]/g, '<sup class="text-primary" style="cursor:pointer">[📄$1]</sup>')
                          .replace(/\n/g, '<br/>')
                      }} />
                    )}
                  </div>
                </div>
              ))}

              {loading && !streaming && (
                <div style={s.rowLeft}>
                  <div style={s.bubbleAI}>
                    <span style={s.dot} />
                    <span style={{ ...s.dot, animationDelay: '0.2s' }} />
                    <span style={{ ...s.dot, animationDelay: '0.4s' }} />
                  </div>
                </div>
              )}
              {loading && streaming && (
                <div style={s.rowLeft}>
                  <div ref={streamingElRef} style={s.bubbleAI} />
                </div>
              )}
            </div>
          </div>

          <div style={s.inputBar}>
            <div style={s.inputWrap}>
              <input
                ref={inputRef}
                style={s.input}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="问一个超导问题..."
                disabled={loading}
              />
              <button
                style={{ ...s.sendBtn, opacity: input.trim() && !loading ? 1 : 0.3 }}
                onClick={handleSend}
                disabled={!input.trim() || loading}
              >↑</button>
            </div>
          </div>
        </main>

        {/* ── right: sources ──────────────────────────────── */}
        {sourceOpen && (
          <aside style={s.rightBar}>
            <div style={s.sourceHeader}>
              <span>📚 文献来源</span>
              <button onClick={() => setSourceOpen(false)} style={s.closeBtn}>×</button>
            </div>
            <div style={{ overflowY: 'auto', flex: 1, padding: 12 }}>
              {citationIds().length === 0 && <div style={{ color: '#999', fontSize: 13 }}>当前回答暂无引用</div>}
              {citationIds().map((id) => {
                const p = papers[id]
                if (!p) return null
                return (
                  <div key={id} style={s.paperCard}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{p.title || `Paper #${id}`}</div>
                    {p.journal && <div style={{ fontSize: 12, color: '#666' }}>{p.journal}{p.year ? ` (${p.year})` : ''}</div>}
                    {p.doi && <a href={`https://doi.org/${p.doi}`} target="_blank" style={{ fontSize: 11, color: '#4d6bfe' }}>{p.doi}</a>}
                  </div>
                )
              })}
            </div>
          </aside>
        )}

        {!sourceOpen && (
          <button onClick={() => setSourceOpen(true)} style={s.openSourceBtn}>📚</button>
        )}
      </div>

      <style>{`@keyframes blink{0%,60%,100%{opacity:.3;transform:scale(.8)}30%{opacity:1;transform:scale(1)}}`}</style>
    </div>
  )
}

/* ── styles ──────────────────────────────────────────────── */

const s: Record<string, React.CSSProperties> = {
  wrapper: { height: '100vh', display: 'flex', flexDirection: 'column', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', backgroundColor: '#fafafa' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', height: 52, backgroundColor: '#fff', borderBottom: '1px solid #f0f0f0', flexShrink: 0 },
  brand: { fontWeight: 700, fontSize: 15, color: '#1a1a1a', textDecoration: 'none' },
  navLink: { fontSize: 13, color: '#666', textDecoration: 'none' },

  body: { flex: 1, display: 'flex', overflow: 'hidden' },

  /* left */
  leftBar: { width: 230, flexShrink: 0, backgroundColor: '#fff', borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', padding: 12 },
  newBtn: { width: '100%', padding: '8px 0', borderRadius: 8, border: '1px solid #e5e5e5', backgroundColor: '#fff', fontSize: 13, cursor: 'pointer', marginBottom: 12, color: '#333' },
  historyItem: { padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 2, transition: 'background .15s' },
  historyTitle: { fontSize: 13, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  historyDate: { fontSize: 11, color: '#aaa', marginTop: 2 },

  /* center */
  chatMain: { flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, backgroundColor: '#fafafa' },
  chatBox: { flex: 1, overflowY: 'auto', padding: '0 20px' },
  rowRight: { display: 'flex', justifyContent: 'flex-end', marginBottom: 16 },
  rowLeft: { display: 'flex', justifyContent: 'flex-start', marginBottom: 16 },
  bubbleUser: { maxWidth: '70%', padding: '10px 16px', borderRadius: 18, backgroundColor: '#4d6bfe', color: '#fff', fontSize: 14, lineHeight: 1.7 },
  bubbleAI: { maxWidth: '85%', padding: '10px 16px', borderRadius: 18, backgroundColor: '#fff', color: '#1a1a1a', fontSize: 14, lineHeight: 1.9, border: '1px solid #f0f0f0' },
  dot: { display: 'inline-block', width: 6, height: 6, borderRadius: '50%', backgroundColor: '#999', animation: 'blink 1.2s infinite', marginRight: 4 },
  chip: { padding: '6px 14px', borderRadius: 18, border: '1px solid #e5e5e5', backgroundColor: '#fff', color: '#666', fontSize: 13, cursor: 'pointer', margin: '0 4px 8px' },

  inputBar: { padding: '12px 20px 20px', backgroundColor: '#fafafa' },
  inputWrap: { maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'center', backgroundColor: '#fff', borderRadius: 24, border: '1px solid #e5e5e5', padding: '4px 4px 4px 16px', boxShadow: '0 2px 8px rgba(0,0,0,.04)' },
  input: { flex: 1, border: 'none', outline: 'none', fontSize: 14, padding: '8px 0', backgroundColor: 'transparent' },
  sendBtn: { width: 34, height: 34, borderRadius: '50%', border: 'none', backgroundColor: '#4d6bfe', color: '#fff', fontSize: 16, cursor: 'pointer', flexShrink: 0, transition: 'opacity .2s' },

  /* right */
  rightBar: { width: 260, flexShrink: 0, backgroundColor: '#fff', borderLeft: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' },
  sourceHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 12px 8px', fontWeight: 600, fontSize: 13, borderBottom: '1px solid #f0f0f0' },
  closeBtn: { background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#999' },
  paperCard: { padding: '8px 0', borderBottom: '1px solid #f5f5f5' },
  openSourceBtn: { position: 'absolute' as const, right: 16, bottom: 100, width: 40, height: 40, borderRadius: '50%', border: '1px solid #e5e5e5', backgroundColor: '#fff', fontSize: 18, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,.08)' },
}

export default RagPage
