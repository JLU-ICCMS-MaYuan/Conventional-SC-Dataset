import React, { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button, Card, CardContent, CardHeader, Input, Separator } from '@heroui/react'
import { getToken, requestJson } from '../lib/apiClient'

type DownloadScope = 'formula' | 'elements' | 'all'
type ElementMode = 'elements_combination_search' | 'elements_exact_search' | 'elements_contained_search'

const scopeOptions: Array<{ key: DownloadScope; label: string }> = [
  { key: 'formula', label: '按化学式检索' },
  { key: 'elements', label: '按元素组合检索' },
  { key: 'all', label: '全库下载' },
]

const modeOptions: Array<{ key: ElementMode; label: string }> = [
  { key: 'elements_combination_search', label: '选择元素的组合' },
  { key: 'elements_exact_search', label: '仅包含选择元素' },
  { key: 'elements_contained_search', label: '包含所选元素' },
]

function parseElements(value: string) {
  return value
    .replace(/[，、\s]+/g, '-')
    .split('-')
    .map((item) => item.trim())
    .filter(Boolean)
}

const SharePage: React.FC = () => {
  const navigate = useNavigate()
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [scope, setScope] = useState<DownloadScope>('formula')
  const [query, setQuery] = useState('')
  const [mode, setMode] = useState<ElementMode>('elements_combination_search')
  const [status, setStatus] = useState('')
  const [isUploading, setIsUploading] = useState(false)

  function download(format: 'json' | 'ris') {
    const trimmedQuery = query.trim()
    const params = new URLSearchParams({ format })

    if (scope === 'all') {
      params.set('scope', 'all')
    } else if (scope === 'formula') {
      if (!trimmedQuery) {
        setStatus('请先输入化学式')
        return
      }
      params.set('scope', 'search')
      params.set('mode', 'formula_search')
      params.set('formula', trimmedQuery)
    } else {
      const elements = parseElements(trimmedQuery)
      if (elements.length === 0) {
        setStatus('请先输入元素组合')
        return
      }
      params.set('scope', 'search')
      params.set('mode', mode)
      params.set('elements', elements.join(','))
    }

    setStatus('')
    window.location.href = `/api/papers/share-export?${params.toString()}`
  }

  async function uploadPdf(file?: File) {
    if (!file) return
    const token = getToken()
    if (!token) {
      setStatus('请先登录后再上传 PDF')
      if (fileInputRef.current) fileInputRef.current.value = ''
      return
    }

    const form = new FormData()
    form.append('file', file)
    setIsUploading(true)
    setStatus('正在上传 PDF...')

    try {
      const data = await requestJson<{ ok?: boolean; data?: { title?: string } }>('/api/rag/upload-pdf', {
        method: 'POST',
        body: form,
      })
      if (data.ok === false) {
        throw new Error('上传失败')
      }
      setStatus(`上传完成：${data.data?.title || file.name}`)
    } catch (err: any) {
      setStatus(`上传失败：${err.message || '未知错误'}`)
    } finally {
      setIsUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  function manualUpload() {
    if (!getToken()) {
      setStatus('请先登录后再手动填写数据')
      navigate('/login')
      return
    }
    navigate('/compound/H?mode=elements_contained_search&upload=1')
  }

  return (
    <section className="page">
      <header className="page-header">
        <div>
          <p className="page-kicker">SC Share</p>
          <h1 className="page-title">超导分享</h1>
        </div>
        <p className="muted">获取你需要的超导文献数据，也分享新的超导体系进展。</p>
      </header>

      <div className="grid-two">
        <Card>
          <CardHeader className="flex flex-col items-start gap-1">
            <h2 className="section-title">获取数据</h2>
            <p className="section-subtitle">按化学式或元素组合下载数据，也可以导出全库文献。</p>
          </CardHeader>
          <Separator />
          <CardContent className="stack">
            <div className="form-field">
              <span>下载方式</span>
              <div className="segmented-control" role="group" aria-label="下载方式">
                {scopeOptions.map((item) => (
                  <Button
                    key={item.key}
                    variant={scope === item.key ? 'primary' : 'outline'}
                    onPress={() => setScope(item.key)}
                  >
                    {item.label}
                  </Button>
                ))}
              </div>
            </div>

            {scope !== 'all' && (
              <label className="form-field">
                <span>{scope === 'formula' ? '化学式' : '元素'}</span>
                <Input
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                  placeholder={scope === 'formula' ? 'LaH10、FeSe1-xTex、Y-Ba-Cu-O' : 'H-La 或 H La Mg'}
                />
              </label>
            )}

            {scope === 'elements' && (
              <div className="form-field">
                <span>元素筛选方式</span>
                <div className="segmented-control" role="group" aria-label="元素筛选方式">
                  {modeOptions.map((item) => (
                    <Button
                      key={item.key}
                      variant={mode === item.key ? 'primary' : 'outline'}
                      onPress={() => setMode(item.key)}
                    >
                      {item.label}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            <div className="toolbar">
              <Button variant="primary" onPress={() => download('json')}>下载 JSON 数据</Button>
              <Button variant="outline" onPress={() => download('ris')}>下载 RIS 引文</Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-col items-start gap-1">
            <h2 className="section-title">分享进展</h2>
            <p className="section-subtitle">上传论文 PDF，或手动填写你发现的超导体系和 Tc 数据。</p>
          </CardHeader>
          <Separator />
          <CardContent className="stack">
            <div className="share-upload-actions">
              <Button
                variant="primary"
                isDisabled={isUploading}
                onPress={() => fileInputRef.current?.click()}
              >
                从 PDF 上传
              </Button>
              <Button variant="outline" onPress={manualUpload}>手动填写数据</Button>
            </div>
            <input
              ref={fileInputRef}
              className="sr-only-file"
              type="file"
              accept=".pdf"
              onChange={(event) => uploadPdf(event.target.files?.[0])}
            />
            {status && <div className="status-message">{status}</div>}
          </CardContent>
        </Card>
      </div>
    </section>
  )
}

export default SharePage
