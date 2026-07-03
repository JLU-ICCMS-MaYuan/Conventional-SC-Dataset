import React from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import remarkMath from 'remark-math'

interface PaperInfo {
  title?: string
  doi?: string
  journal?: string
  year?: number
}

interface MarkdownMessageProps {
  content: string
  papers: Record<string, PaperInfo>
  paperSeqMap?: Record<string, number>
}

/** 清理文本中的内部标记，保留 [PID_xxx] 给组件处理 */
function cleanText(text: string): string {
  let t = text
  for (const tag of ['<!--IS:', '<!--BS:']) {
    const i = t.lastIndexOf(tag)
    if (i !== -1) t = t.substring(0, i)
  }
  t = t.replace(/\[PID_(\d+)[,\s]*来源\d+\]/g, '[PID_$1]')
  t = t.replace(/\[来源\d+\]（paper_id=\d+）/g, '')
  t = t.replace(/\[来源\d+\]/g, '')
  // 包裹裸 LaTeX
  t = t.replace(/(\\mathrm\{(?:[^{}]|\{[^{}]*\})*\}(?:_\{[^}]*\})?)/g, '$$1$')
  return t
}

const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, papers, paperSeqMap }) => {
  const text = cleanText(content)

  // 闭包捕获 papers, paperSeqMap
  const processText = (str: string): React.ReactNode => {
    const parts = str.split(/(\[PID_\d+\])/)
    if (parts.length === 1) return str
    return parts.map((part, i) => {
      const m = part.match(/^\[PID_(\d+)\]$/)
      if (!m) return part
      const pid = m[1]
      const seq = paperSeqMap?.[pid]
      if (!seq) return null
      const p = papers?.[pid]
      const href = p?.doi ? `https://doi.org/${p.doi}` : undefined
      const title = p?.journal && p?.year ? `${p.journal} (${p.year})` : p?.journal || `Paper #${pid}`
      return React.createElement('sup', {
        key: i,
        className: href ? 'cite-ref' : 'cite-muted',
        title,
      }, `[${seq}]`)
    })
  }

  const processChildren = (children: React.ReactNode): React.ReactNode => {
    return React.Children.map(children, child => {
      if (typeof child === 'string') return processText(child)
      if (React.isValidElement(child) && (child.props as any)?.children) {
        return React.cloneElement(child, {
          ...(child.props as any),
          children: processChildren((child.props as any).children),
        } as any)
      }
      return child
    })
  }

  return (
    <div className="markdown-body" style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[[rehypeKatex, { strict: false }]]}
        components={{
          p: ({ children, ...props }) => React.createElement('p', props, processChildren(children)),
          li: ({ children, ...props }) => React.createElement('li', props, processChildren(children)),
          td: ({ children, ...props }) => React.createElement('td', props, processChildren(children)),
          th: ({ children, ...props }) => React.createElement('th', props, processChildren(children)),
          span: ({ children, ...props }) => React.createElement('span', props, processChildren(children)),
        }}
      >
        {text}
      </ReactMarkdown>
      <style>{`
        sup.cite-ref { font-size: 11px; color: #4d6bfe; cursor: pointer; margin: 0 1px; }
        sup.cite-ref:hover { text-decoration: underline; }
        sup.cite-muted { font-size: 11px; color: #999; margin: 0 1px; }
      `}</style>
    </div>
  )
}

export default MarkdownMessage
