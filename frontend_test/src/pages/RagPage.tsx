import React, { useState, useRef, useEffect, useMemo } from 'react'
import 'bootstrap/dist/css/bootstrap.min.css'
import 'katex/dist/katex.min.css'
import { useStreamingChat } from '../hooks/useStreamingChat'
import MarkdownMessage from '../components/MarkdownMessage'
import EvidenceCard from '../components/EvidenceCard'

/** get citation order for right sidebar */
function citationOrder(content: string): string[] {
  const ids: string[] = []
  for (const m of content.matchAll(/\[PID_(\d+)\]/g)) {
    if (!ids.includes(m[1])) ids.push(m[1])
  }
  return ids
}

const RagPage: React.FC = () => {
  const {
    convs, activeId, messages, loading, papers, top10, streamRef,
    ideas, reviews, statusLog, savedPapers,
    newConversation, switchConversation, deleteConversation, send,
  } = useStreamingChat()

  const [input, setInput] = useState('')
  const [exploreMode, setExploreMode] = useState(false)
  const [sourceOpen, setSourceOpen] = useState(true)
  const [isStreaming, setIsStreaming] = useState(false)
  const chatBoxRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight) }, [messages, loading, ideas])
  useEffect(() => { inputRef.current?.focus() }, [])

  /* detect streaming start to hide loading dots */
  useEffect(() => {
    if (!loading) { setIsStreaming(false); return }
    const check = setInterval(() => {
      if (streamRef.current?.textContent) setIsStreaming(true)
    }, 100)
    return () => clearInterval(check)
  }, [loading, streamRef])


  const handleSend = () => { const q = input; setInput(''); send(q, exploreMode) }
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const loadSuggest = (q: string) => { setInput(q); send(q, exploreMode) }

  const citedOrder = useMemo(() => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant')
    return last ? citationOrder(last.content) : []
  }, [messages])

  const hasRightContent = top10.length > 0 || savedPapers.length > 0
  const hasCards = !loading && ideas.length > 0

  const paperSeqMap = useMemo(() => {
    const map: Record<string, number> = {}
    savedPapers.forEach((p, i) => { map[p.pid] = i + 1 })
    return map
  }, [savedPapers])

  return (
    <div style={st.wrapper}>
      <div style={st.body}>
        {/* ========== left: conversation list ========== */}
        <aside style={st.left}>
          <button style={st.newBtn} onClick={newConversation}>+ 新对话</button>
          <div style={{ overflowY: 'auto', flex: 1 }}>
            {convs.map((c) => (
              <div key={c.id} onClick={() => switchConversation(c.id)}
                style={{
                  ...st.hItem,
                  backgroundColor: c.id === activeId ? '#f0f0f0' : 'transparent',
                  position: 'relative',
                }}>
                <div style={st.hTitle}>{c.title}</div>
                <div style={st.hDate}>{new Date(c.createdAt).toLocaleDateString()}</div>
                <button onClick={(e) => { e.stopPropagation(); deleteConversation(c.id) }}
                  className="conv-del-btn" title="删除对话">x</button>
              </div>
            ))}
          </div>
        </aside>

        {/* ========== center: chat area ========== */}
        <main style={st.center}>
          <div ref={chatBoxRef} style={st.chatBox}>
            <div style={{ maxWidth: 720, margin: '0 auto', padding: '20px 0' }}>
              {/* empty state */}
              {messages.length === 0 && (
                <div style={{ textAlign: 'center', paddingTop: '20vh' }}>
                  <div style={{ fontSize: 28, fontWeight: 700, marginBottom: 8 }}>
                    氢化物超导文献助手
                  </div>
                  <div style={{ color: '#999', marginBottom: 24 }}>
                    基于超导论文数据库，问任何关于氢化物超导的问题
                  </div>
                  {['LaH10 的 Tc 是多少?', '超导温度高于 200K 的有哪些?', '笼状氢化物是什么?'].map((s) => (
                    <button key={s} style={st.chip} onClick={() => loadSuggest(s)}>{s}</button>
                  ))}
                </div>
              )}

              {/* message list — statusLog injected between user Q and AI A */}
              {messages.map((msg, i) => {
                const isUser = msg.role === 'user'
                const isAssistant = msg.role === 'assistant'
                const isEmptyAssistant = isAssistant && !msg.content && loading
                // true when this user message is immediately followed by the last assistant msg
                const beforeAssistant = isUser && messages[i + 1]?.role === 'assistant'

                return (
                  <React.Fragment key={i}>
                    {isUser && (
                      <div style={st.rowR}>
                        <div style={st.bubbleU}>{msg.content}</div>
                      </div>
                    )}

                    {/* status between user question and AI response */}
                    {beforeAssistant && statusLog.length > 0 && (
                      <div style={st.stepsWrap}>
                        {statusLog.map((s, j) => (
                          <div key={j} style={st.stepLine}>{s}</div>
                        ))}
                      </div>
                    )}

                    {isAssistant && msg.content && (
                      <div style={st.rowL}>
                        <div style={st.bubbleA}>
                          <MarkdownMessage content={msg.content} papers={papers} />
                        </div>
                      </div>
                    )}

                    {/* streaming placeholder replaces empty assistant during loading */}
                    {isEmptyAssistant && (
                      <>
                        {isStreaming && (
                          <div style={st.rowL}>
                            <div ref={streamRef} style={st.bubbleA} />
                          </div>
                        )}
                        {!isStreaming && (
                          <div style={st.loadingBar}>
                            <span style={st.dot} />
                            <span style={{ ...st.dot, animationDelay: '0.2s' }} />
                            <span style={{ ...st.dot, animationDelay: '0.4s' }} />
                            <span style={st.loadingText}>思考中...</span>
                          </div>
                        )}
                      </>
                    )}
                  </React.Fragment>
                )
              })}

              {/* idea cards */}
              {hasCards && (
                <div style={st.cardsWrap}>
                  {ideas.map((idea, i) => (
                    <EvidenceCard key={i} idea={idea} review={reviews[i]} paperSeqMap={paperSeqMap} />
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* input bar */}
          <div style={st.inputBar}>
            <div style={st.inputWrap}>
              <input ref={inputRef} style={st.input_} value={input}
                onChange={(e) => setInput(e.target.value)} onKeyDown={handleKeyDown}
                placeholder={exploreMode ? "说说你的想法，AI 帮你探索研究方向..." : "问一个超导问题..."} disabled={loading} />
              <button
                onClick={() => setExploreMode(!exploreMode)}
                style={{
                  ...st.exploreBtn,
                  backgroundColor: exploreMode ? '#4d6bfe' : '#fff',
                  color: exploreMode ? '#fff' : '#666',
                  borderColor: exploreMode ? '#4d6bfe' : '#e5e5e5',
                }}
              >🔬 探索模式</button>
              <button style={{ ...st.sendBtn, opacity: input.trim() && !loading ? 1 : 0.3 }}
                onClick={handleSend} disabled={!input.trim() || loading}>↑</button>
            </div>
          </div>
        </main>

        {/* ========== right: sources ========== */}
        {sourceOpen && (
          <aside style={st.right}>
            <div style={st.srcHead}>
              <span>文献来源</span>
              <button onClick={() => setSourceOpen(false)} style={st.closeBtn}>x</button>
            </div>
            <div style={{ overflowY: 'auto', flex: 1, padding: 12 }}>
              {!hasRightContent && !loading && (
                <div style={{ color: '#999', fontSize: 13 }}>探索模式下筛选的文献将显示在此处</div>
              )}

              {top10.length > 0 && (
                <div style={{ marginBottom: 16 }}>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#333' }}>Top 结果</div>
                  <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ borderBottom: '2px solid #e5e5e5', textAlign: 'left' }}>
                        <th style={{ padding: '4px 6px' }}>化合物</th>
                        <th style={{ padding: '4px 6px' }}>数值</th>
                        <th style={{ padding: '4px 6px' }}>文献</th>
                      </tr>
                    </thead>
                    <tbody>
                      {top10.map((r: any, i: number) => (
                        <tr key={i} style={{ borderBottom: '1px solid #f5f5f5' }}>
                          <td style={{ padding: '4px 6px', fontWeight: 500 }}>{r.subject}</td>
                          <td style={{ padding: '4px 6px', color: '#4d6bfe' }}>{r.object}</td>
                          <td style={{ padding: '4px 6px' }}>
                            {r.paper_id
                              ? <span style={st.pidBadge}>[{citedOrder.indexOf(String(r.paper_id)) + 1 || '?'}]</span>
                              : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {savedPapers.length > 0 && (
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 8, color: '#333' }}>
                    筛选文献 ({savedPapers.length})
                  </div>
                  {savedPapers.map(({ pid, info: p }, i) => (
                    <div key={pid} style={st.pCard}>
                      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 4 }}>
                        <span style={{ color: '#4d6bfe', marginRight: 6 }}>[{i + 1}]</span>
                        {p.title || `Paper #${pid}`}
                      </div>
                      {p.journal && (
                        <div style={{ fontSize: 12, color: '#666', marginLeft: 24 }}>
                          {p.journal}{p.year ? ` (${p.year})` : ''}
                        </div>
                      )}
                      {p.doi && (
                        <a href={`https://doi.org/${p.doi}`} target="_blank" rel="noopener"
                          style={{ fontSize: 11, color: '#4d6bfe', marginLeft: 24 }}>
                          {p.doi}
                        </a>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}
        {!sourceOpen && (
          <button onClick={() => setSourceOpen(true)} style={st.openSrc}>文献</button>
        )}
      </div>

      <style>{`
        @keyframes blink{0%,60%,100%{opacity:.3;transform:scale(.8)}30%{opacity:1;transform:scale(1)}}
        sup.cite-ref { font-size:11px; color:#4d6bfe; cursor:pointer; margin:0 1px; }
        sup.cite-ref:hover { text-decoration:underline; }
        sup.cite-muted { color:#999; }
        .conv-del-btn { position:absolute; right:6px; top:50%; transform:translateY(-50%); width:22px; height:22px; border-radius:50%; border:none; background:transparent; color:#ccc; font-size:16px; cursor:pointer; line-height:20px; text-align:center; transition:all .15s; }
        .conv-del-btn:hover { color:#e55; background:#fff0f0; }
        .navbar-custom { background-color:rgba(255,255,255,0.7) !important; backdrop-filter:blur(10px); -webkit-backdrop-filter:blur(10px); }
        .navbar-custom .navbar-brand, .navbar-custom .nav-link { color:#000 !important; }
        .navbar-custom .nav-link.active { font-weight:600; }
        .navbar-custom .btn-outline-light { color:#000 !important; border-color:#000 !important; }
        .navbar-custom .btn-outline-light:hover { background-color:#000 !important; color:#fff !important; }
        body { background:#fafafa; }
      `}</style>
    </div>
  )
}

const st: Record<string, React.CSSProperties> = {
  wrapper: {
    height: '100vh', display: 'flex', flexDirection: 'column',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    backgroundColor: '#fafafa', animation: 'elementFadeIn 0.5s ease both',
  },
  body: { flex: 1, display: 'flex', overflow: 'hidden' },

  left: {
    width: 230, flexShrink: 0, backgroundColor: '#fff',
    borderRight: '1px solid #f0f0f0', display: 'flex',
    flexDirection: 'column', padding: 12,
  },
  newBtn: {
    width: '100%', padding: '8px 0', borderRadius: 8,
    border: '1px solid #e5e5e5', backgroundColor: '#fff',
    fontSize: 13, cursor: 'pointer', marginBottom: 12, color: '#333',
  },
  hItem: {
    padding: '8px 10px', borderRadius: 8, cursor: 'pointer',
    marginBottom: 2, transition: 'background .15s',
  },
  hTitle: {
    fontSize: 13, color: '#333', overflow: 'hidden',
    textOverflow: 'ellipsis', whiteSpace: 'nowrap',
  },
  hDate: { fontSize: 11, color: '#aaa', marginTop: 2 },

  center: {
    flex: 1, display: 'flex', flexDirection: 'column',
    minWidth: 0, backgroundColor: '#fafafa',
  },
  chatBox: { flex: 1, overflowY: 'auto', padding: '0 20px' },

  rowR: { display: 'flex', justifyContent: 'flex-end', marginBottom: 16 },
  rowL: { display: 'flex', justifyContent: 'flex-start', marginBottom: 16 },

  bubbleU: {
    maxWidth: '70%', padding: '10px 16px', borderRadius: 18,
    backgroundColor: '#4d6bfe', color: '#fff', fontSize: 14, lineHeight: 1.7,
  },
  bubbleA: {
    maxWidth: '85%', padding: '12px 18px', borderRadius: 18,
    backgroundColor: '#fff', border: '1px solid #f0f0f0',
  },

  cardsWrap: {
    display: 'flex', flexDirection: 'column',
    alignItems: 'flex-start', marginBottom: 16,
    maxWidth: '85%', padding: '10px 0',
  } as React.CSSProperties,

  dot: {
    display: 'inline-block', width: 6, height: 6, borderRadius: '50%',
    backgroundColor: '#999', animation: 'blink 1.2s infinite', marginRight: 4,
  },

  chip: {
    padding: '6px 14px', borderRadius: 18, border: '1px solid #e5e5e5',
    backgroundColor: '#fff', color: '#666', fontSize: 13, cursor: 'pointer',
    margin: '0 4px 8px',
  },

  inputBar: { padding: '12px 20px 20px', backgroundColor: '#fafafa' },
  inputWrap: {
    maxWidth: 720, margin: '0 auto', display: 'flex', alignItems: 'center',
    backgroundColor: '#fff', borderRadius: 24, border: '1px solid #e5e5e5',
    padding: '4px 4px 4px 16px', boxShadow: '0 2px 8px rgba(0,0,0,.04)',
  },
  input_: {
    flex: 1, border: 'none', outline: 'none', fontSize: 14,
    padding: '8px 0', backgroundColor: 'transparent',
  },
  sendBtn: {
    width: 34, height: 34, borderRadius: '50%', border: 'none',
    backgroundColor: '#4d6bfe', color: '#fff', fontSize: 16,
    cursor: 'pointer', flexShrink: 0, transition: 'opacity .2s',
  },
  exploreBtn: {
    padding: '6px 12px', borderRadius: 18, border: '1px solid #e5e5e5',
    fontSize: 12, cursor: 'pointer', flexShrink: 0,
    transition: 'all .2s', marginRight: 6, whiteSpace: 'nowrap',
  } as React.CSSProperties,

  right: {
    width: 300, flexShrink: 0, backgroundColor: '#fff',
    borderLeft: '1px solid #f0f0f0', display: 'flex', flexDirection: 'column',
  },
  srcHead: {
    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
    padding: '12px 12px 8px', fontWeight: 600, fontSize: 13,
    borderBottom: '1px solid #f0f0f0',
  },
  closeBtn: { background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#999' },
  pCard: { padding: '8px 0', borderBottom: '1px solid #f5f5f5' },
  pidBadge: {
    display: 'inline-block', padding: '1px 6px', borderRadius: 4,
    backgroundColor: '#eef0ff', color: '#4d6bfe', fontSize: 11, fontWeight: 500,
  },
  openSrc: {
    position: 'absolute' as const, right: 16, bottom: 100,
    width: 40, height: 40, borderRadius: '50%', border: '1px solid #e5e5e5',
    backgroundColor: '#fff', fontSize: 18, cursor: 'pointer',
    boxShadow: '0 2px 8px rgba(0,0,0,.08)',
  },

  loadingBar: {
    display: 'flex', alignItems: 'center', gap: 4,
    padding: '4px 0 12px',
  } as React.CSSProperties,
  loadingText: {
    fontSize: 12, color: '#999', marginLeft: 4,
  },

  stepsWrap: {
    marginBottom: 12,
  } as React.CSSProperties,
  stepLine: {
    fontSize: 13, color: '#888', lineHeight: 1.8,
    fontWeight: 500,
  },
}

export default RagPage
