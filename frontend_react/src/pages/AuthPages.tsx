import React, { useState } from 'react'
import { Button, Card, CardContent, CardHeader, Separator, Input } from '@heroui/react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { postJson } from '../lib/apiClient'
import { useAuth } from '../context/AuthContext'

interface AuthResponse {
  access_token: string
  user: { id: number; username: string; email: string; role: string }
}

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const isAdmin = location.pathname.startsWith('/admin')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    try {
      const data = await postJson<AuthResponse>('/api/auth/login', { username, password })
      login(data.access_token, data.user)
      navigate(isAdmin ? '/admin/dashboard' : '/')
    } catch (err: any) {
      setError(err.message)
    }
  }

  return (
    <section className="page">
      <Card   className="mx-auto mt-10 max-w-[460px]">
        <CardHeader><h1 className="page-title">{isAdmin ? '管理员登录' : '用户登录'}</h1></CardHeader>
        <Separator />
        <CardContent>
        <form className="stack" onSubmit={submit}>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            用户名或邮箱
            <Input value={username} onChange={(event) => setUsername(event.target.value)} />
          </label>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            密码
            <Input type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
          </label>
          {error && <div className="status-message error">{error}</div>}
          <Button variant="primary"  type="submit">登录</Button>
          <Link className="text-sm text-[var(--sc-primary)]" to={isAdmin ? '/admin/register' : '/register'}>{isAdmin ? '申请管理员账号' : '注册新账号'}</Link>
        </form>
        </CardContent>
      </Card>
    </section>
  )
}

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const isAdmin = location.pathname.startsWith('/admin')
  const [form, setForm] = useState({ username: '', email: '', password: '', real_name: '' })
  const [status, setStatus] = useState('')

  function update(key: keyof typeof form, value: string) {
    setForm((prev) => ({ ...prev, [key]: value }))
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setStatus('')
    try {
      await postJson('/api/auth/register', { ...form, is_admin: isAdmin })
      setStatus(isAdmin ? '申请已提交，请等待超级管理员审批' : '注册成功，请登录')
      setTimeout(() => navigate(isAdmin ? '/admin/login' : '/login'), 800)
    } catch (err: any) {
      setStatus(err.message)
    }
  }

  return (
    <section className="page">
      <Card   className="mx-auto mt-10 max-w-[520px]">
        <CardHeader><h1 className="page-title">{isAdmin ? '管理员注册申请' : '用户注册'}</h1></CardHeader>
        <Separator />
        <CardContent>
        <form className="stack" onSubmit={submit}>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            用户名
            <Input value={form.username} onChange={(event) => update('username', event.target.value)} />
          </label>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            真实姓名
            <Input value={form.real_name} onChange={(event) => update('real_name', event.target.value)} />
          </label>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            邮箱
            <Input value={form.email} onChange={(event) => update('email', event.target.value)} />
          </label>
          <label className="stack gap-2 text-sm font-semibold text-[var(--sc-muted)]">
            密码
            <Input type="password" value={form.password} onChange={(event) => update('password', event.target.value)} />
          </label>
          {status && <div className="status-message">{status}</div>}
          <Button variant="primary"  type="submit">提交</Button>
        </form>
        </CardContent>
      </Card>
    </section>
  )
}
