import { useState, useRef, useCallback, useEffect } from 'react'
import { api } from '../lib/api'
import { renderMath } from '../utils/math'
import 'katex/dist/katex.min.css'

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

interface CachedMeta {
  papers: Record<string, PaperInfo>
  top10: any[]
}

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6)

function load(): Conversation[] {
  try { return JSON.parse(localStorage.getItem('rag_conversations') || '[]') } catch { return [] }
}
function save(list: Conversation[]) {
  localStorage.setItem('rag_conversations', JSON.stringify(list))
}

/** 按对话 ID 存取 papers + top10 */
function metaKey(cid: string) { return `rag_meta_${cid}` }
function loadMeta(cid: string): CachedMeta {
  try { return JSON.parse(localStorage.getItem(metaKey(cid)) || '{"papers":{},"top10":[]}') } catch { return { papers: {}, top10: [] } }
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

  const messages = convs.find((c) => c.id === activeId)?.messages || []

  useEffect(() => { save(convs) }, [convs])

  const newConversation = useCallback(() => {
    const c: Conversation = { id: uid(), title: '新对话', messages: [], createdAt: Date.now() }
    setConvs((prev) => [c, ...prev])
    setActiveId(c.id)
    setPapers({})
    setTop10([])
  }, [])

  const switchConversation = useCallback((id: string) => {
    setActiveId(id)
    const m = loadMeta(id)
    setPapers(m.papers)
    setTop10(m.top10)
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
        } else {
          setPapers({})
          setTop10([])
        }
      }
      return next
    })
    try { localStorage.removeItem(metaKey(id)) } catch { /* ignore */ }
  }, [activeId])

  const send = useCallback(async (question: string) => {
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

    setConvs((prev) => prev.map((c) => c.id === cid ? {
      ...c,
      messages: [...c.messages, userMsg, { role: 'assistant' as const, content: '' }],
      title: c.messages.length === 0 ? q.slice(0, 20) : c.title,
    } : c))

    let fullAnswer = ''
    let firstToken = true
    let receivedPapers: Record<string, PaperInfo> = {}
    let receivedTop10: any[] = []

    try {
      const response = await api.postStream('/api/rag/chat/stream', {
        question: q, top_k: 15, rerank_top_k: 5, history,
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
            if (eventType === 'token') {
              const t = typeof data === 'string' ? data : String(data || '')
              fullAnswer += t
              if (streamRef.current) {
                if (firstToken) { streamRef.current.innerHTML = ''; firstToken = false }
                const cMap = new Map<string, number>()
                let cn = 1
                streamRef.current.innerHTML = renderMath(fullAnswer)
                  .replace(/\[PID_(\d+)\]/g, (_s: string, pid: string) => {
                    if (!cMap.has(pid)) cMap.set(pid, cn++)
                    return `<sup class="cite-ref">[${cMap.get(pid)}]</sup>`
                  })
                  .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                  .replace(/\n/g, '<br/>')
              }
            } else if (eventType === 'done') {
              if (data.papers) { receivedPapers = data.papers; setPapers(data.papers) }
              if (data.top10) { receivedTop10 = data.top10; setTop10(data.top10) }
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
    if (cid) saveMeta(cid, { papers: receivedPapers, top10: receivedTop10 })
  }, [activeId, convs, loading])

  return {
    convs, activeId, messages, loading, papers, top10, streamRef,
    newConversation, switchConversation, deleteConversation, send,
  }
}
