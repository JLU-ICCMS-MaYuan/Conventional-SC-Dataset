import React, { useState, useRef, useEffect } from 'react'
import { useStreamingChat } from '../hooks/useStreamingChat'

const RagPage: React.FC = () => {
  const {
    convs, activeId, messages, loading, papers, streamRef,
    newConversation, switchConversation, send,
  } = useStreamingChat()

  const [input, setInput] = useState('')
  const [sourceOpen, setSourceOpen] = useState(true)
  const chatBoxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight) }, [messages, loading])
  useEffect(() => { inputRef.current?.focus() }, [])

  const handleSend = () => { const q = input; setInput(''); send(q) }
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const loadSuggest = (q: string) => { setInput(q); send(q) }

  const citationIds = () => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant')
    if (!last) return []
    return [...new Set(Array.from(last.content.matchAll(/\[PID_(\d+)\]/g), (m) => m[1]))]
  }

  return (
    <div style={st.wrapper}>
      <header style={st.topbar}>
        <a href="/" style={st.brand}>⚛️ 超导文献数据库</a>
        <nav style={{ display: 'flex', gap: 20 }}>
          <a href="/" style={st.nav}>首页</a>
          <a href="/rag" style={{ ...st.nav, fontWeight: 600, color: '#4d6bfe' }}>AI 助手</a>
          <a href="/tc-pre" style={st.nav}>Tc 预测</a>
          <a href="/login" style={st.nav}>登录</a>
        </nav>
      </header>

      <div style={st.body}>
        <aside style={st.left}>
          <button style={st.newBtn} onClick={newConversation}>+ 新对话</button>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {convs.map((c) => (
              <div key={c.id} onClick={() => switchConversation(c.id)}
                style={{ ...st.hItem, backgroundColor: c.id === activeId ? '#f0f0f0' : 'transparent' }}>
                <div style={st.hTitle}>{c.title}</div>
                <div style={st.hDate}>{new Date(c.createdAt).toLocaleDateString()}</div>
              </div>
            ))}
          </div>
        </aside>

        <main style={st.center}>
          <div ref={chatBoxRef} style={st.chatBox}>
            <div style={{ maxWidth: 720, margin: '0 auto', padding: '20px 0' }}>
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', paddingTop: '20vh' }}>
                  <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>⚛️ 氢化物超导文献助手</div>
                  <div style={{ color: '#999', marginBottom: 24 }}>基于超导论文数据库，问任何关于氢化物超导的问题</div>
                  {['LaH10 的 Tc 是多少？', '超导温度高于 200K 的有哪些？', '笼状氢化物是什么？'].map((s) => (
                    <button key={s} style={st.chip} onClick={() => loadSuggest(s)}>{s}</button>
                  ))}
                </div>
              )}

              {messages.map((msg, i) => (
                <div key={i} style={msg.role === 'user' ? st.rowR : st.rowL}>
                  <div style={msg.role === 'user' ? st.bubbleU : st.bubbleA}
                    dangerouslySetInnerHTML={msg.role === 'assistant' ? { __html:
                      msg.content.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\[PID_(\d+)\]/g, '<sup class="text-primary">[📄$1]</sup>')
                        .replace(/\n/g, '<br/>')
                    } : undefined}>
                    {msg.role === 'user' ? msg.content : undefined}
                  </div>
                </div>
              ))}

              {loading && (
                <div style={st.rowL}>
                  <div ref={streamRef} style={st.bubbleA}>
                    <span style={st.dot} />
                    <span style={{ ...st.dot, animationDelay: '0.2s' }} />
                    <span style={{ ...st.dot, animationDelay: '0.4s' }} />
                  </div>
                </div>
              )}
            </div>
          </div>

          <div style={st.inputBar}>
            <div style={st.inputWrap}>
              <input ref={inputRef} style={st.input_} value={input}
                onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
                placeholder="问一个超导问题..." disabled={loading} />
              <button style={{ ...st.sendBtn, opacity: input.trim() && !loading ? 1 : 0.3 }}
                onClick={handleSend} disabled={!input.trim() || loading}>↑</button>
            </div>
          </div>
        </main>

        {sourceOpen && (
          <aside style={st.right}>
            <div style={st.srcHead}>
              <span>📚 文献来源</span>
              <button onClick={() => setSourceOpen(false)} style={st.closeBtn}>×</button>
            </div>
            <div style={{ overflowY: 'auto', flex: 1, padding: 12 }}>
              {citationIds().length === 0 && <div style={{ color: '#999', fontSize: 13 }}>暂无引用</div>}
              {citationIds().map((id) => {
                const p = papers[id]
                if (!p) return null
                return (
                  <div key={id} style={st.pCard}>
                    <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>{p.title || `Paper #${id}`}</div>
                    {p.journal && <div style={{ fontSize: 12, color: '#666' }}>{p.journal}{p.year ? ` (${p.year})` : ''}</div>}
                    {p.doi && <a href={`https://doi.org/${p.doi}`} target="_blank" style={{ fontSize: 11, color: '#4d6bfe' }}>{p.doi}</a>}
                  </div>
                )
              })}
            </div>
          </aside>
        )}
        {!sourceOpen && <button onClick={() => setSourceOpen(true)} style={st.openSrc}>📚</button>}
      </div>

      <style>{`@keyframes blink{0%,60%,100%{opacity:.3;transform:scale(.8)}30%{opacity:1;transform:scale(1)}}`}</style>
    </div>
  )
}

const st: Record<string, React.CSSProperties> = {
  wrapper: { height: '100vh', display: 'flex', flexDirection: 'column', fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif', backgroundColor: '#fafafa' },
  topbar: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 20px', height: 52, backgroundColor: '#fff', borderBottom: '1px solid #f0f0f0', flexShrink: 0 },
  brand: { fontWeight: 700, fontSize: 15, color: '#1a1a1a', textDecoration: 'none' },
  nav: { fontSize: 13, color: '#666', textDecoration: 'none' },
  body: { flex: 1, display: 'flex', overflow: 'hidden' },
  left: { width: 230, flexShrink: 0, backgroundColor: '#fff', borderRight: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column', padding: 12 },
  newBtn: { width: '100%', padding: '8px 0', borderRadius: 8, border: '1px solid #e5e5e5', backgroundColor: '#fff', fontSize: 13, cursor: 'pointer', marginBottom: 12, color: '#333' },
  hItem: { padding: '8px 10px', borderRadius: 8, cursor: 'pointer', marginBottom: 2, transition: 'background .15s' },
  hTitle: { fontSize: 13, color: '#333', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' },
  hDate: { fontSize: 11, color: '#aaa', marginTop: 2 },
  center: { flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, backgroundColor: '#fafafa' },
  chatBox: { flex: 1, overflowY: 'auto', padding: '0 20px' },
  rowR: { display: 'flex', justifyContent: 'flex-end', marginBottom: 16 },
  rowL: { display: 'flex', justifyContent: 'flex-start', marginBottom: 16 },
  bubbleU: { maxWidth: '70%', padding: '10px 16px', borderRadius: 18, backgroundColor: '#4d6bfe', color: '#fff', fontSize: 14, lineHeight: 1.7 },
  bubbleA: { maxWidth: '85%', padding: '10px 16px', borderRadius: 18, backgroundColor: '#fff', color: '#1a1a1a', fontSize: 14, lineHeight: 1.9, border: '1px solid #f0f0f0' },
  dot: { display: 'inline-block', width: 6, height: 6, borderRadius: '50%', backgroundColor: '#999', animation: 'blink 1.2s infinite', marginRight: 4 },
  chip: { padding: '6px 14px', borderRadius: 18, border: '1px solid #e5e5e5', backgroundColor: '#fff', color: '#666', fontSize: 13, cursor: 'pointer', margin: '0 4px 8px' },
  inputBar: { padding: '12px 20px 20px', backgroundColor: '#fafafa' },
  inputWrap: { maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'center', backgroundColor: '#fff', borderRadius: 24, border: '1px solid #e5e5e5', padding: '4px 4px 4px 16px', boxShadow: '0 2px 8px rgba(0,0,0,.04)' },
  input_: { flex: 1, border: 'none', outline: 'none', fontSize: 14, padding: '8px 0', backgroundColor: 'transparent' },
  sendBtn: { width: 34, height: 34, borderRadius: '50%', border: 'none', backgroundColor: '#4d6bfe', color: '#fff', fontSize: 16, cursor: 'pointer', flexShrink: 0, transition: 'opacity .2s' },
  right: { width: 260, flexShrink: 0, backgroundColor: '#fff', borderLeft: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column' },
  srcHead: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 12px 8px', fontWeight: 600, fontSize: 13, borderBottom: '1px solid #f0f0f0' },
  closeBtn: { background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#999' },
  pCard: { padding: '8px 0', borderBottom: '1px solid #f5f5f5' },
  openSrc: { position: 'absolute' as const, right: 16, bottom: 100, width: 40, height: 40, borderRadius: '50%', border: '1px solid #e5e5e5', backgroundColor: '#fff', fontSize: 18, cursor: 'pointer', boxShadow: '0 2px 8px rgba(0,0,0,.08)' },
}

export default RagPage
