import React, { useState } from 'react'
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
      <div className="panel">
        <form className="grid" onSubmit={submit}>
          <label className="field">CONTCAR<input className="input" name="contcar" type="file" /></label>
          <label className="field">PDOS_H.dat<input className="input" name="pdos" type="file" /></label>
          <button className="button">运行预测</button>
        </form>
        {status && <div className="status" style={{ marginTop: 12 }}>{status}</div>}
        {result && <pre className="panel" style={{ marginTop: 12, whiteSpace: 'pre-wrap' }}>{JSON.stringify(result, null, 2)}</pre>}
      </div>
    </section>
  )
}

export default TcPredictionPage
