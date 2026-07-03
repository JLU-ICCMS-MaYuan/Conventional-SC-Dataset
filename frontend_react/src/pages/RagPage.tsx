import React, { useEffect, useMemo, useRef, useState } from 'react'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  Separator,
  Input,
  ScrollShadow,
  Switch,
  Table,
} from '@heroui/react'
import { useStreamingChat } from '../hooks/useStreamingChat'
import MarkdownMessage from '../components/MarkdownMessage'
import EvidenceCard from '../components/EvidenceCard'

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

  useEffect(() => {
    if (!loading) { setIsStreaming(false); return }
    const check = setInterval(() => {
      if (streamRef.current?.textContent) setIsStreaming(true)
    }, 100)
    return () => clearInterval(check)
  }, [loading, streamRef])

  const handleSend = () => {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    send(question, exploreMode)
  }

  const handleKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const loadSuggest = (question: string) => {
    setInput(question)
    send(question, exploreMode)
  }

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
    <section className={`chat-shell ${sourceOpen ? '' : 'chat-shell-compact'}`}>
      <Card   className="chat-panel">
        <CardHeader className="flex-col items-stretch gap-3">
          <Button variant="primary"  onPress={newConversation}>新对话</Button>
        </CardHeader>
        <Separator />
        <CardContent className="p-2">
          <ScrollShadow className="h-full">
            <div className="stack">
              {convs.map((conversation) => (
                <Button
                  key={conversation.id}
                  className="justify-start"

                  variant={conversation.id === activeId ? 'secondary' : 'ghost'}

                  onPress={() => switchConversation(conversation.id)}
                >
                  <span className="min-w-0 flex-1 truncate text-left">
                    <span className="block truncate text-sm">{conversation.title}</span>
                    <span className="block text-xs text-[var(--sc-muted)]">{new Date(conversation.createdAt).toLocaleDateString()}</span>
                  </span>
                  <span
                    className="ml-2 rounded px-1 text-xs text-[var(--sc-muted)]"
                    onClick={(event) => {
                      event.stopPropagation()
                      deleteConversation(conversation.id)
                    }}
                  >
                    x
                  </span>
                </Button>
              ))}
            </div>
          </ScrollShadow>
        </CardContent>
      </Card>

      <Card   className="chat-panel">
        <CardContent className="grid h-full grid-rows-[1fr_auto] gap-4 p-4">
          <ScrollShadow className="chat-scroll" ref={chatBoxRef}>
            <div className="mx-auto max-w-[760px] py-6">
              {messages.length === 0 && (
                <div className="mx-auto grid max-w-[640px] gap-4 pt-[18vh] text-center">
                  <h1 className="page-title">氢化物超导文献助手</h1>
                  <p className="muted">基于超导论文数据库，问任何关于氢化物超导的问题</p>
                  <div className="toolbar justify-center">
                    {['LaH10 的 Tc 是多少?', '超导温度高于 200K 的有哪些?', '笼状氢化物是什么?'].map((suggestion) => (
                      <Button key={suggestion} variant="outline"  size="sm" onPress={() => loadSuggest(suggestion)}>
                        {suggestion}
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map((message, index) => {
                const isUser = message.role === 'user'
                const isAssistant = message.role === 'assistant'
                const isEmptyAssistant = isAssistant && !message.content && loading
                const beforeAssistant = isUser && messages[index + 1]?.role === 'assistant'

                return (
                  <React.Fragment key={`${message.role}-${index}`}>
                    {isUser && (
                      <div className="chat-message-row user">
                        <Card   className="chat-bubble user">
                          <CardContent className="px-4 py-3 text-sm">{message.content}</CardContent>
                        </Card>
                      </div>
                    )}

                    {beforeAssistant && statusLog.length > 0 && (
                      <div className="mb-3 grid gap-1 text-sm text-[var(--sc-muted)]">
                        {statusLog.map((item, stepIndex) => (
                          <span key={`${item}-${stepIndex}`}>{item}</span>
                        ))}
                      </div>
                    )}

                    {isAssistant && message.content && (
                      <div className="chat-message-row assistant">
                        <Card   className="chat-bubble border border-[var(--sc-border)]">
                          <CardContent className="px-4 py-3 text-sm">
                            <MarkdownMessage content={message.content} papers={papers} />
                          </CardContent>
                        </Card>
                      </div>
                    )}

                    {isEmptyAssistant && (
                      <>
                        {isStreaming && (
                          <div className="chat-message-row assistant">
                            <Card   className="chat-bubble border border-[var(--sc-border)]">
                              <CardContent><div ref={streamRef} /></CardContent>
                            </Card>
                          </div>
                        )}
                        {!isStreaming && (
                          <div className="mb-4 flex items-center">
                            <span className="loading-dot" />
                            <span className="loading-dot [animation-delay:0.2s]" />
                            <span className="loading-dot [animation-delay:0.4s]" />
                            <span className="ml-1 text-xs text-[var(--sc-muted)]">思考中...</span>
                          </div>
                        )}
                      </>
                    )}
                  </React.Fragment>
                )
              })}

              {hasCards && (
                <div className="max-w-[760px]">
                  {ideas.map((idea, index) => (
                    <EvidenceCard key={`${idea.title}-${index}`} idea={idea} review={reviews[index]} paperSeqMap={paperSeqMap} />
                  ))}
                </div>
              )}
            </div>
          </ScrollShadow>

          <div className="mx-auto flex w-full max-w-[760px] flex-col gap-3">
            <div className="flex gap-2">
              <Input
                ref={inputRef}
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={exploreMode ? '说说你的想法，AI 帮你探索研究方向...' : '问一个超导问题...'}
                disabled={loading}
              />
              <Button variant="primary" size="sm" isDisabled={!input.trim() || loading} onPress={handleSend}>
                发送
              </Button>
            </div>
            <div className="flex items-center justify-between gap-3">
              <Switch isSelected={exploreMode} onChange={setExploreMode} size="sm">
                探索模式
              </Switch>
              <Button variant="ghost"  size="sm" onPress={() => setSourceOpen((value) => !value)}>
                {sourceOpen ? '隐藏文献' : '显示文献'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {sourceOpen && (
        <Card   className="chat-panel">
          <CardHeader className="justify-between">
            <h2 className="font-semibold">文献来源</h2>
            <Button variant="ghost"  size="sm" onPress={() => setSourceOpen(false)}>关闭</Button>
          </CardHeader>
          <Separator />
          <CardContent>
            <ScrollShadow className="h-full">
              {!hasRightContent && !loading && (
                <p className="text-sm text-[var(--sc-muted)]">探索模式下筛选的文献将显示在此处</p>
              )}

              {top10.length > 0 && (
                <div className="stack">
                  <h3 className="font-semibold">Top 结果</h3>
                  <Table aria-label="Top 结果"><Table.Content>
                    <Table.Header>
                      <Table.Column>化合物</Table.Column>
                      <Table.Column>数值</Table.Column>
                      <Table.Column>文献</Table.Column>
                    </Table.Header>
                    <Table.Body>
                      {top10.map((result: any, index: number) => (
                        <Table.Row key={`${result.subject}-${index}`}>
                          <Table.Cell>{result.subject}</Table.Cell>
                          <Table.Cell>{result.object}</Table.Cell>
                          <Table.Cell>
                            {result.paper_id ? `[${citedOrder.indexOf(String(result.paper_id)) + 1 || '?'}]` : '-'}
                          </Table.Cell>
                        </Table.Row>
                      ))}
                    </Table.Body>
                  </Table.Content></Table>
                </div>
              )}

              {savedPapers.length > 0 && (
                <div className="stack mt-4">
                  <h3 className="font-semibold">筛选文献 ({savedPapers.length})</h3>
                  {savedPapers.map(({ pid, info: paper }, index) => (
                    <Card key={pid}   className="border border-[var(--sc-border)]">
                      <CardContent className="gap-1 text-sm">
                        <div className="font-semibold">
                          <span className="mr-2 text-[var(--sc-primary)]">[{index + 1}]</span>
                          {paper.title || `Paper #${pid}`}
                        </div>
                        {paper.journal && (
                          <div className="text-xs text-[var(--sc-muted)]">
                            {paper.journal}{paper.year ? ` (${paper.year})` : ''}
                          </div>
                        )}
                        {paper.doi && (
                          <a className="text-xs text-[var(--sc-primary)]" href={`https://doi.org/${paper.doi}`} target="_blank" rel="noopener">
                            {paper.doi}
                          </a>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </ScrollShadow>
          </CardContent>
        </Card>
      )}
    </section>
  )
}

export default RagPage
