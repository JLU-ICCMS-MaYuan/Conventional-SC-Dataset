import React from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/AppShell'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import RagPage from './pages/RagPage'
import TcPredictPage from './pages/TcPredictPage'
import ChartsPage from './pages/ChartsPage'

const App: React.FC = () => (
  <Routes>
    <Route element={<AppShell />}>
      <Route path="/" element={<HomePage />} />
      <Route path="/search" element={<SearchPage />} />
      <Route path="/rag" element={<RagPage />} />
      <Route path="/tc-predict" element={<TcPredictPage />} />
      <Route path="/charts" element={<ChartsPage />} />
    </Route>
  </Routes>
)

export default App
