import React, { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Alert, Avatar, Box, Button, Card, CardContent, Chip, CircularProgress, Divider,
  Stack, TextField, Typography,
} from '@mui/material'
import { AdminPanelSettings, DeleteOutline, OpenInNew, PhotoCamera, Security } from '@mui/icons-material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import UsernameField from '../components/UsernameField'
import MyPapersList from '../components/MyPapersList'

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

const AccountPage: React.FC = () => {
  const navigate = useNavigate()
  const { user, replaceUser, updateUsername, logout } = useAuth()
  const { t } = useLanguage()
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

  /**
   * 错误消息映射：AuthContext 抛出的 Error.message 是机器键（如 'usernameUpdateFailed'），
   * 此处映射为 `account.*` 字典文案（随语言切换）；api 层返回的后端原文原样显示。
   */
  const errorText = (error: unknown): string => {
    const message = (error as Error).message
    const key = `account.${message}`
    const mapped = t(key)
    return mapped === key ? message : mapped
  }

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
    void load().catch(error => setMessage({ severity: 'error', text: errorText(error) })).finally(() => setInitialLoading(false))
  }, [])

  const run = async (action: () => Promise<void>, success: string) => {
    setBusy(true)
    setMessage(null)
    try {
      await action()
      setMessage({ severity: 'success', text: success })
    } catch (error) {
      setMessage({ severity: 'error', text: errorText(error) })
    } finally {
      setBusy(false)
    }
  }

  if (initialLoading) return <Box sx={{ minHeight: '55vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  if (!profile || !user) return <Alert severity="error">{message?.text || t('account.profileLoadFailed')}</Alert>

  const saveProfile = () => {
    if (realName && !profile.real_name && !window.confirm(t('account.realNameConfirm'))) return
    void run(async () => {
    const researchInterests = interests.split(/[，,]/).map(value => value.trim()).filter(Boolean)
    const updated = await api.patch<Profile>('/api/account/profile', { real_name: realName, affiliation, orcid, research_interests: researchInterests })
    setProfile(updated)
    }, t('account.profileSaved'))
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
    }, t('account.avatarUpdated'))
  }

  return (
    <Box sx={{ maxWidth: 1040, mx: 'auto' }}>
      <Typography variant="overline" color="primary" fontWeight={700}>ACCOUNT</Typography>
      <Typography variant="h3" fontWeight={800}>{t('account.title')}</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>{t('account.subtitle')}</Typography>
      {message && <Alert severity={message.severity} onClose={() => setMessage(null)} sx={{ mb: 2 }}>{message.text}</Alert>}

      <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={3} alignItems={{ md: 'center' }}>
            <Avatar src={profile.avatar_url || undefined} sx={{ width: 92, height: 92, bgcolor: 'primary.main', fontSize: 32 }}>{profile.username[0].toUpperCase()}</Avatar>
            <Box sx={{ flex: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Typography variant="h5" fontWeight={750}>{profile.username}</Typography>
                <Chip size="small" label={t(`enums.role.${profile.role}`)} color={profile.role === 'superadmin' ? 'error' : profile.role === 'admin' ? 'primary' : 'default'} />
              </Stack>
              <Typography color="text.secondary">{profile.email} · {t('account.emailVerified')}</Typography>
              <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                <Button component="label" size="small" startIcon={<PhotoCamera />}>{t('account.uploadAvatar')}<input hidden type="file" accept="image/jpeg,image/png,image/webp" onChange={event => uploadAvatar(event.target.files?.[0])} /></Button>
                {profile.avatar_url && <Button color="error" size="small" startIcon={<DeleteOutline />} onClick={() => void run(async () => { await api.del('/api/account/avatar'); setProfile({ ...profile, avatar_url: null }); replaceUser({ ...user, avatar_url: null }) }, t('account.avatarDeleted'))}>{t('common.delete')}</Button>}
                <Button size="small" startIcon={<OpenInNew />} onClick={() => navigate(`/users/${profile.username}`)}>{t('account.viewPublicProfile')}</Button>
              </Stack>
            </Box>
          </Stack>
          <Divider sx={{ my: 3 }} />
          <Typography variant="h6" fontWeight={750} gutterBottom>{t('account.profileSection')}</Typography>
          <Alert severity="info" sx={{ mb: 2 }}>{t('account.profilePrivacyHint')}</Alert>
          <Box sx={{ display: 'grid', gridTemplateColumns: { xs: '1fr', md: '1fr 1fr' }, gap: 2 }}>
            <TextField label={t('account.realName')} value={realName} onChange={event => setRealName(event.target.value)} helperText={t('account.realNameHelper')} />
            <TextField label={t('account.affiliation')} value={affiliation} onChange={event => setAffiliation(event.target.value)} />
            <TextField label="ORCID" value={orcid} onChange={event => setOrcid(event.target.value)} placeholder="0000-0002-1825-0097" />
            <TextField label={t('account.researchInterests')} value={interests} onChange={event => setInterests(event.target.value)} helperText={t('account.interestsHelper')} />
          </Box>
          <Button variant="contained" disabled={busy} onClick={saveProfile} sx={{ mt: 2 }}>{t('account.saveProfile')}</Button>
        </CardContent>
      </Card>

      {profile.username_change_allowed && (
        <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
          <Typography variant="h6" fontWeight={750}>{t('account.setUsernameTitle')}</Typography>
          <Alert severity="warning" sx={{ my: 2 }}>{t('account.usernameChangeWarning')}</Alert>
          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5} alignItems="start">
            <Box sx={{ flex: 1, width: '100%' }}><UsernameField value={newUsername} onChange={setNewUsername} /></Box>
            <Button variant="outlined" disabled={busy || !newUsername} onClick={() => void run(async () => { await updateUsername(newUsername); await load() }, t('account.usernameUpdated'))}>{t('account.confirmChange')}</Button>
          </Stack>
        </CardContent></Card>
      )}

      <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
        <Typography variant="h6" fontWeight={750}>{t('account.myPapers')}</Typography>
        <Typography color="text.secondary" variant="body2" sx={{ mt: 0.5 }}>
          {t('account.myPapersHint')}
        </Typography>
        <MyPapersList />
      </CardContent></Card>

      <Card variant="outlined" sx={{ mb: 3, borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center"><Security color="primary" /><Typography variant="h6" fontWeight={750}>{t('account.securitySection')}</Typography></Stack>
        <Typography color="text.secondary" sx={{ my: 1.5 }}>{t('account.securityHint')}</Typography>
        <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
          <TextField type="password" label={t('account.currentPassword')} value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} />
          <TextField type="password" label={t('account.newPassword')} value={newPassword} onChange={event => setNewPassword(event.target.value)} helperText={t('account.passwordMinHint')} />
          <Button variant="outlined" disabled={busy || newPassword.length < 10} onClick={() => void run(async () => { await api.post('/api/account/change-password', { current_password: currentPassword, new_password: newPassword }); logout(); navigate('/news') }, t('account.passwordChanged'))}>{t('account.changePassword')}</Button>
        </Stack>
      </CardContent></Card>

      <Card variant="outlined" sx={{ borderRadius: 3 }}><CardContent sx={{ p: 3 }}>
        <Stack direction="row" spacing={1} alignItems="center"><AdminPanelSettings color="primary" /><Typography variant="h6" fontWeight={750}>{t('account.workSection')}</Typography></Stack>
        {profile.role === 'admin' && <Button variant="contained" sx={{ mt: 2 }} onClick={() => navigate('/admin')}>{t('account.enterAdmin')}</Button>}
        {profile.role === 'superadmin' && <Button variant="contained" color="error" sx={{ mt: 2 }} onClick={() => navigate('/superadmin')}>{t('account.enterSuperAdmin')}</Button>}
        {profile.role === 'user' && (
          <Box sx={{ mt: 2 }}>
            <Typography color="text.secondary">{t('account.adminApplyHint')}</Typography>
            <Button variant="contained" sx={{ mt: 1.5 }} disabled={busy || Boolean(pendingApplication)} onClick={() => void run(async () => { await api.post('/api/account/admin-applications'); await load() }, t('account.adminApplied'))}>{t('account.applyAdmin')}</Button>
            {applications.length > 0 && <Stack spacing={1} sx={{ mt: 2 }}>{applications.map(item => <Box key={item.id} sx={{ p: 1.5, bgcolor: 'action.hover', borderRadius: 2 }}><Stack direction="row" justifyContent="space-between" alignItems="center"><Box><Chip size="small" label={t(`account.applicationStatus.${item.status}`)} /><Typography variant="caption" color="text.secondary" sx={{ ml: 1 }}>{new Date(item.submitted_at).toLocaleString()}</Typography>{item.rejection_reason && <Typography color="error" variant="body2" sx={{ mt: 0.5 }}>{t('account.rejectionReason', { reason: item.rejection_reason || '' })}</Typography>}</Box>{item.status === 'pending' && <Button size="small" color="warning" onClick={() => void run(async () => { await api.post(`/api/account/admin-applications/${item.id}/withdraw`); await load() }, t('account.applicationWithdrawn'))}>{t('account.withdraw')}</Button>}</Stack></Box>)}</Stack>}
          </Box>
        )}
      </CardContent></Card>
    </Box>
  )
}

export default AccountPage
