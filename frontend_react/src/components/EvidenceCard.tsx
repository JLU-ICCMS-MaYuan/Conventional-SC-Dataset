import React from 'react'
import { Card, CardContent, CardHeader, Chip, Separator } from '@heroui/react'

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

const severityColor: Record<string, 'danger' | 'warning' | 'default'> = {
  high: 'danger',
  medium: 'warning',
  low: 'default',
}

function Stars({ n, max = 5 }: { n: number; max?: number }) {
  return (
    <span className="text-xs text-amber-500">
      {'★'.repeat(n)}
      <span className="text-default-300">{'★'.repeat(max - n)}</span>
    </span>
  )
}

const EvidenceCard: React.FC<EvidenceCardProps> = ({ idea, review, paperSeqMap }) => {
  return (
    <Card   className="my-4 border border-[var(--sc-border)]">
      <CardHeader className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-[var(--sc-text)]">{idea.title}</h3>
          {idea.feasibility && (
            <p className="text-xs text-[var(--sc-muted)]">可行性 <Stars n={idea.feasibility.overall} /></p>
          )}
        </div>
        <Chip color="accent" variant="soft">灵感</Chip>
      </CardHeader>
      <Separator />
      <CardContent className="stack text-sm">
        {idea.fragments.length > 0 && (
          <section className="stack">
            <h4 className="font-semibold text-[var(--sc-muted)]">灵感来源</h4>
            {idea.fragments.map((fragment, index) => (
              <Card key={`${fragment.paper_id}-${index}`}   className="border border-[var(--sc-border)] bg-[var(--sc-bg-soft)]">
                <CardContent className="gap-2">
                  <blockquote className="m-0 leading-7 text-[var(--sc-text)]">&ldquo;{fragment.quoted_text}&rdquo;</blockquote>
                  <div className="flex items-center gap-2 text-xs text-[var(--sc-muted)]">
                    <Chip size="sm" color="accent" variant="soft">
                      {paperSeqMap?.[String(fragment.paper_id)] !== undefined
                        ? `[${paperSeqMap[String(fragment.paper_id)]}]`
                        : `PID_${fragment.paper_id}`}
                    </Chip>
                    <span>{fragment.section}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </section>
        )}

        {idea.reasoning_chain && (
          <section className="stack">
            <h4 className="font-semibold text-[var(--sc-muted)]">推理链</h4>
            <p className="whitespace-pre-wrap leading-7">{idea.reasoning_chain}</p>
          </section>
        )}

        {idea.assumptions.length > 0 && (
          <section className="stack">
            <h4 className="font-semibold text-[var(--sc-muted)]">假设前提</h4>
            <ul className="m-0 grid gap-1 pl-5 text-[var(--sc-muted)]">
              {idea.assumptions.map((assumption, index) => (
                <li key={`${assumption}-${index}`}>{assumption}</li>
              ))}
            </ul>
          </section>
        )}

        {review && (
          <section className="stack rounded-sm border border-amber-200 bg-amber-50 p-3">
            <div className="flex items-center justify-between gap-3">
              <h4 className="font-semibold text-amber-700">审稿意见</h4>
              <span className="text-xs text-amber-700">综合可行性 <Stars n={review.feasibility_score} /></span>
            </div>
            {review.flaws.map((flaw, index) => (
              <div className="flex items-start gap-2" key={`${flaw.severity}-${index}`}>
                <Chip color={severityColor[flaw.severity] || 'default'} size="sm" variant="soft">
                  {flaw.severity === 'high' ? '严重' : flaw.severity === 'medium' ? '中等' : '轻微'}
                </Chip>
                <span className="leading-6 text-slate-700">{flaw.description}</span>
              </div>
            ))}
            <div className="grid-three">
              {([
                { key: 'theory', label: '理论自洽' },
                { key: 'synthesis', label: '合成可达' },
                { key: 'measurement', label: '测量可验' },
              ] as const).map(({ key, label }) => (
                <div className="rounded-sm bg-white p-2 text-center" key={key}>
                  <div className="text-xs text-[var(--sc-muted)]">{label}</div>
                  <Stars n={review.dimensions[key]} />
                </div>
              ))}
            </div>
          </section>
        )}
      </CardContent>
    </Card>
  )
}

export default EvidenceCard
