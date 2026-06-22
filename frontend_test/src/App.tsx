import React from 'react'
import { Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import RagPage from './pages/RagPage'
import CompoundPage from './pages/CompoundPage'

const App: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/rag" element={<RagPage />} />
      <Route path="/compound/:elementSymbols" element={<CompoundPage />} />
      <Route path="*" element={
        <div className="container py-5 text-center">
          <h1>SC-Wiki</h1>
          <p className="text-muted">页面未找到</p>
          <p><a href="/">← 返回首页</a></p>
        </div>
      } />
    </Routes>
  )
}

export default App
