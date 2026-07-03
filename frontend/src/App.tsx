import React from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'
import HomePage from './pages/HomePage'
import ElementsPage from './pages/ElementsPage'
import SharePage from './pages/SharePage'
import CompoundPage from './pages/CompoundPage'
import TcPredictionPage from './pages/TcPredictionPage'
import RagPage from './pages/RagPage'
import { LoginPage, RegisterPage } from './pages/AuthPages'
import { AdminDashboardPage, AdminPapersPage, AdminUsersPage } from './pages/AdminPages'

const App: React.FC = () => {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/elements" element={<ElementsPage />} />
        <Route path="/periodic-table" element={<ElementsPage />} />
        <Route path="/share" element={<SharePage />} />
        <Route path="/compound/:elementSymbols" element={<CompoundPage />} />
        <Route path="/compound" element={<ElementsPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/admin/login" element={<LoginPage />} />
        <Route path="/admin/register" element={<RegisterPage />} />
        <Route path="/admin/dashboard" element={<AdminDashboardPage />} />
        <Route path="/admin/my-reviews" element={<AdminDashboardPage />} />
        <Route path="/admin/superadmin" element={<AdminUsersPage />} />
        <Route path="/admin/papers" element={<AdminPapersPage />} />
        <Route path="/admin/users" element={<AdminUsersPage />} />
        <Route path="/tc-pre" element={<TcPredictionPage />} />
        <Route path="/rag" element={<RagPage />} />
        <Route path="/merged" element={<Navigate to="/" replace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default App
