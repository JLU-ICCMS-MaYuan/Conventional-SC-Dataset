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
