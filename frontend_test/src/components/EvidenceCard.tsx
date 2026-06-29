import React from 'react'

interface EvidenceFragment {
  paper_id: number
  quoted_text: string
  section: string
}

interface ReviewVerdict {
  flaws: Array<{ severity: string; description: string }>
  feasibility_score: number
  revised_idea: string
  dimensions: { theory: number; synthesis: number; measurement: number }
}

interface IdeaCard {
  title: string
  fragments: EvidenceFragment[]
  reasoning_chain: string
  assumptions: string[]
  feasibility?: { overall: number; theory: number; synthesis: number; measurement: number }
}

interface EvidenceCardProps {
  idea: IdeaCard
  review?: ReviewVerdict
}

const severityColors: Record<string, string> = {
  high: '#e55',
  medium: '#f90',
  low: '#999',
}

const EvidenceCard: React.FC<EvidenceCardProps> = ({ idea, review }) => {
  return (
    <div style={{
      margin: '12px 0', border: '1px solid #e0e0e0', borderRadius: 12,
      backgroundColor: '#fafbff', overflow: 'hidden', fontSize: 13,
    }}>
      <div style={{
        padding: '10px 14px', fontWeight: 600, fontSize: 14,
        backgroundColor: '#eef1ff', color: '#3b4da0',
        borderBottom: '1px solid #dde0f0',
      }}>
        💡 {idea.title}
      </div>

      {idea.fragments.length > 0 && (
        <div style={{ padding: '10px 14px' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 6 }}>
            📎 灵感来源
          </div>
          {idea.fragments.map((f, i) => (
            <div key={i} style={{
              padding: '6px 10px', marginBottom: 6,
              backgroundColor: '#f5f5f5', borderRadius: 6,
              borderLeft: '3px solid #4d6bfe',
            }}>
              <div style={{ fontStyle: 'italic', color: '#333', lineHeight: 1.6 }}>
                &ldquo;{f.quoted_text}&rdquo;
              </div>
              <div style={{ fontSize: 11, color: '#999', marginTop: 4 }}>
                [PID_{f.paper_id}] — {f.section}
              </div>
            </div>
          ))}
        </div>
      )}

      {idea.reasoning_chain && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 4 }}>
            🔗 推理链
          </div>
          <div style={{ color: '#444', lineHeight: 1.6 }}>{idea.reasoning_chain}</div>
        </div>
      )}

      {idea.assumptions.length > 0 && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0f0f0' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#666', marginBottom: 4 }}>
            ⚠️ 假设前提
          </div>
          <ul style={{ margin: 0, paddingLeft: 18 }}>
            {idea.assumptions.map((a, i) => (
              <li key={i} style={{ color: '#666', marginBottom: 2 }}>{a}</li>
            ))}
          </ul>
        </div>
      )}

      {review && (
        <div style={{ padding: '10px 14px', borderTop: '1px solid #f0e0e0', backgroundColor: '#fffaf5' }}>
          <div style={{ fontWeight: 600, fontSize: 12, color: '#e55', marginBottom: 6 }}>
            🔍 审稿意见 (可行性: {'★'.repeat(review.feasibility_score)}{'☆'.repeat(5 - review.feasibility_score)})
          </div>
          {review.flaws.map((f, i) => (
            <div key={i} style={{
              padding: '4px 8px', marginBottom: 4,
              backgroundColor: '#fff', borderRadius: 4,
              borderLeft: `3px solid ${severityColors[f.severity] || '#999'}`,
              fontSize: 12,
            }}>
              <span style={{
                display: 'inline-block', padding: '1px 6px', borderRadius: 3,
                backgroundColor: severityColors[f.severity] || '#999',
                color: '#fff', fontSize: 10, marginRight: 6,
              }}>
                {f.severity.toUpperCase()}
              </span>
              {f.description}
            </div>
          ))}
          <div style={{ display: 'flex', gap: 16, marginTop: 8, fontSize: 12 }}>
            <span>理论: {'★'.repeat(review.dimensions.theory)}</span>
            <span>合成: {'★'.repeat(review.dimensions.synthesis)}</span>
            <span>测量: {'★'.repeat(review.dimensions.measurement)}</span>
          </div>
        </div>
      )}
    </div>
  )
}

export default EvidenceCard
export type { IdeaCard, ReviewVerdict, EvidenceFragment }
