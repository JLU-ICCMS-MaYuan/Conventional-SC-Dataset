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
}

/**
 * Renders markdown with citation support.
 * Replaces [PID_xxx] markers with superscript citation links.
 */
/** 构建 PID → 顺序编号映射（按首次出现顺序） */
function buildSeqMap(content: string): Map<string, number> {
  const map = new Map<string, number>()
  let n = 1
  for (const m of content.matchAll(/\[PID_(\d+)\]/g)) {
    if (!map.has(m[1])) map.set(m[1], n++)
  }
  return map
}

const MarkdownMessage: React.FC<MarkdownMessageProps> = ({ content, papers }) => {
  // 清理内部标记
  let text = content
  for (const tag of ['<!--IS:', '<!--BS:']) {
    const i = text.lastIndexOf(tag)
    if (i !== -1) text = text.substring(0, i)
  }
  text = text.replace(/\[来源\d+\]（paper_id=\d+）/g, '')
  text = text.replace(/\[来源\d+\]/g, '')

  // PID → 上标序号
  const seqMap = buildSeqMap(text)
  const processed = text.replace(
    /\[PID_(\d+)\]/g,
    (_match, pid: string) => {
      const seq = seqMap.get(pid) || pid
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
