import React, { useCallback, useEffect, useState } from 'react'
import {
  Button,
  Card,
  CardContent,
  Input,
  Table,
} from '@heroui/react'
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
      {status && <div className="status-message">{status}</div>}
      <PaperTable papers={papers} actions={(paper) => (
        <div className="toolbar">
          <Button variant="primary"  size="sm" onPress={() => review(paper.id, true)}>通过</Button>
          <Button variant="danger"  size="sm" onPress={() => review(paper.id, false)}>拒绝</Button>
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
          <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} placeholder="标题 / DOI" />
          <Button variant="primary"  onPress={search}>搜索</Button>
        </div>
      </header>
      {status && <div className="status-message">{status}</div>}
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
      {status && <div className="status-message">{status}</div>}
      <Card  >
        <CardContent>
        <Table aria-label="用户管理"><Table.Content>
          <Table.Header>
            <Table.Column>用户</Table.Column>
            <Table.Column>邮箱</Table.Column>
            <Table.Column>角色</Table.Column>
            <Table.Column>状态</Table.Column>
            <Table.Column>操作</Table.Column>
          </Table.Header>
          <Table.Body>
            {users.map((user) => (
              <Table.Row key={user.id}>
                <Table.Cell>{user.real_name || user.username || user.id}</Table.Cell>
                <Table.Cell>{user.email || '-'}</Table.Cell>
                <Table.Cell>{user.role || (user.is_superadmin ? 'superadmin' : user.is_admin ? 'admin' : 'user')}</Table.Cell>
                <Table.Cell>{user.is_approved === false ? '待审批' : '已启用'}</Table.Cell>
                <Table.Cell>
                  <div className="toolbar">
                    <Button variant="outline"  size="sm" onPress={() => setRole(user, 'user')}>用户</Button>
                    <Button variant="outline"  size="sm" onPress={() => setRole(user, 'admin')}>管理员</Button>
                    <Button variant="outline"  size="sm" onPress={() => setRole(user, 'superadmin')}>超管</Button>
                  </div>
                </Table.Cell>
              </Table.Row>
            ))}
            {users.length === 0 && (
              <Table.Row>
                <Table.Cell colSpan={5}>暂无用户</Table.Cell>
              </Table.Row>
            )}
          </Table.Body>
        </Table.Content></Table>
        </CardContent>
      </Card>
    </section>
  )
}

function PaperTable({ papers, actions }: { papers: Paper[]; actions?: (paper: Paper) => React.ReactNode }) {
  return (
    <Card  >
      <CardContent>
      <Table aria-label="文献表格"><Table.Content>
        <Table.Header>
          <Table.Column>ID</Table.Column>
          <Table.Column>标题</Table.Column>
          <Table.Column>来源</Table.Column>
          <Table.Column>状态</Table.Column>
          <Table.Column>操作</Table.Column>
        </Table.Header>
        <Table.Body>
          {papers.map((paper) => (
            <Table.Row key={paper.id}>
              <Table.Cell>{paper.id}</Table.Cell>
              <Table.Cell>{paper.title || paper.doi || '-'}</Table.Cell>
              <Table.Cell>{[paper.journal, paper.year].filter(Boolean).join(' · ') || '-'}</Table.Cell>
              <Table.Cell>{paper.review_status || '-'}</Table.Cell>
              <Table.Cell>{actions ? actions(paper) : '-'}</Table.Cell>
            </Table.Row>
          ))}
          {papers.length === 0 && (
            <Table.Row>
              <Table.Cell colSpan={5}>暂无文献</Table.Cell>
            </Table.Row>
          )}
        </Table.Body>
      </Table.Content></Table>
      </CardContent>
    </Card>
  )
}
