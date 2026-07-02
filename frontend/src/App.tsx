import React, { Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import Layout from './components/Layout'

const HomePage = React.lazy(() => import('./pages/HomePage'))
const ElementsPage = React.lazy(() => import('./pages/ElementsPage'))
const SharePage = React.lazy(() => import('./pages/SharePage'))
const CompoundPage = React.lazy(() => import('./pages/CompoundPage'))
const TcPredictionPage = React.lazy(() => import('./pages/TcPredictionPage'))
const RagPage = React.lazy(() => import('./pages/RagPage'))
const LoginPage = React.lazy(() => import('./pages/AuthPages').then((module) => ({ default: module.LoginPage })))
const RegisterPage = React.lazy(() => import('./pages/AuthPages').then((module) => ({ default: module.RegisterPage })))
const AdminDashboardPage = React.lazy(() =>
  import('./pages/AdminPages').then((module) => ({ default: module.AdminDashboardPage })),
)
const AdminPapersPage = React.lazy(() =>
  import('./pages/AdminPages').then((module) => ({ default: module.AdminPapersPage })),
)
const AdminUsersPage = React.lazy(() =>
  import('./pages/AdminPages').then((module) => ({ default: module.AdminUsersPage })),
)

const Fallback = () => <div className="status">正在加载页面...</div>

const App: React.FC = () => {
  return (
    <Suspense fallback={<Fallback />}>
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
    </Suspense>
  )
}

export default App
