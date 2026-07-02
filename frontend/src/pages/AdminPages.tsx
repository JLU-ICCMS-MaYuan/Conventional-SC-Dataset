import React, { useCallback, useEffect, useState } from 'react'
import { putJson, requestJson } from '../lib/apiClient'

interface Paper {
  id: number
  title?: string
  doi?: string
  journal?: string
  year?: number
  review_status?: string
}

interface UserRow {
  id: number
  username?: string
  email?: string
  real_name?: string
  role?: string
  is_admin?: boolean
  is_superadmin?: boolean
  is_approved?: boolean
}

export const AdminDashboardPage: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([])
  const [status, setStatus] = useState('正在加载待审核文献...')

  async function load() {
    try {
      const data = await requestJson<{ papers?: Paper[]; data?: Paper[] }>('/api/admin/papers/unreviewed?limit=30&offset=0')
      setPapers(data.papers || data.data || [])
      setStatus('')
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  async function review(id: number, approved: boolean) {
    try {
      await requestJson(`/api/admin/papers/${id}/review`, {
        method: 'POST',
        body: JSON.stringify({ approved, status: approved ? 'approved' : 'rejected' }),
      })
      setPapers((prev) => prev.filter((paper) => paper.id !== id))
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <section className="page">
      <header className="page-header"><h1 className="page-title">审核面板</h1></header>
      {status && <div className="status">{status}</div>}
      <PaperTable papers={papers} actions={(paper) => (
        <div className="toolbar">
          <button className="button" onClick={() => review(paper.id, true)}>通过</button>
          <button className="button danger" onClick={() => review(paper.id, false)}>拒绝</button>
        </div>
      )} />
    </section>
  )
}

export const AdminPapersPage: React.FC = () => {
  const [papers, setPapers] = useState<Paper[]>([])
  const [keyword, setKeyword] = useState('')
  const [status, setStatus] = useState('')

  const search = useCallback(async () => {
    setStatus('正在加载文献...')
    try {
      const params = new URLSearchParams({ limit: '50' })
      if (keyword) params.set('keyword', keyword)
      const data = await requestJson<{ papers?: Paper[]; data?: Paper[] }>(`/api/admin/papers?${params.toString()}`)
      setPapers(data.papers || data.data || [])
      setStatus('')
    } catch (err: any) {
      setStatus(err.message)
    }
  }, [keyword])

  useEffect(() => { search() }, [search])

  return (
    <section className="page">
      <header className="page-header">
        <h1 className="page-title">文献管理</h1>
        <div className="toolbar">
          <input className="input" value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="标题 / DOI" />
          <button className="button" onClick={search}>搜索</button>
        </div>
      </header>
      {status && <div className="status">{status}</div>}
      <PaperTable papers={papers} />
    </section>
  )
}

export const AdminUsersPage: React.FC = () => {
  const [users, setUsers] = useState<UserRow[]>([])
  const [status, setStatus] = useState('正在加载用户...')

  async function load() {
    try {
      const data = await requestJson<UserRow[] | { data?: UserRow[] }>('/api/admin/all-users')
      setUsers(Array.isArray(data) ? data : data.data || [])
      setStatus('')
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  async function setRole(user: UserRow, role: string) {
    try {
      await putJson(`/api/admin/users/${user.id}/permissions`, { role, is_approved: true })
      load()
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <section className="page">
      <header className="page-header"><h1 className="page-title">用户管理</h1></header>
      {status && <div className="status">{status}</div>}
      <div className="table-wrap panel">
        <table className="table">
          <thead><tr><th>用户</th><th>邮箱</th><th>角色</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            {users.map((user) => (
              <tr key={user.id}>
                <td>{user.real_name || user.username || user.id}</td>
                <td>{user.email || '-'}</td>
                <td>{user.role || (user.is_superadmin ? 'superadmin' : user.is_admin ? 'admin' : 'user')}</td>
                <td>{user.is_approved === false ? '待审批' : '已启用'}</td>
                <td>
                  <div className="toolbar">
                    <button className="button secondary" onClick={() => setRole(user, 'user')}>用户</button>
                    <button className="button secondary" onClick={() => setRole(user, 'admin')}>管理员</button>
                    <button className="button secondary" onClick={() => setRole(user, 'superadmin')}>超管</button>
                  </div>
                </td>
              </tr>
            ))}
            {users.length === 0 && <tr><td colSpan={5} className="muted">暂无用户</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function PaperTable({ papers, actions }: { papers: Paper[]; actions?: (paper: Paper) => React.ReactNode }) {
  return (
    <div className="table-wrap panel">
      <table className="table">
        <thead><tr><th>ID</th><th>标题</th><th>来源</th><th>状态</th><th>操作</th></tr></thead>
        <tbody>
          {papers.map((paper) => (
            <tr key={paper.id}>
              <td>{paper.id}</td>
              <td>{paper.title || paper.doi || '-'}</td>
              <td>{[paper.journal, paper.year].filter(Boolean).join(' · ') || '-'}</td>
              <td>{paper.review_status || '-'}</td>
              <td>{actions ? actions(paper) : '-'}</td>
            </tr>
          ))}
          {papers.length === 0 && <tr><td colSpan={5} className="muted">暂无文献</td></tr>}
        </tbody>
      </table>
    </div>
  )
}
