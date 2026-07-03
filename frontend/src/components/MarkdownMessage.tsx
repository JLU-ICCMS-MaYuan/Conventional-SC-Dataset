import React from 'react'
import ReactMarkdown from 'react-markdown'
import rehypeRaw from 'rehype-raw'
import remarkGfm from 'remark-gfm'

interface PaperInfo {
  title?: string
  doi?: string
  journal?: string
  year?: number
}

interface MarkdownMessageProps {
  content: string
  papers?: Record<string, PaperInfo>
}

function citationOrder(content: string): Record<string, number> {
  const order: Record<string, number> = {}
  let next = 1
  for (const match of content.matchAll(/\[PID_(\d+)\]/g)) {
    const pid = match[1]
    if (order[pid] === undefined) order[pid] = next++
  }
  return order
}

function normalizeCitations(content: string, order: Record<string, number>) {
  return content.replace(/\[PID_(\d+)\]/g, (_match, pid: string) => {
    return `<sup class="cite-ref" data-paper-id="${pid}">[${order[pid] ?? pid}]</sup>`
  })
}

const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, papers = {} }) => {
  const order = citationOrder(content)
  const normalized = normalizeCitations(content, order)

  return (
    <div className="markdown-message">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeRaw]}
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
          sup: ({ children, ...props }) => {
            const paperId = (props as { 'data-paper-id'?: string })['data-paper-id']
            const paper = paperId ? papers[paperId] : undefined
            const title = paper
              ? [paper.title, paper.journal, paper.year].filter(Boolean).join(' · ')
              : undefined
            return (
              <sup {...props} title={title}>
                {children}
              </sup>
            )
          },
        }}
      >
        {normalized}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMessage
