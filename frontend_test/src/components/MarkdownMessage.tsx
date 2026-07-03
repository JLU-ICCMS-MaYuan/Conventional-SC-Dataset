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
  paperSeqMap?: Record<string, number>  // 全局 PID→序号映射（来自 savedPapers）
}

const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, papers, paperSeqMap }) => {
  // 清理内部标记
  let text = content
  for (const tag of ['<!--IS:', '<!--BS:']) {
    const i = text.lastIndexOf(tag)
    if (i !== -1) text = text.substring(0, i)
  }
  text = text.replace(/\[来源\d+\]（paper_id=\d+）/g, '')
  text = text.replace(/\[来源\d+\]/g, '')
  const processed = text.replace(
    /\[PID_(\d+)\]/g,
    (_match, pid: string) => {
      const seq = paperSeqMap?.[pid]
      if (!seq) return ''  // 不在检索结果中，不显示
      const p = papers?.[pid]
      const doi = p?.doi || ''
      const tooltip = p?.journal && p?.year
        ? `${p.journal} (${p.year})`
        : p?.journal || `Paper #${pid}`
      return doi
        ? `<sup class="cite-ref" title="${tooltip}"><a href="https://doi.org/${doi}" target="_blank" rel="noopener">[${seq}]</a></sup>`
        : `<sup class="cite-muted">[${seq}]</sup>`
    }
  )

  return (
    <div className="markdown-body" style={{ fontSize: 14, lineHeight: 1.8, color: '#333' }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
      >
        {processed}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownMessage
