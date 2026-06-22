import { useState, useRef, useCallback, useEffect } from 'react'
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

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 6)

function load(): Conversation[] {
  try { return JSON.parse(localStorage.getItem('rag_conversations') || '[]') } catch { return [] }
}
function save(list: Conversation[]) {
  localStorage.setItem('rag_conversations', JSON.stringify(list))
}

export function useStreamingChat() {
  const [convs, setConvs] = useState<Conversation[]>(load)
  const [activeId, setActiveId] = useState<string>(() => convs[0]?.id || '')
  const [loading, setLoading] = useState(false)
  const [papers, setPapers] = useState<Record<string, PaperInfo>>({})
  const streamRef = useRef<HTMLDivElement | null>(null)

  const messages = convs.find((c) => c.id === activeId)?.messages || []

  useEffect(() => { save(convs) }, [convs])

  const newConversation = useCallback(() => {
    const c: Conversation = { id: uid(), title: '新对话', messages: [], createdAt: Date.now() }
    setConvs((prev) => [c, ...prev])
    setActiveId(c.id)
    setPapers({})
  }, [])

  const switchConversation = useCallback((id: string) => {
    setActiveId(id)
    setPapers({})
  }, [])

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

    setConvs((prev) => prev.map((c) => c.id === cid ? {
      ...c,
      messages: [...c.messages, userMsg, { role: 'assistant' as const, content: '' }],
      title: c.messages.length === 0 ? q.slice(0, 20) : c.title,
    } : c))

    let fullAnswer = ''

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
              if (streamRef.current) streamRef.current.textContent += t
            } else if (eventType === 'done' && data.papers) {
              setPapers((prev) => ({ ...prev, ...data.papers }))
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

    // 完成后一次性写入 React state
    setConvs((prev) => prev.map((c) => c.id === cid ? {
      ...c,
      messages: c.messages.map((m, i) =>
        i === c.messages.length - 1 && m.role === 'assistant'
          ? { ...m, content: fullAnswer }
          : m
      ),
    } : c))
  }, [activeId, convs, loading])

  return {
    convs, activeId, messages, loading, papers, streamRef,
    newConversation, switchConversation, send,
  }
}
