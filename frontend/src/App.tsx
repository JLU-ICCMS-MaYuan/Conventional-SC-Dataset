import React, { Suspense, lazy } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { Box, CircularProgress } from '@mui/material'
import AppShell from './components/AppShell'

// 首页 — 唯一在主 bundle 中的 lazy import
const NewsPage = lazy(() => import('./pages/NewsPage'))

// 其他页面的 import() 藏在 LazyRoutes 中惰性加载
// 避免主 bundle 包含其路径，防止浏览器预取 recharts / react-markdown 等重型库
const LazyRoutes = lazy(() => import('./LazyRoutes'))

const PageLoader: React.FC = () => (
  <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '60vh' }}>
    <CircularProgress />
  </Box>
)

const App: React.FC = () => (
  <Routes>
    <Route element={<AppShell />}>
      <Route path="/" element={<Navigate to="/news" replace />} />
      <Route path="/news" element={<Suspense fallback={<PageLoader />}><NewsPage /></Suspense>} />
      <Route path="*" element={<Suspense fallback={<PageLoader />}><LazyRoutes /></Suspense>} />
    </Route>
  </Routes>
)

export default App
