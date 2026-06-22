# 前端 React 迁移实现计划（阶段 1：RAG 页面 + 脚手架）

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 `frontend_test/` 搭建 Vite + React + TypeScript 脚手架，实现 RAG 对话页作为第一个 React 页面。

**Architecture:** Vite 开发服务器 proxy `/api/*` 到后端 FastAPI `:8000`。React Context 管理认证状态。react-router-dom 负责路由。react-bootstrap 保持现有 Bootstrap 5 外观。

**Tech Stack:** Vite 5 + React 18 + TypeScript + react-router-dom + react-bootstrap + bootstrap

---

### Task 1: 初始化 Vite + React + TypeScript 项目

**Files:**
- Create: `frontend_test/` （Vite 脚手架生成的全部文件）

- [ ] **Step 1: 创建 Vite 项目**

```bash
cd /home/work/workshop/git/SC-Wiki
conda run -n Conventional-SC-Dataset npm create vite@latest frontend_test -- --template react-ts
```

Expected: `frontend_test/` 目录创建成功。

- [ ] **Step 2: 安装依赖**

```bash
cd frontend_test
conda run -n Conventional-SC-Dataset npm install
conda run -n Conventional-SC-Dataset npm install react-router-dom react-bootstrap bootstrap
```

Expected: 所有包安装成功。

- [ ] **Step 3: 验证脚手架可运行**

```bash
cd frontend_test && conda run -n Conventional-SC-Dataset npm run dev
```

Expected: Vite 启动在 `localhost:5173`。

- [ ] **Step 4: Commit**

```bash
git add frontend_test/
git commit -m "feat: scaffold Vite + React + TypeScript project"
```

---

### Task 2: 配置 Vite proxy 和路径别名

**Files:**
- Modify: `frontend_test/vite.config.ts`

- [ ] **Step 1: 修改 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
```

- [ ] **Step 2: 验证 proxy 工作**

```bash
# 确保 FastAPI 在 :8000 运行
# 然后在另一个终端启动 Vite
cd frontend_test && conda run -n Conventional-SC-Dataset npm run dev
```

访问 `http://localhost:5173/api/rag/health`，应返回 JSON。

- [ ] **Step 3: Commit**

```bash
git add frontend_test/vite.config.ts
git commit -m "chore: configure Vite proxy to backend :8000"
```

---

### Task 3: 创建认证 Context

**Files:**
- Create: `frontend_test/src/context/AuthContext.tsx`
- Modify: `frontend_test/src/main.tsx`

- [ ] **Step 1: 创建 AuthContext.tsx**

```typescript
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

interface User {
  id: number
  username: string
  email: string
  role: string
}

interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (token: string, user: User) => void
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: () => {},
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem('token')
    const savedUser = localStorage.getItem('user')
    if (savedToken && savedUser) {
      try {
        setToken(savedToken)
        setUser(JSON.parse(savedUser))
      } catch {
        localStorage.removeItem('token')
        localStorage.removeItem('user')
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback((newToken: string, newUser: User) => {
    localStorage.setItem('token', newToken)
    localStorage.setItem('user', JSON.stringify(newUser))
    setToken(newToken)
    setUser(newUser)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
```

- [ ] **Step 2: 修改 main.tsx 包裹 AuthProvider**

```typescript
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import App from './App'
import 'bootstrap/dist/css/bootstrap.min.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <App />
      </AuthProvider>
    </BrowserRouter>
  </React.StrictMode>
)
```

- [ ] **Step 3: Commit**

```bash
git add frontend_test/src/context/AuthContext.tsx frontend_test/src/main.tsx
git commit -m "feat: add AuthContext with localStorage persistence"
```

---

### Task 4: 创建 API 封装

**Files:**
- Create: `frontend_test/src/lib/api.ts`

- [ ] **Step 1: 创建 api.ts**

```typescript
const BASE = ''

async function request<T = any>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${BASE}${url}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = data.detail || data
    const message = detail.message || detail.detail || `请求失败：HTTP ${response.status}`
    throw new Error(message)
  }

  return data
}

export const api = {
  get: <T = any>(url: string) => request<T>(url),

  post: <T = any>(url: string, body?: any) =>
    request<T>(url, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  postStream: (url: string, body: any) =>
    fetch(`${BASE}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
      body: JSON.stringify(body),
    }),
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend_test/src/lib/api.ts
git commit -m "feat: add API helper with auth and error handling"
```

---

### Task 5: 创建导航栏组件

**Files:**
- Create: `frontend_test/src/components/NavBar.tsx`

- [ ] **Step 1: 创建 NavBar.tsx**

```typescript
import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Navbar, Nav, Container, Button } from 'react-bootstrap'
import { useAuth } from '../context/AuthContext'

const NavBar: React.FC = () => {
  const { user, logout } = useAuth()
  const location = useLocation()

  return (
    <Navbar bg="white" expand="lg" className="border-bottom shadow-sm sticky-top">
      <Container fluid>
        <Navbar.Brand as={Link} to="/" className="fw-bold">
          超导文献数据库
        </Navbar.Brand>
        <Navbar.Toggle />
        <Navbar.Collapse>
          <Nav className="me-auto">
            <Nav.Link as={Link} to="/rag" active={location.pathname === '/rag'}>
              AI 助手
            </Nav.Link>
            <Nav.Link as={Link} to="/compound" active={location.pathname.startsWith('/compound')}>
              化合物
            </Nav.Link>
          </Nav>
          <Nav>
            {user ? (
              <>
                <Navbar.Text className="me-3">{user.username}</Navbar.Text>
                <Button variant="outline-secondary" size="sm" onClick={logout}>
                  退出
                </Button>
              </>
            ) : (
              <Nav.Link as={Link} to="/login">
                登录
              </Nav.Link>
            )}
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  )
}

export default NavBar
```

- [ ] **Step 2: Commit**

```bash
git add frontend_test/src/components/NavBar.tsx
git commit -m "feat: add NavBar component"
```

---

### Task 6: 创建 RAG 对话页

**Files:**
- Create: `frontend_test/src/pages/RagPage.tsx`
- Create: `frontend_test/src/components/ChatMessage.tsx`

- [ ] **Step 1: 创建 ChatMessage.tsx**

```typescript
import React from 'react'
import { Card } from 'react-bootstrap'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
}

const ChatMessage: React.FC<ChatMessageProps> = ({ role, content }) => {
  const isUser = role === 'user'
  return (
    <div className={`d-flex mb-3 ${isUser ? 'justify-content-end' : 'justify-content-start'}`}>
      <Card
        bg={isUser ? 'primary' : 'light'}
        text={isUser ? 'white' : 'dark'}
        className="shadow-sm"
        style={{ maxWidth: '80%', borderRadius: 16 }}
      >
        <Card.Body className="py-2 px-3">
          {isUser ? `🙋 ${content}` : content}
        </Card.Body>
      </Card>
    </div>
  )
}

export default ChatMessage
```

- [ ] **Step 2: 创建 RagPage.tsx**

```typescript
import React, { useState, useRef, useEffect } from 'react'
import { Container, Form, Button, Spinner, Alert, Row, Col, Card } from 'react-bootstrap'
import ChatMessage from '../components/ChatMessage'
import NavBar from '../components/NavBar'
import { api } from '../lib/api'

interface RagMessage {
  role: 'user' | 'assistant'
  content: string
}

interface RagStats {
  papers: number
  superconductors: number
  records: number
  chunks: number
  chroma_chunks: number
}

const RagPage: React.FC = () => {
  const [messages, setMessages] = useState<RagMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState<RagStats | null>(null)
  const [healthMsg, setHealthMsg] = useState('')
  const chatBoxRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    api.get('/api/rag/health').then((d: any) => {
      setHealthMsg(d.message || '')
    }).catch(() => setHealthMsg('AI 文献助手不可用'))

    api.get('/api/rag/stats').then((d: any) => {
      if (d.data) setStats(d.data)
    }).catch(() => {})
  }, [])

  useEffect(() => {
    chatBoxRef.current?.scrollTo(0, chatBoxRef.current.scrollHeight)
  }, [messages])

  const handleSend = async () => {
    const question = input.trim()
    if (!question || loading) return

    const userMsg: RagMessage = { role: 'user', content: question }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    let fullAnswer = ''

    try {
      const response = await api.postStream('/api/rag/chat/stream', {
        question,
        top_k: 15,
        rerank_top_k: 5,
        history: messages,
      })

      if (!response.ok || !response.body) throw new Error(`HTTP ${response.status}`)

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      const assistantMsg: RagMessage = { role: 'assistant', content: '' }
      setMessages((prev) => [...prev, assistantMsg])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const parts = buffer.split('\n\n')
        buffer = parts.pop() || ''

        for (const part of parts) {
          let eventType = 'message'
          const dataLines: string[] = []
          part.split('\n').forEach((line) => {
            if (line.startsWith('event:')) eventType = line.slice(6).trim()
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trim())
          })
          if (dataLines.length === 0) continue

          try {
            const data = JSON.parse(dataLines.join('\n'))
            if (eventType === 'token') {
              fullAnswer += typeof data === 'string' ? data : String(data || '')
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: fullAnswer }
                return updated
              })
            } else if (eventType === 'error') {
              throw new Error(data.message || 'AI 错误')
            }
          } catch {
            // 跳过无法解析的行
          }
        }
      }

      if (!fullAnswer) {
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: '抱歉，未获取到回答。' }
          return updated
        })
      }
    } catch (err: any) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: `❌ ${err.message}` }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
      <NavBar />
      <Container className="py-4" style={{ maxWidth: 800 }}>
        {healthMsg && (
          <Alert variant={healthMsg.includes('已就绪') ? 'success' : 'warning'} className="mb-3 py-2 text-center small">
            {healthMsg}
          </Alert>
        )}

        {stats && (
          <Row className="g-2 mb-4 text-center">
            {[
              { label: '论文', value: stats.papers },
              { label: '超导体', value: stats.superconductors },
              { label: '记录', value: stats.records },
              { label: '片段', value: stats.chunks },
            ].map((s) => (
              <Col key={s.label} xs={3}>
                <Card className="shadow-sm h-100">
                  <Card.Body className="py-2">
                    <div className="fs-5 fw-bold">{s.value?.toLocaleString() ?? '-'}</div>
                    <small className="text-muted">{s.label}</small>
                  </Card.Body>
                </Card>
              </Col>
            ))}
          </Row>
        )}

        <div
          ref={chatBoxRef}
          className="border rounded-3 bg-white p-3 mb-3"
          style={{ minHeight: 400, maxHeight: '60vh', overflowY: 'auto' }}
        >
          {messages.length === 0 && (
            <div className="text-center text-muted py-5">
              <p className="fs-5">💬 AI 文献助手</p>
              <p>基于 638 篇超导论文，问任何关于氢化物超导的问题</p>
            </div>
          )}
          {messages.map((msg, i) => (
            <ChatMessage key={i} role={msg.role} content={msg.content} />
          ))}
          {loading && (
            <div className="d-flex justify-content-start mb-3">
              <Card bg="light" className="shadow-sm" style={{ borderRadius: 16 }}>
                <Card.Body className="py-2 px-4">
                  <Spinner animation="border" size="sm" className="me-2" />
                  思考中...
                </Card.Body>
              </Card>
            </div>
          )}
        </div>

        <Form
          onSubmit={(e) => { e.preventDefault(); handleSend() }}
          className="d-flex gap-2"
        >
          <Form.Control
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="问一个超导问题，例如「LaH10 的 Tc 是多少？」"
            disabled={loading}
            style={{ borderRadius: 24 }}
          />
          <Button type="submit" disabled={loading || !input.trim()} style={{ borderRadius: 24 }}>
            发送
          </Button>
        </Form>
      </Container>
    </>
  )
}

export default RagPage
```

- [ ] **Step 3: Commit**

```bash
git add frontend_test/src/pages/RagPage.tsx frontend_test/src/components/ChatMessage.tsx
git commit -m "feat: add RAG chat page with streaming support"
```

---

### Task 7: 创建 App.tsx 路由入口

**Files:**
- Modify: `frontend_test/src/App.tsx`
- Delete: `frontend_test/src/App.css`
- Delete: `frontend_test/src/index.css`（如果存在）

- [ ] **Step 1: 重写 App.tsx**

```typescript
import React from 'react'
import { Routes, Route } from 'react-router-dom'
import RagPage from './pages/RagPage'

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/rag" element={<RagPage />} />
      <Route path="*" element={
        <div className="container py-5 text-center">
          <h1>SC-Wiki</h1>
          <p className="text-muted">React 前端加载中...</p>
          <p><a href="/rag">→ AI 助手</a></p>
        </div>
      } />
    </Routes>
  )
}

export default App
```

- [ ] **Step 2: 清理默认样式文件**

```bash
rm -f frontend_test/src/App.css frontend_test/src/index.css
```

确保 `main.tsx` 不导入已删除的 CSS 文件。

- [ ] **Step 3: Commit**

```bash
git add frontend_test/src/App.tsx
git commit -m "feat: add App routing with RAG page entry"
```

---

### Task 8: 端到端验证

- [ ] **Step 1: 确保 FastAPI 在 :8000 运行**

```bash
RAG_DATA_ROOT="/home/work/workshop/git/Conventional-SC-Dataset-talk" PYTHONPATH="." conda run -n Conventional-SC-Dataset uvicorn backend.main:app --host 0.0.0.0 --port 8000
```

- [ ] **Step 2: 启动 Vite 并验证**

```bash
cd frontend_test && conda run -n Conventional-SC-Dataset npm run dev
```

打开 `http://localhost:5173/rag`：
- 应看到导航栏（AI 助手、化合物）
- 应看到统计卡片（论文/超导体/记录/片段）
- 输入问题应流式返回回答

- [ ] **Step 3: 验证 API proxy**

```bash
curl http://localhost:5173/api/rag/health
```

Expected: 返回 JSON 健康状态。

- [ ] **Step 4: Commit**

```bash
git add frontend_test/
git commit -m "chore: finalize React scaffolding verification"
```

---

### 验证清单

- [ ] `http://localhost:5173/rag` 页面正常加载
- [ ] 导航栏显示 "AI 助手"、"化合物" 链接
- [ ] 健康状态提示正确
- [ ] 统计卡片显示数据
- [ ] 输入问题 → 流式回答正常
- [ ] `loading` 状态有 spinner
- [ ] 错误状态有红色提示
- [ ] `/api/rag/health` 通过 proxy 可达
- [ ] 未登录时不崩溃（显示登录链接）
