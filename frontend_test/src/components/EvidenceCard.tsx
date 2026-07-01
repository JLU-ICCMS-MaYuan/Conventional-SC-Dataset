import React from 'react'

/* ========== 类型定义 ========== */

export interface EvidenceFragment {
  paper_id: number
  quoted_text: string
  section: string
}

export interface ReviewVerdict {
  flaws: Array<{ severity: string; description: string }>
  feasibility_score: number
  revised_idea: string
  dimensions: { theory: number; synthesis: number; measurement: number }
}

export interface IdeaCard {
  title: string
  fragments: EvidenceFragment[]
  reasoning_chain: string
  assumptions: string[]
  feasibility?: { overall: number; theory: number; synthesis: number; measurement: number }
}

interface EvidenceCardProps {
  idea: IdeaCard
  review?: ReviewVerdict
  paperSeqMap?: Record<string, number>
}

/* ========== 辅助组件 ========== */

const severityBadge: Record<string, React.CSSProperties> = {
  high: { backgroundColor: '#dc3545', color: '#fff' },
  medium: { backgroundColor: '#f59e0b', color: '#fff' },
  low: { backgroundColor: '#94a3b8', color: '#fff' },
}

function Stars({ n, max = 5 }: { n: number; max?: number }) {
  return (
    <span style={{ color: '#f59e0b', letterSpacing: 1 }}>
      {'★'.repeat(n)}
      <span style={{ color: '#d4d4d4' }}>{'★'.repeat(max - n)}</span>
    </span>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div style={s.label}>{children}</div>
  )
}

/* ========== 主组件 ========== */

const EvidenceCard: React.FC<EvidenceCardProps> = ({ idea, review, paperSeqMap }) => {
  return (
    <div style={s.card}>
      {/* 标题栏 */}
      <div style={s.header}>
        <span style={{ fontSize: 16, lineHeight: 1 }}>💡</span>
        <span style={{ flex: 1 }}>{idea.title}</span>
        {idea.feasibility && (
          <span style={{ fontSize: 12, fontWeight: 400, color: '#94a3b8' }}>
            可行性 <Stars n={idea.feasibility.overall} />
          </span>
        )}
      </div>

      {/* 灵感来源 — 引文片段 */}
      {idea.fragments.length > 0 && (
        <div style={s.section}>
          <SectionLabel>📎 灵感来源</SectionLabel>
          {idea.fragments.map((f, i) => (
            <div key={i} style={s.fragment}>
              <div style={s.quote}>
                &ldquo;{f.quoted_text}&rdquo;
              </div>
              <div style={s.fragmentMeta}>
                <span style={s.pidTag}>
                  {paperSeqMap?.[String(f.paper_id)] !== undefined
                    ? `[${paperSeqMap[String(f.paper_id)]}]`
                    : `PID_${f.paper_id}`}
                </span>
                <span style={{ color: '#94a3b8' }}>{f.section}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 推理链 */}
      {idea.reasoning_chain && (
        <div style={s.section}>
          <SectionLabel>🔗 推理链</SectionLabel>
          <div style={s.textBlock}>{idea.reasoning_chain}</div>
        </div>
      )}

      {/* 假设前提 */}
      {idea.assumptions.length > 0 && (
        <div style={s.section}>
          <SectionLabel>⚠️ 假设前提</SectionLabel>
          <ul style={s.assumptionList}>
            {idea.assumptions.map((a, i) => (
              <li key={i} style={s.assumptionItem}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 双角色审稿意见 */}
      {review && (
        <div style={s.review}>
          <div style={s.reviewHeader}>
            <span>🔍 审稿意见</span>
            <span style={{ fontWeight: 400, fontSize: 12 }}>
              综合可行性 <Stars n={review.feasibility_score} />
            </span>
          </div>

          {/* 缺陷列表 */}
          {review.flaws.map((f, i) => (
            <div key={i} style={s.flawItem}>
              <span style={{ ...s.flawBadge, ...(severityBadge[f.severity] || severityBadge.low) }}>
                {f.severity === 'high' ? '严重' : f.severity === 'medium' ? '中等' : '轻微'}
              </span>
              <span style={{ color: '#475569', lineHeight: 1.55 }}>{f.description}</span>
            </div>
          ))}

          {/* 三维评分 */}
          <div style={s.dimensionBar}>
            {([
              { key: 'theory', label: '理论自洽' },
              { key: 'synthesis', label: '合成可达' },
              { key: 'measurement', label: '测量可验' },
            ] as const).map(({ key, label }) => (
              <div key={key} style={s.dimensionItem}>
                <span style={{ fontSize: 11, color: '#94a3b8' }}>{label}</span>
                <Stars n={review.dimensions[key]} max={5} />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

/* ========== 样式表 ========== */

const s: Record<string, React.CSSProperties> = {
  card: {
    margin: '14px 0',
    border: '1px solid #f0f0f0',
    borderRadius: 10,
    backgroundColor: '#fff',
    boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
    overflow: 'hidden',
    fontSize: 13,
  },

  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    padding: '10px 14px',
    fontWeight: 700,
    fontSize: 14,
    backgroundColor: '#fff',
    color: '#1e3a5f',
    borderLeft: '3px solid #4d6bfe',
    margin: '-1px',
  },

  section: {
    padding: '10px 14px',
  },

  label: {
    fontWeight: 700,
    fontSize: 11,
    color: '#64748b',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: '0.4px',
  } as React.CSSProperties,

  fragment: {
    padding: '8px 10px',
    marginBottom: 8,
    backgroundColor: '#f8fafc',
    borderRadius: 6,
    borderLeft: '3px solid #4d6bfe',
  },

  quote: {
    fontStyle: 'italic',
    color: '#334155',
    lineHeight: 1.7,
    marginBottom: 6,
  },

  fragmentMeta: {
    fontSize: 11,
    color: '#94a3b8',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },

  pidTag: {
    display: 'inline-block',
    padding: '1px 8px',
    borderRadius: 10,
    backgroundColor: '#eef1ff',
    color: '#4d6bfe',
    fontWeight: 500,
    fontSize: 10,
  },

  textBlock: {
    color: '#334155',
    lineHeight: 1.7,
    whiteSpace: 'pre-wrap',
  } as React.CSSProperties,

  assumptionList: {
    margin: 0,
    paddingLeft: 18,
  },

  assumptionItem: {
    color: '#64748b',
    marginBottom: 3,
    lineHeight: 1.6,
  },

  review: {
    borderTop: '2px solid #fed7aa',
    backgroundColor: '#fffbf5',
    padding: '10px 14px',
  },

  reviewHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontWeight: 700,
    fontSize: 12,
    color: '#c2410c',
    marginBottom: 10,
  },

  flawItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 8,
    padding: '6px 0',
    borderBottom: '1px solid #fef3c7',
  },

  flawBadge: {
    display: 'inline-block',
    padding: '1px 8px',
    borderRadius: 3,
    fontSize: 10,
    fontWeight: 600,
    flexShrink: 0,
    marginTop: 1,
    textAlign: 'center',
    minWidth: 36,
  },

  dimensionBar: {
    display: 'flex',
    gap: 24,
    marginTop: 10,
    padding: '8px 10px',
    backgroundColor: '#f1f5f9',
    borderRadius: 6,
    fontSize: 12,
  },

  dimensionItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    alignItems: 'center',
  } as React.CSSProperties,
}

export default EvidenceCard
