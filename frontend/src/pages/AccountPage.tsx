import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  Stack, TextField, Typography,
} from '@mui/material'
import { AdminPanelSettings, DeleteOutline, OpenInNew, PhotoCamera, Security } from '@mui/icons-material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import UsernameField from '../components/UsernameField'

interface Profile {
  id: number
  email: string
  username: string
  username_change_allowed: boolean
  real_name: string
  affiliation: string | null
  orcid: string | null
  research_interests: string[]
  avatar_url: string | null
  role: 'user' | 'admin' | 'superadmin'
  is_email_verified: boolean
  account_status: string
}

interface AdminApplication {
  id: number
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  rejection_reason?: string | null
  submitted_at: string
}

const roleLabel = { user: '用户', admin: '管理员', superadmin: '超级管理员' }
const applicationLabel = { pending: '待审核', approved: '已通过', rejected: '已拒绝', withdrawn: '已撤回' }

const AccountPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, replaceUser, updateUsername, logout } = useAuth()
  const [profile, setProfile] = useState<Profile | null>(null)
  const [applications, setApplications] = useState<AdminApplication[]>([])
  const [realName, setRealName] = useState('')
  const [affiliation, setAffiliation] = useState('')
  const [orcid, setOrcid] = useState('')
  const [interests, setInterests] = useState('')
  const [newUsername, setNewUsername] = useState('')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [initialLoading, setInitialLoading] = useState(true)
  const [message, setMessage] = useState<{ severity: 'success' | 'error' | 'info'; text: string } | null>(null)

  const pendingApplication = useMemo(() => applications.find(item => item.status === 'pending'), [applications])

  const load = async () => {
    const data = await api.get<Profile>('/api/account/profile')
    setProfile(data)
    setRealName(data.real_name || '')
    setAffiliation(data.affiliation || '')
    setOrcid(data.orcid || '')
    setInterests((data.research_interests || []).join('，'))
    if (data.role === 'user') setApplications(await api.get<AdminApplication[]>('/api/account/admin-applications'))
  }

  useEffect(() => {
    void load().catch(error => setMessage({ severity: 'error', text: error.message })).finally(() => setInitialLoading(false))
  }, [])

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true)
    setMessage(null)
    try {
      await action()
      setMessage({ severity: 'success', text: success })
    } catch (error) {
      setMessage({ severity: 'error', text: (error as Error).message })
    } finally {
      setBusy(false)
    }
  }

  if (initialLoading) return <Box sx={{ minHeight: '55vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  if (!profile || !user) return <Alert severity="error">{message?.text || '用户资料加载失败'}</Alert>

  const saveProfile = () => {
    if (realName && !profile.real_name && !window.confirm('真实姓名填写后会在公开主页展示，确认继续吗？')) return
    void run(async () => {
    const researchInterests = interests.split(/[，,]/).map(value => value.trim()).filter(Boolean)
    const updated = await api.patch<Profile>('/api/account/profile', { real_name: realName, affiliation, orcid, research_interests: researchInterests })
    setProfile(updated)
    }, '个人资料已保存')
  }

  const uploadAvatar = (file?: File) => {
    if (!file) return
    void run(async () => {
      const form = new FormData()
      form.append('avatar', file)
      const result = await api.post<{ avatar_url: string }>('/api/account/avatar', form)
      const next = { ...profile, avatar_url: result.avatar_url }
      setProfile(next)
      replaceUser({ ...user, avatar_url: result.avatar_url })
    }, '头像已更新')
  }

  return (
    <Box sx={{ maxWidth: 1040, mx: 'auto' }}>
      <Typography variant="overline" color="primary" fontWeight={700}>ACCOUNT</Typography>
      <Typography variant="h3" fontWeight={800}>用户中心</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>统一维护你的公开研究身份、账户安全和工作入口。</Typography>
      {message && <Alert severity={message.severity} onClose={() => setMessage(null)} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems={{ md: 'center' }}>
            <Avatar src={profile.avatar_url || undefined} sx={{ width: 92, height: 92, bgcolor: 'primary.main', fontSize: 32 }}>{profile.username[0].toUpperCase()}</Avatar>
            <Box sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Typography variant="h5" fontWeight={750}>{profile.username}</Typography>
                <Chip size="small" label={roleLabel[profile.role]} color={profile.role === 'superadmin' ? 'error' : profile.role === 'admin' ? 'primary' : 'default'} />
              </Stack>
              <Typography color="text.secondary">{profile.email} · 邮箱已验证</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                <Button component="label" size="small" startIcon={<PhotoCamera />}>上传头像<input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={event => uploadAvatar(event.target.files?.[0])} /></Button>
                {profile.avatar_url && <Button color="error" size="small" startIcon={<DeleteOutline />} onClick={() => void run(async () => { await api.del('/api/account/avatar'); setProfile({ ...profile, avatar_url: null }); replaceUser({ ...user, avatar_url: null }) }, '头像已删除')}>删除</Button>}
                <Button size="small" startIcon={<OpenInNew />} onClick={() => navigate(`/users/${profile.username}`)}>查看公开主页</Button>
              </Stack>
            </Box>
          </Stack>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" fontWeight={750} gutterBottom>个人资料</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>头像、用户名、真实姓名、所属机构、ORCID 和研究方向在填写后对所有访客公开；邮箱始终不公开。</Alert>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            <TextField label="真实姓名" value={realName} onChange={event => setRealName(event.target.value)} helperText="可清空；每次变更都会留下审计记录" />
            <TextField label="所属机构" value={affiliation} onChange={event => setAffiliation(event.target.value)} />
            <TextField label="ORCID" value={orcid} onChange={event => setOrcid(event.target.value)} placeholder="0000-0002-1825-0097" />
            <TextField label="研究方向" value={interests} onChange={event => setInterests(event.target.value)} helperText="使用逗号分隔，最多 10 项，每项最多 30 字" />
          </Box>
          <Button variant="contained" disabled={busy} onClick={saveProfile} sx={{ mt: 2 }}>保存资料</Button>
        </CardContent>
      </Card>

      {profile.username_change_allowed && (
        <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={750}>设置正式用户名</Typography>
          <Alert severity="warning" sx={{ my: 2 }}>用户名只能由你修改一次；提交后旧公开主页地址立即失效。</Alert>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="start">
            <Box sx={{ flex: 1, width: '100%' }}><UsernameField value={newUsername} onChange={setNewUsername} /></Box>
            <Button variant="outlined" disabled={busy || !newUsername} onClick={() => void run(async () => { await updateUsername(newUsername); await load() }, '用户名已更新')}>确认修改</Button>
          </Stack>
        </CardContent></Card>
      )}

      <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center"><Security color="primary" /><Typography variant="h6" fontWeight={750}>账户安全</Typography></Stack>
        <Typography color="text.secondary" sx={{ my: 1.5 }}>修改成功后，其他设备和当前设备的旧登录状态都会失效。</Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField type="password" label="当前密码" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} />
          <TextField type="password" label="新密码" value={newPassword} onChange={event => setNewPassword(event.target.value)} helperText="至少 10 位" />
          <Button variant="outlined" disabled={busy || newPassword.length < 10} onClick={() => void run(async () => { await api.post('/api/account/change-password', { current_password: currentPassword, new_password: newPassword }); logout(); navigate('/news') }, '密码已修改，请重新登录')}>修改密码</Button>
        </Stack>
      </CardContent></Card>

      <Card variant="outlined" sx={{ borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center"><AdminPanelSettings color="primary" /><Typography variant="h6" fontWeight={750}>工作入口</Typography></Stack>
        {profile.role === 'admin' && <Button variant="contained" sx={{ mt: 2 }} onClick={() => navigate('/admin')}>进入管理员工作台</Button>}
        {profile.role === 'superadmin' && <Button variant="contained" color="error" sx={{ mt: 2 }} onClick={() => navigate('/superadmin')}>进入超级管理员工作台</Button>}
        {profile.role === 'user' && (
          <Box sx={{ mt: 2 }}>
            <Typography color="text.secondary">管理员可参与科研内容审核。申请无需填写理由，但提交前必须完善真实姓名和所属机构。</Typography>
            <Button variant="contained" sx={{ mt: 1.5 }} disabled={busy || Boolean(pendingApplication)} onClick={() => void run(async () => { await api.post('/api/account/admin-applications'); await load() }, '管理员申请已提交')}>申请成为管理员</Button>
            {applications.length > 0 && <Stack spacing={1} sx={{ mt: 2 }}>{applications.map(item => <Box key={item.id} sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}><Stack direction="row" justifyContent="space-between" alignItems="center"><Box><Chip size="small" label={applicationLabel[item.status]} /><Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>{new Date(item.submitted_at).toLocaleString()}</Typography>{item.rejection_reason && <Typography color="error" variant="body2" sx={{ mt: 0.5 }}>原因：{item.rejection_reason}</Typography>}</Box>{item.status === 'pending' && <Button size="small" color="warning" onClick={() => void run(async () => { await api.post(`/api/account/admin-applications/${item.id}/withdraw`); await load() }, '申请已撤回')}>撤回</Button>}</Stack></Box>)}</Stack>}
          </Box>
        )}
      </CardContent></Card>
    </Box>
  )
}

export default AccountPage
