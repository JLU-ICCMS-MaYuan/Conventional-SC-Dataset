import React, { useState } from 'react'
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
      <div className="panel" style={{ maxWidth: 460, margin: '40px auto' }}>
        <h1>{isAdmin ? '管理员登录' : '用户登录'}</h1>
        <form className="grid" onSubmit={submit}>
          <label className="field">用户名或邮箱<input className="input" value={username} onChange={(e) => setUsername(e.target.value)} /></label>
          <label className="field">密码<input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          {error && <div className="status error">{error}</div>}
          <button className="button">登录</button>
          <Link to={isAdmin ? '/admin/register' : '/register'}>{isAdmin ? '申请管理员账号' : '注册新账号'}</Link>
        </form>
      </div>
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
      <div className="panel" style={{ maxWidth: 520, margin: '40px auto' }}>
        <h1>{isAdmin ? '管理员注册申请' : '用户注册'}</h1>
        <form className="grid" onSubmit={submit}>
          <label className="field">用户名<input className="input" value={form.username} onChange={(e) => update('username', e.target.value)} /></label>
          <label className="field">真实姓名<input className="input" value={form.real_name} onChange={(e) => update('real_name', e.target.value)} /></label>
          <label className="field">邮箱<input className="input" value={form.email} onChange={(e) => update('email', e.target.value)} /></label>
          <label className="field">密码<input className="input" type="password" value={form.password} onChange={(e) => update('password', e.target.value)} /></label>
          {status && <div className="status">{status}</div>}
          <button className="button">提交</button>
        </form>
      </div>
    </section>
  )
}
