import React, { useState, useRef, useEffect, useMemo } from 'react'
import { Box, Typography, Button, IconButton, Chip, TextField, Paper, CircularProgress } from '@mui/material'
import SendIcon from '@mui/icons-material/Send'
import { useStreamingChat } from '../lib/useStreamingChat'
import MarkdownMessage from '../components/MarkdownMessage'
import EvidenceCard from '../components/EvidenceCard'
import { useLanguage } from '../context/LanguageContext'

function citationOrder(content: string): string[] {
  const ids: string[] = []
  for (const m of content.matchAll(/\[PID_(\d+)\]/g)) {
    if (!ids.includes(m[1])) ids.push(m[1])
  }
  return ids
}

const RagPage: React.FC = () => {
  const { t } = useLanguage()
  const suggestions = [t('rag.suggestion1'), t('rag.suggestion2'), t('rag.suggestion3')]

  const {
    convs, activeId, messages, loading, papers, top10,
    ideas, reviews, statusLog, savedPapers, inspiration,
    newConversation, switchConversation, deleteConversation, send,
  } = useStreamingChat()

  const [input, setInput] = useState('')
  const [exploreMode, setExploreMode] = useState(false)
  const [deleteMode, setDeleteMode] = useState(false)
  const chatBoxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (convs.length === 0) newConversation()
    else { if (activeId) switchConversation(activeId) } // 刷新后重新加载当前会话数据
  }, [])
  // activeId 变化时重新加载 papers
  useEffect(() => {
    if (activeId) switchConversation(activeId)
  }, [activeId])
  // 对话被命名后自动创建新的空对话（不切换）
  useEffect(() => {
    const active = convs.find((c) => c.id === activeId)
    if (active && active.title !== t('rag.newConversation') && active.messages.length > 0) {
      const hasEmpty = convs.some((c) => c.messages.length === 0 && c.title === t('rag.newConversation'))
      if (!hasEmpty) newConversation(false)
    }
  }, [convs, t])
  useEffect(() => {
    chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight)
  }, [messages, loading, ideas])

  const handleSend = () => {
    const q = input
    setInput('')
    send(q, exploreMode)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const citedOrder = useMemo(() => {
    const last = [...messages].reverse().find((m) => m.role === 'assistant')
    return last ? citationOrder(last.content) : []
  }, [messages])

  const paperSeqMap = useMemo(() => {
    const map: Record<string, number> = {}
    savedPapers.forEach((p, i) => { map[p.pid] = i + 1 })
    return map
  }, [savedPapers])

  return (
    <Box>
      {/* Page Header — matches demo .page-header */}
      <Box sx={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) auto', gap: 3, alignItems: 'end', mb: 3 }}>
        <Box>
          <Typography variant="overline">RAG Question Answering</Typography>
          <Typography variant="h1">{t('rag.pageTitle')}</Typography>
          <Typography variant="body2" sx={{ mt: 1 }}>
            {t('rag.pageDescription')}
          </Typography>
        </Box>
      </Box>

      {/* Two-column layout — matches demo .grid.two-col */}
      <Box sx={{ display: 'grid', gridTemplateColumns: '220px minmax(0, 1.6fr) minmax(280px, 0.9fr)', gap: 3 }}>
        {/* Left: Conversation List */}
        <Paper sx={{ p: 1.5, borderRadius: 4, height: 'calc(100vh - 300px)', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
            <Typography variant="h3">{t('rag.conversations')}</Typography>
            <Chip label={deleteMode ? t('rag.done') : t('common.delete')} size="small" color={deleteMode ? 'error' : 'default'} onClick={() => setDeleteMode(!deleteMode)} />
          </Box>
          {convs.length === 0 ? (
            <Typography variant="body2" sx={{ color: 'text.secondary' }}>{t('rag.noConversations')}</Typography>
          ) : (
            convs.map((c) => (
              <Box key={c.id} sx={{ position: 'relative', mb: 1, '&:hover .del-btn': { opacity: 1 } }}>
                <Chip
                  label={c.title}
                  color={c.id === activeId ? 'primary' : 'default'}
                  variant={c.id === activeId ? 'filled' : 'outlined'}
                  onClick={() => { if (deleteMode) deleteConversation(c.id); else switchConversation(c.id) }}
                  size="small"
                  sx={{ width: '100%' }}
                />
                {deleteMode && (
                  <IconButton
                    className="del-btn"
                    size="small"
                    onClick={() => deleteConversation(c.id)}
                    sx={{ position: 'absolute', right: -4, top: '50%', transform: 'translateY(-50%)', color: '#e55', bgcolor: '#fff0f0', width: 22, height: 22, fontSize: 14, opacity: 0.8, '&:hover': { bgcolor: '#ffe0e0' } }}
                  >
                    ✕
                  </IconButton>
                )}
              </Box>
            ))
          )}
        </Paper>

        {/* Center: Chat */}
        <Box sx={{ display: 'flex', flexDirection: 'column' }}>
          <Paper sx={{ p: 2.5, borderRadius: 4, boxShadow: '0 2px 6px rgba(15,23,42,.14), 0 4px 12px rgba(15,23,42,.08)', height: 'calc(100vh - 300px)', display: 'flex', flexDirection: 'column' }}>
            <Typography variant="h2" gutterBottom>{t('rag.chatStream')}</Typography>
            {inspiration.active && inspiration.statusMessage && (
              <Box sx={{ mb: 1, p: '6px 12px', borderRadius: 1, bgcolor: '#eef2ff', display: 'flex', alignItems: 'center', gap: 1 }}>
                <CircularProgress size={14} sx={{ color: '#4f46e5' }} />
                <Typography variant="body2" fontWeight={600} color="#4f46e5">
                  {inspiration.statusMessage}
                </Typography>
              </Box>
            )}
            <Box ref={chatBoxRef} sx={{ flex: 1, overflowY: 'auto', minHeight: 0 }}>
              {messages.length === 0 && (
                <Paper sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 4, mb: 2 }}>
                  <Typography variant="body2" sx={{ color: 'text.secondary' }}>
                    {t('rag.emptyHint')}
                  </Typography>
                  <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    {suggestions.map((s) => (
                      <Chip key={s} label={s} onClick={() => send(s, exploreMode)} size="small" />
                    ))}
                  </Box>
                </Paper>
              )}

              {messages.map((msg, i) => {
                const isUser = msg.role === 'user'
                const isAssistant = msg.role === 'assistant'

                return (
                  <Box key={i} sx={{ mb: 2 }}>
                    {isUser && (
                      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
                        <Paper sx={{
                          maxWidth: '75%', p: '10px 16px', borderRadius: '18px',
                          bgcolor: 'primary.main', color: 'primary.contrastText', fontSize: 14, lineHeight: 1.7,
                        }}>
                          {msg.content}
                        </Paper>
                      </Box>
                    )}

                    {isAssistant && msg.content && (
                      <Paper sx={{
                        p: '12px 18px', borderRadius: '18px',
                        bgcolor: 'background.paper', border: 1, borderColor: 'divider',
                      }}>
                        <MarkdownMessage content={msg.content} papers={papers} paperSeqMap={paperSeqMap} />
                      </Paper>
                    )}

                    {isAssistant && !msg.content && loading && (
                      <Box sx={{ py: 1 }}>
                        {statusLog.length > 0 ? (
                          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.5 }}>
                            {statusLog.map((s, i) => (
                              <Typography key={i} variant="body2" color="text.secondary" sx={{ fontSize: 12, fontFamily: 'monospace' }}>
                                {s}
                              </Typography>
                            ))}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                              <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#4f46e5', animation: 'blink 1.2s infinite' }} />
                            </Box>
                          </Box>
                        ) : (
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#999', animation: 'blink 1.2s infinite' }} />
                            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#999', animation: 'blink 1.2s infinite', animationDelay: '0.2s' }} />
                            <Box sx={{ width: 6, height: 6, borderRadius: '50%', bgcolor: '#999', animation: 'blink 1.2s infinite', animationDelay: '0.4s' }} />
                            <Typography variant="body2" color="text.secondary" sx={{ ml: 0.5, fontSize: 12 }}>{t('rag.waitingResponse')}</Typography>
                          </Box>
                        )}
                      </Box>
                    )}
                  </Box>
                )
              })}

              {/* Evidence cards */}
              {ideas.length > 0 && ideas.map((idea, i) => (
                <EvidenceCard key={i} idea={idea} review={reviews[i]} paperSeqMap={paperSeqMap} />
              ))}
            </Box>

            {/* Input — matches demo .field */}
            <Box sx={{ mt: 2.5, display: 'flex', gap: 1, alignItems: 'center' }}>
              <TextField
                fullWidth
                variant="outlined"
                size="small"
                placeholder={exploreMode ? t('rag.inputPlaceholderExplore') : t('rag.inputPlaceholder')}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={loading}
                sx={{ '& .MuiOutlinedInput-root': { borderRadius: '999px' } }}
              />
              <Button
                size="small"
                variant={exploreMode ? 'contained' : 'outlined'}
                onClick={() => setExploreMode(!exploreMode)}
                sx={{ borderRadius: '18px', flexShrink: 0, textTransform: 'none' }}
              >
                {t('rag.explore')}
              </Button>
              <IconButton
                onClick={handleSend}
                disabled={!input.trim() || loading}
                sx={{ width: 40, height: 40, bgcolor: 'primary.main', color: 'primary.contrastText', flexShrink: 0, '&:hover': { bgcolor: 'primary.dark' }, '&.Mui-disabled': { opacity: 0.3 } }}
              >
                <SendIcon sx={{ fontSize: 18 }} />
              </IconButton>
            </Box>
          </Paper>
        </Box>

        {/* Right: Evidence Panel — matches demo .card.side-sheet */}
        <Paper sx={{
          p: 2.5, borderRadius: 4, height: 'calc(100vh - 300px)', overflowY: 'auto',
          boxShadow: '0 6px 16px rgba(15,23,42,.16), 0 10px 24px rgba(15,23,42,.10)',
        }}>
          <Typography variant="h2" gutterBottom>{t('rag.evidencePanel')}</Typography>

          {top10.length > 0 && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="caption">{t('rag.topResults')}</Typography>
              <Box component="table" sx={{ width: '100%', fontSize: 12, borderCollapse: 'collapse', mt: 1 }}>
                <Box component="thead">
                  <Box component="tr" sx={{ borderBottom: '2px solid', borderColor: 'divider' }}>
                    <Box component="th" sx={{ p: '4px 6px', textAlign: 'left' }}>{t('rag.topHeaders.compound')}</Box>
                    <Box component="th" sx={{ p: '4px 6px', textAlign: 'left' }}>{t('rag.topHeaders.value')}</Box>
                    <Box component="th" sx={{ p: '4px 6px', textAlign: 'left' }}>{t('rag.topHeaders.reference')}</Box>
                  </Box>
                </Box>
                <Box component="tbody">
                  {top10.map((r: any, i: number) => (
                    <Box component="tr" key={i} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
                      <Box component="td" sx={{ p: '4px 6px', fontWeight: 500 }}>{r.subject}</Box>
                      <Box component="td" sx={{ p: '4px 6px', color: 'primary.main' }}>{r.object}</Box>
                      <Box component="td" sx={{ p: '4px 6px' }}>
                        {r.paper_id
                          ? <Chip label={`[${citedOrder.indexOf(String(r.paper_id)) + 1 || '?'}]`} size="small" color="primary" />
                          : '-'}
                      </Box>
                    </Box>
                  ))}
                </Box>
              </Box>
            </Box>
          )}

          {(savedPapers.length > 0 || Object.keys(papers).length > 0) ? (
            <Box>
              <Typography variant="caption" sx={{ mb: 1, display: 'block' }}>
                {t('rag.filteredPapers', { count: savedPapers.length || Object.keys(papers).length })}
              </Typography>
              {(savedPapers.length > 0 ? savedPapers.map(({ pid, info: p }, i) => (
                <Paper key={pid} sx={{ p: 1.5, mb: 1, bgcolor: 'grey.50', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <Chip label={`[${i + 1}]`} size="small" color="primary" />
                    <Typography variant="body2" fontWeight={600}>{p.title || `Paper #${pid}`}</Typography>
                  </Box>
                  {p.journal && (
                    <Typography variant="caption" sx={{ ml: 3, display: 'block' }}>
                      {p.journal}{p.year ? ` (${p.year})` : ''}
                    </Typography>
                  )}
                </Paper>
              )) : Object.entries(papers).map(([pid, p]: [string, any], i) => (
                <Paper key={pid} sx={{ p: 1.5, mb: 1, bgcolor: 'grey.50', borderRadius: 2 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                    <Chip label={`[${i + 1}]`} size="small" color="primary" />
                    <Typography variant="body2" fontWeight={600}>{p.title || `Paper #${pid}`}</Typography>
                  </Box>
                  {p.journal && (
                    <Typography variant="caption" sx={{ ml: 3, display: 'block' }}>
                      {p.journal}{p.year ? ` (${p.year})` : ''}
                    </Typography>
                  )}
                </Paper>
              )))}
            </Box>
          ) : (
            <Paper sx={{ p: 2, bgcolor: 'grey.50', borderRadius: 2 }}>
              <Typography variant="body2" sx={{ color: 'text.secondary', fontSize: 13 }}>
                {loading ? t('rag.searchingEvidence') : t('rag.evidenceEmptyHint')}
              </Typography>
            </Paper>
          )}

        </Paper>
      </Box>
    </Box>
  )
}

export default RagPage
