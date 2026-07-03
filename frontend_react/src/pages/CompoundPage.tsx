import React, { useEffect, useMemo, useState } from 'react'
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  Separator,
  Input,
  Table,
} from '@heroui/react'
import { useLocation, useParams } from 'react-router-dom'
import { getToken, postJson, requestJson } from '../lib/apiClient'

interface PaperResult {
  id?: number
  title?: string
  doi?: string
  year?: number
  journal?: string
  summary?: string
  records?: Array<{ chemical_formula?: string; tc_value?: number; pressure?: number; space_group?: string }>
}

interface AlexandriaResult {
  mat_id?: string
  formula?: string
  tc?: number
  stable?: boolean
  spacegroup?: string
}

const CompoundPage: React.FC = () => {
  const { elementSymbols = '' } = useParams()
  const location = useLocation()
  const params = new URLSearchParams(location.search)
  const mode = params.get('mode') || 'elements_combination_search'
  const formula = params.get('formula') || ''
  const elements = useMemo(() => elementSymbols.split('-').filter(Boolean), [elementSymbols])

  const [papers, setPapers] = useState<PaperResult[]>([])
  const [materials, setMaterials] = useState<AlexandriaResult[]>([])
  const [status, setStatus] = useState('正在加载本地数据...')
  const [error, setError] = useState('')

  useEffect(() => {
    const body = formula
      ? { mode: 'formula_search', formula, elements }
      : { mode, elements }

    postJson<{ papers?: PaperResult[]; data?: PaperResult[] }>('/api/papers/search-by-mode', body)
      .then((data) => {
        setPapers(data.papers || data.data || [])
        setStatus('本地数据加载完成')
      })
      .catch((err) => {
        setError(err.message)
        setStatus('')
      })
  }, [formula, mode, elements])

  async function loadAlexandria() {
    setStatus('正在加载 Alexandria 数据...')
    try {
      const data = await postJson<{ results?: AlexandriaResult[]; data?: AlexandriaResult[] }>('/api/alexandria/search', {
        elements,
        mode,
        page: 1,
        page_size: 20,
      })
      setMaterials(data.results || data.data || [])
      setStatus('Alexandria 数据加载完成')
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function loadHtsc() {
    setStatus('正在加载 HTSC-2025 数据...')
    try {
      const data = await postJson<{ results?: AlexandriaResult[]; data?: AlexandriaResult[] }>('/api/htsc2025/search', {
        elements,
        mode,
        page: 1,
        page_size: 20,
      })
      setMaterials(data.results || data.data || [])
      setStatus('HTSC-2025 数据加载完成')
    } catch (err: any) {
      setError(err.message)
    }
  }

  async function uploadPaper(file?: File) {
    if (!file) return
    if (!getToken()) {
      setError('请先登录后再上传文献')
      return
    }
    const form = new FormData()
    form.append('file', file)
    try {
      await requestJson('/api/papers/', { method: 'POST', body: form })
      setStatus('上传完成，等待审核')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="muted">Compound</p>
          <h1 className="page-title">{formula || elementSymbols || '材料体系'}</h1>
        </div>
        <div className="toolbar">
          <Button variant="outline"  onPress={loadAlexandria}>Alexandria</Button>
          <Button variant="outline"  onPress={loadHtsc}>HTSC-2025</Button>
        </div>
      </header>
      <div className="stack">
        {status && <div className="status-message">{status}</div>}
        {error && <div className="status-message error">{error}</div>}
      </div>

      <div className="grid-two" style={{ marginTop: 16 }}>
        <Card  >
          <CardHeader><h2 className="section-title">本地文献与超导记录</h2></CardHeader>
          <Separator />
          <CardContent className="stack">
            {papers.map((paper, index) => (
              <Card   className="border border-[var(--sc-border)]" key={paper.id || index}>
                <CardContent>
                <h3 className="font-semibold">{paper.title || paper.doi || `论文 ${paper.id || index + 1}`}</h3>
                <p className="muted">{[paper.journal, paper.year].filter(Boolean).join(' · ') || '来源信息待补充'}</p>
                {paper.summary && <p>{paper.summary}</p>}
                </CardContent>
              </Card>
            ))}
            {papers.length === 0 && <p className="muted">暂无本地文献结果</p>}
          </CardContent>
        </Card>

        <Card  >
          <CardHeader><h2 className="section-title">外部候选材料</h2></CardHeader>
          <Separator />
          <CardContent>
            <Table aria-label="外部候选材料"><Table.Content>
              <Table.Header>
                <Table.Column>材料</Table.Column>
                <Table.Column>Tc</Table.Column>
                <Table.Column>空间群</Table.Column>
                <Table.Column>状态</Table.Column>
              </Table.Header>
              <Table.Body>
                {materials.map((item, index) => (
                  <Table.Row key={item.mat_id || index}>
                    <Table.Cell>{item.formula || item.mat_id || '-'}</Table.Cell>
                    <Table.Cell>{item.tc ?? '-'}</Table.Cell>
                    <Table.Cell>{item.spacegroup || '-'}</Table.Cell>
                    <Table.Cell>{item.stable === undefined ? '-' : item.stable ? '稳定' : '不稳定'}</Table.Cell>
                  </Table.Row>
                ))}
                {materials.length === 0 && (
                  <Table.Row>
                    <Table.Cell colSpan={4}>点击上方按钮加载外部数据库</Table.Cell>
                  </Table.Row>
                )}
              </Table.Body>
            </Table.Content></Table>
          </CardContent>
        </Card>
      </div>

      <Card   style={{ marginTop: 16 }}>
        <CardHeader><h2 className="section-title">上传文献</h2></CardHeader>
        <Separator />
        <CardContent>
          <Input  type="file" onChange={(e) => uploadPaper(e.target.files?.[0])} />
        </CardContent>
      </Card>
    </section>
  )
}

export default CompoundPage
