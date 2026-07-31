import React from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import RagPage from './pages/RagPage'
import TcPredictPage from './pages/TcPredictPage'
import NewsPage from './pages/NewsPage'
import SharePage from './pages/share'
import KnowledgeGraphPage from './pages/KnowledgeGraphPage'
import AdminPage from './pages/AdminPage'
import UploadPage from './pages/UploadPage'

const App: React.FC = () => (
  <Routes>
    <Route element={<AppShell />}>
      <Route path="/" element={<HomePage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/share" element={<SharePage />} />
      <Route path="/upload" element={<UploadPage />} />
      <Route path="/rag" element={<RagPage />} />
      <Route path="/tc-predict" element={<TcPredictPage />} />
      <Route path="/news" element={<NewsPage />} />
      <Route path="/knowledge" element={<KnowledgeGraphPage />} />
      <Route path="/admin" element={<AdminPage />} />
    </Route>
  </Routes>
)

export default App
