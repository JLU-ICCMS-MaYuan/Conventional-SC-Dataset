import { useState, useRef, useCallback, useEffect } from 'react'
import { flushSync } from 'react-dom'
import { api } from '../lib/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: number
}

interface PaperInfo {
  title?: string
  doi?: string
  journal?: string
  year?: number
}

interface InspirationState {
  active: boolean
  mode: string
  modeLabel: string
  statusMessage: string
  sessionId: string
  ideasCount: number
}

interface IdeaCard {
  title: string
  fragments: Array<{ paper_id: number; quoted_text: string; section: string }>
  reasoning_chain: string
  assumptions: string[]
  feasibility?: { overall: number; theory: number; synthesis: number; measurement: number }
}

interface ReviewVerdict {
  flaws: Array<{ severity: string; description: string }>
  feasibility_score: number
  revised_idea: string
  dimensions: { theory: number; synthesis: number; measurement: number }
}

interface CachedMeta {
  papers: Record<string, PaperInfo>
  top10: any[]
  inspiration: InspirationState | null
  ideas: IdeaCard[]
  reviews: ReviewVerdict[]
}

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6)

function load(): Conversation[] {
  try {
    const raw = JSON.parse(localStorage.getItem('rag_conversations') || '[]')
    // strip empty assistant messages left over from failed sends
    return raw.map((c: Conversation) => ({
      ...c,
      messages: c.messages.filter(m => !(m.role === 'assistant' && !m.content)),
    }))
  } catch { return [] }
}
function save(list: Conversation[]) {
  localStorage.setItem('rag_conversations', JSON.stringify(list))
}

/** 按对话 ID 存取 papers + top10 */
function metaKey(cid: string) { return `rag_meta_${cid}` }
function loadMeta(cid: string): CachedMeta {
  try { return JSON.parse(localStorage.getItem(metaKey(cid)) || '{"papers":{},"top10":[],"inspiration":null,"ideas":[],"reviews":[]}') } catch { return { papers: {}, top10: [], inspiration: null, ideas: [], reviews: [] } }
}
function saveMeta(cid: string, meta: CachedMeta) {
  localStorage.setItem(metaKey(cid), JSON.stringify(meta))
}

export function useStreamingChat() {
  const [convs, setConvs] = useState<Conversation[]>(load)
  const [activeId, setActiveId] = useState<string>(() => convs[0]?.id || '')
  const [loading, setLoading] = useState(false)
  const [papers, setPapers] = useState<Record<string, PaperInfo>>(() => {
    const cid = convs[0]?.id
    return cid ? loadMeta(cid).papers : {}
  })
  const [top10, setTop10] = useState<any[]>(() => {
    const cid = convs[0]?.id
    return cid ? loadMeta(cid).top10 : []
  })
  const streamRef = useRef<HTMLDivElement | null>(null)

  const [inspiration, setInspiration] = useState<InspirationState>(() => {
    const cid = convs[0]?.id
    const defaultIns: InspirationState = { active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 }
    return cid ? (loadMeta(cid).inspiration || defaultIns) : defaultIns
  })
  const [ideas, setIdeas] = useState<IdeaCard[]>(() => {
    const cid = convs[0]?.id
    return cid ? (loadMeta(cid).ideas || []) : []
  })
  const [reviews, setReviews] = useState<ReviewVerdict[]>(() => {
    const cid = convs[0]?.id
    return cid ? (loadMeta(cid).reviews || []) : []
  })
  const [statusLog, setStatusLog] = useState<string[]>([])

  /** accumulated filtered papers across conversation turns */
  const [savedPapers, setSavedPapers] = useState<Array<{ pid: string; info: PaperInfo }>>([])
  const keptIdsRef = useRef<string[]>([])

  const messages = convs.find((c) => c.id === activeId)?.messages || []

  useEffect(() => { save(convs) }, [convs])

  const newConversation = useCallback(() => {
    const c: Conversation = { id: uid(), title: '新对话', messages: [], createdAt: Date.now() }
    setConvs((prev) => [c, ...prev])
    setActiveId(c.id)
    setPapers({})
    setTop10([])
    setIdeas([])
    setReviews([])
    setInspiration({ active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 })
    setStatusLog([])
    setSavedPapers([])
  }, [])

  const switchConversation = useCallback((id: string) => {
    setActiveId(id)
    const m = loadMeta(id)
    setPapers(m.papers || {})
    setTop10(m.top10 || [])
    setIdeas(m.ideas || [])
    setReviews(m.reviews || [])
    setInspiration(m.inspiration || { active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 })
    setStatusLog([])
    setSavedPapers([])
  }, [])

  const deleteConversation = useCallback((id: string) => {
    setConvs((prev) => {
      const next = prev.filter((c) => c.id !== id)
      save(next)
      if (activeId === id) {
        const nid = next[0]?.id || ''
        setActiveId(nid)
        if (nid) {
          const m = loadMeta(nid)
          setPapers(m.papers)
          setTop10(m.top10)
          setInspiration(m.inspiration || { active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 })
        } else {
          setPapers({})
          setTop10([])
          setInspiration({ active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 })
        }
      }
      return next
    })
    try { localStorage.removeItem(metaKey(id)) } catch { /* ignore */ }
  }, [activeId])

  const send = useCallback(async (question: string, explore = false) => {
    const q = question.trim()
    if (!q || loading) return

    let cid = activeId
    let history: Message[] = []

    if (!cid) {
      const c: Conversation = { id: uid(), title: q.slice(0, 20), messages: [], createdAt: Date.now() }
      setConvs((prev) => { save([c, ...prev]); return [c, ...prev] })
      cid = c.id
      setActiveId(cid)
    } else {
      const conv = convs.find((c) => c.id === cid)
      if (!conv) return
      history = conv.messages
    }

    const userMsg: Message = { role: 'user', content: q }
    setLoading(true)
    setPapers({})
    setTop10([])
    setStatusLog([])

    setConvs((prev) => prev.map((c) => c.id === cid ? {
      ...c,
      messages: [...c.messages, userMsg, { role: 'assistant' as const, content: '' }],
      title: c.messages.length === 0 ? q.slice(0, 20) : c.title,
    } : c))

    let fullAnswer = ''
    let firstToken = true
    let receivedPapers: Record<string, PaperInfo> = {}
    let receivedTop10: any[] = []
    let receivedIdeas: IdeaCard[] = []
    let receivedReviews: ReviewVerdict[] = []
    let finalInspiration: InspirationState | null = null

    try {
      const response = await api.postStream('/api/rag/chat/stream', {
        question: q, top_k: 15, rerank_top_k: 5, history, explore,
      })
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
            if (eventType === 'inspire_enter') {
              setInspiration({
                active: true,
                mode: data.mode,
                modeLabel: data.mode_label,
                sessionId: data.session_id,
                statusMessage: '正在分析...',
                ideasCount: 0,
              })
            } else if (eventType === 'inspire_mode') {
              setInspiration(prev => ({ ...prev, mode: data.mode, modeLabel: data.label }))
            } else if (eventType === 'curation') {
              keptIdsRef.current = (data.keep_paper_ids || []).map(String)
              setInspiration(prev => ({ ...prev, statusMessage: `筛选文献: ${data.keep_paper_ids?.length || 0} 篇 - ${data.summary?.slice(0, 60) || ''}` }))
            } else if (eventType === 'inspire_exit') {
              setInspiration({ active: false, mode: '', modeLabel: '', statusMessage: '', sessionId: '', ideasCount: 0 })
            } else if (eventType === 'evidence_card') {
              const card: IdeaCard = data
              receivedIdeas.push(card)
              setIdeas(prev => [...prev, card])
              setInspiration(prev => ({ ...prev, ideasCount: prev.ideasCount + 1 }))
            } else if (eventType === 'review_verdict') {
              const verdict: ReviewVerdict = data
              receivedReviews.push(verdict)
              setReviews(prev => [...prev, verdict])
            } else if (eventType === 'status') {
              const msg = data.message || ''
              if (msg) {
                flushSync(() => { setStatusLog(prev => [...prev, msg]) })
              }
              setInspiration(prev => prev.active ? { ...prev, statusMessage: msg } : prev)
            } else if (eventType === 'token') {
              const t = typeof data === 'string' ? data : String(data || '')
              fullAnswer += t
              if (streamRef.current) {
                if (firstToken) { streamRef.current.textContent = ''; firstToken = false }
                // 流式时用纯文本（快），完成后才由 React 渲染 LaTeX
                streamRef.current.textContent += t
              }
            } else if (eventType === 'done') {
              if (data.papers) { receivedPapers = data.papers; setPapers(data.papers) }
              if (data.top10) { receivedTop10 = data.top10; setTop10(data.top10) }
              // accumulate papers into savedPapers (deduplicated, sequential numbering)
              if (data.papers) {
                setSavedPapers(prev => {
                  const seen = new Set(prev.map(p => p.pid))
                  const added: Array<{ pid: string; info: PaperInfo }> = []
                  for (const pid of Object.keys(data.papers)) {
                    if (!seen.has(pid) && data.papers[pid]) {
                      added.push({ pid, info: data.papers[pid] })
                    }
                  }
                  return added.length > 0 ? [...prev, ...added] : prev
                })
              }
              // Brainstorm 会话标记嵌入在 answer 中（<!--BS:json-->），
              // token 事件只含正文不含标记，必须用 data.answer 覆盖 fullAnswer
              if (data.answer && data.answer.includes('<!--BS:')) {
                fullAnswer = data.answer
              }
              if (data.inspiration) {
                const ins: InspirationState = {
                  active: true,
                  mode: data.inspiration.current_mode || '',
                  modeLabel: data.inspiration.mode_label || '',
                  statusMessage: '',
                  sessionId: data.inspiration.session_id || '',
                  ideasCount: 0,
                }
                setInspiration(ins)
                finalInspiration = ins
              }
            } else if (eventType === 'error') {
              throw new Error(data.message || 'AI 错误')
            }
          } catch { /* skip */ }
        }
      }
    } catch (err: any) {
      setConvs((prev) => prev.map((c) => c.id === cid ? {
        ...c,
        messages: [...c.messages, { role: 'assistant', content: `❌ ${err.message}` }],
      } : c))
      return
    } finally {
      setLoading(false)
    }

    // 完成后写入 React state + 持久化 papers/top10
    setConvs((prev) => prev.map((c) => c.id === cid ? {
      ...c,
      messages: c.messages.map((m, i) =>
        i === c.messages.length - 1 && m.role === 'assistant'
          ? { ...m, content: fullAnswer }
          : m
      ),
    } : c))
    if (cid) saveMeta(cid, { papers: receivedPapers, top10: receivedTop10, inspiration: finalInspiration, ideas: receivedIdeas, reviews: receivedReviews })
  }, [activeId, convs, loading])

  return {
    convs, activeId, messages, loading, papers, top10, streamRef, inspiration,
    ideas, reviews, statusLog, savedPapers,
    newConversation, switchConversation, deleteConversation, send,
  }
}
