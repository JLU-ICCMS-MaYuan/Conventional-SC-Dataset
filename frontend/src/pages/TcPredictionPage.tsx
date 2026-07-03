import React, { useState } from 'react'
import { Button, Card, CardContent, CardHeader, Separator, Input } from '@heroui/react'
import { requestJson } from '../lib/apiClient'

const TcPredictionPage: React.FC = () => {
  const [status, setStatus] = useState('')
  const [result, setResult] = useState<any>(null)

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setStatus('正在预测...')
    setResult(null)
    try {
      const data = await requestJson('/api/tc-predict', { method: 'POST', body: form })
      setResult(data)
      setStatus('预测完成')
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="muted">Tc Prediction</p>
          <h1 className="page-title">超导 Tc 预测</h1>
        </div>
      </header>
      <Card  >
        <CardHeader><h2 className="section-title">输入结构与态密度文件</h2></CardHeader>
        <Separator />
        <CardContent className="stack">
        <form className="stack" onSubmit={submit}>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            CONTCAR
            <Input name="contcar" type="file" />
          </label>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            PDOS_H.dat
            <Input name="pdos" type="file" />
          </label>
          <Button variant="primary"  type="submit">运行预测</Button>
        </form>
        {status && <div className="status-message">{status}</div>}
        {result && (
          <Card   className="border border-[var(--sc-border)]">
            <CardContent>
              <pre className="whitespace-pre-wrap text-sm">{JSON.stringify(result, null, 2)}</pre>
            </CardContent>
          </Card>
        )}
        </CardContent>
      </Card>
    </section>
  )
}

export default TcPredictionPage
