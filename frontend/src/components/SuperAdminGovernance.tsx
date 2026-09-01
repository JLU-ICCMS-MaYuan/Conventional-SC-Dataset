import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, FormControl, InputLabel, MenuItem,
  Paper, Select, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Tabs, Typography,
} from '@mui/material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

interface GovernanceUser {
  id: number
  email: string
  username: string
  real_name: string
  affiliation: string | null
  role: 'user' | 'admin' | 'superadmin'
  account_status: 'active' | 'banned' | 'deactivated'
  is_email_verified: boolean
  created_at: string
}

interface AdminApplication {
  id: number
  user_id: number
  real_name_snapshot: string
  affiliation_snapshot: string
  orcid_snapshot?: string | null
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  rejection_reason?: string | null
  submitted_at: string
}

interface AuditEvent {
  id: number
  target_user_id: number
  actor_user_id?: number
  changed_by_user_id?: number
  changed_by_username?: string
  event_type?: string
  field_name?: string
  old_value?: string | null
  new_value?: string | null
  old_username?: string
  new_username?: string
  old_role?: string | null
  new_role?: string | null
  old_status?: string | null
  new_status?: string | null
  reason?: string
  created_at: string
}

const SuperAdminGovernance: React.FC = () => {
  const { user } = useAuth()
  const { t, dict } = useLanguage()
  const [section, setSection] = useState(0)
  const [users, setUsers] = useState<GovernanceUser[]>([])
  const [applications, setApplications] = useState<AdminApplication[]>([])
  const [audits, setAudits] = useState<AuditEvent[]>([])
  const [auditKind, setAuditKind] = useState('governance')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // 按 value 取枚举标签；未知值原样展示。
  const roleLabel = (value: string): string => {
    const labels = dict.enums.role
    return labels[value as keyof typeof labels] || value
  }
  const userStatusLabel = (value: string): string => {
    const labels = dict.admin.userStatus
    return labels[value as keyof typeof labels] || value
  }
  const applicationStatusLabel = (value: string): string => {
    const labels = dict.admin.applicationStatus
    return labels[value as keyof typeof labels] || value
  }

  const loadUsers = useCallback(async () => setUsers(await api.get<GovernanceUser[]>('/api/superadmin/users')), [])
  const loadApplications = useCallback(async () => setApplications(await api.get<AdminApplication[]>('/api/superadmin/admin-applications')), [])
  const loadAudits = useCallback(async (kind = auditKind) => {
    const path = kind === 'profile' ? 'profile-changes' : kind === 'username' ? 'username-changes' : 'governance'
    setAudits(await api.get<AuditEvent[]>(`/api/superadmin/audits/${path}`))
  }, [auditKind])

  const refresh = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      if (section === 0) await loadApplications()
      if (section === 1) await loadUsers()
      if (section === 2) await loadAudits()
    } catch (cause) {
      setError((cause as Error).message)
    } finally {
      setLoading(false)
    }
  }, [loadApplications, loadAudits, loadUsers, section])

  useEffect(() => { void refresh() }, [refresh])

  const act = async (action: () => Promise<unknown>) => {
    setLoading(true)
    setError('')
    try { await action(); await refresh() } catch (cause) { setError((cause as Error).message); setLoading(false) }
  }

  const reason = (label: string) => {
    const value = window.prompt(`${label}${t('admin.reasonSuffix')}`)?.trim()
    return value || null
  }

  const changeRole = (target: GovernanceUser, role: GovernanceUser['role']) => {
    if (role === target.role) return
    const why = reason(t('admin.changeRolePrompt', { username: target.username, role: roleLabel(role) }))
    if (!why || !window.confirm(t('admin.confirmRoleChange', { username: target.username }))) return
    void act(() => api.post(`/api/superadmin/users/${target.id}/role`, { role, reason: why }))
  }

  const changeStatus = (target: GovernanceUser, action: 'ban' | 'unban' | 'deactivate') => {
    const labels = { ban: t('admin.ban'), unban: t('admin.unban'), deactivate: t('admin.deactivate') }
    const why = reason(t('admin.statusActionPrompt', { action: labels[action], username: target.username }))
    if (!why || !window.confirm(t('admin.confirmStatusAction', { action: labels[action], username: target.username }))) return
    void act(() => api.post(`/api/superadmin/users/${target.id}/${action}`, { reason: why }))
  }

  const pendingCount = applications.filter(item => item.status === 'pending').length

  return (
    <Box>
      <Tabs value={section} onChange={(_, value) => setSection(value)} sx={{ mb: 2 }}>
        <Tab label={`${t('admin.applicationsTab')}${pendingCount ? ` (${pendingCount})` : ''}`} />
        <Tab label={t('admin.usersPermissions')} />
        <Tab label={t('admin.auditTab')} />
      </Tabs>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading && <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}><CircularProgress size={24} /></Box>}

      {section === 0 && !loading && (
        <TableContainer component={Paper} variant="outlined"><Table size="small">
          <TableHead><TableRow><TableCell>{t('admin.thApplicantSnapshot')}</TableCell><TableCell>{t('admin.thAffiliationOrcid')}</TableCell><TableCell>{t('admin.thStatus')}</TableCell><TableCell>{t('admin.thSubmittedAt')}</TableCell><TableCell align="right">{t('common.operations')}</TableCell></TableRow></TableHead>
          <TableBody>{applications.map(item => <TableRow key={item.id} hover><TableCell><Typography fontWeight={650}>{item.real_name_snapshot}</Typography><Typography variant="caption" color="text.secondary">{t('admin.userHash', { id: item.user_id })}</Typography></TableCell><TableCell>{item.affiliation_snapshot}<br /><Typography variant="caption">{item.orcid_snapshot || t('admin.orcidNotProvided')}</Typography></TableCell><TableCell><Chip size="small" label={applicationStatusLabel(item.status)} color={item.status === 'pending' ? 'warning' : item.status === 'approved' ? 'success' : 'default'} />{item.rejection_reason && <Typography variant="caption" color="error" display="block">{item.rejection_reason}</Typography>}</TableCell><TableCell>{new Date(item.submitted_at).toLocaleString()}</TableCell><TableCell align="right">{item.status === 'pending' && <Stack direction="row" spacing={1} justifyContent="flex-end"><Button size="small" color="success" onClick={() => { if (window.confirm(t('admin.confirmApproveApplication'))) void act(() => api.post(`/api/superadmin/admin-applications/${item.id}/approve`)) }}>{t('admin.approve')}</Button><Button size="small" color="error" onClick={() => { const why = reason(t('admin.rejectApplicationReason')); if (why) void act(() => api.post(`/api/superadmin/admin-applications/${item.id}/reject`, { reason: why })) }}>{t('admin.reject')}</Button></Stack>}</TableCell></TableRow>)}</TableBody>
        </Table></TableContainer>
      )}

      {section === 1 && !loading && (
        <TableContainer component={Paper} variant="outlined"><Table size="small">
          <TableHead><TableRow><TableCell>{t('admin.thUser')}</TableCell><TableCell>{t('admin.thRealNameAffiliation')}</TableCell><TableCell>{t('admin.fieldRole')}</TableCell><TableCell>{t('admin.thStatus')}</TableCell><TableCell align="right">{t('admin.thGovernanceActions')}</TableCell></TableRow></TableHead>
          <TableBody>{users.map(item => <TableRow key={item.id} hover><TableCell><Typography fontWeight={650}>{item.username}{item.id === user?.id ? t('admin.currentAccountSuffix') : ''}</Typography><Typography variant="caption" color="text.secondary">{item.email}</Typography></TableCell><TableCell>{item.real_name || '-'}<br /><Typography variant="caption" color="text.secondary">{item.affiliation || '-'}</Typography></TableCell><TableCell><FormControl size="small" sx={{ minWidth: 128 }} disabled={item.id === user?.id || item.account_status !== 'active'}><InputLabel>{t('admin.fieldRole')}</InputLabel><Select value={item.role} label={t('admin.fieldRole')} onChange={event => changeRole(item, event.target.value as GovernanceUser['role'])}><MenuItem value="user">{roleLabel('user')}</MenuItem><MenuItem value="admin">{roleLabel('admin')}</MenuItem><MenuItem value="superadmin">{roleLabel('superadmin')}</MenuItem></Select></FormControl></TableCell><TableCell><Chip size="small" label={userStatusLabel(item.account_status)} color={item.account_status === 'active' ? 'success' : item.account_status === 'banned' ? 'warning' : 'default'} /></TableCell><TableCell align="right">{item.id !== user?.id && item.account_status === 'active' && <><Button size="small" color="warning" onClick={() => changeStatus(item, 'ban')}>{t('admin.ban')}</Button><Button size="small" color="error" onClick={() => changeStatus(item, 'deactivate')}>{t('admin.deactivate')}</Button></>}{item.id !== user?.id && item.account_status === 'banned' && <><Button size="small" onClick={() => changeStatus(item, 'unban')}>{t('admin.unban')}</Button><Button size="small" color="error" onClick={() => changeStatus(item, 'deactivate')}>{t('admin.deactivate')}</Button></>}</TableCell></TableRow>)}</TableBody>
        </Table></TableContainer>
      )}

      {section === 2 && !loading && (
        <Box>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}><Chip label={t('admin.auditKindGovernance')} clickable color={auditKind === 'governance' ? 'primary' : 'default'} onClick={() => { setAuditKind('governance'); void loadAudits('governance') }} /><Chip label={t('admin.auditKindProfile')} clickable color={auditKind === 'profile' ? 'primary' : 'default'} onClick={() => { setAuditKind('profile'); void loadAudits('profile') }} /><Chip label={t('admin.auditKindUsername')} clickable color={auditKind === 'username' ? 'primary' : 'default'} onClick={() => { setAuditKind('username'); void loadAudits('username') }} /></Stack>
          <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell>{t('admin.thTime')}</TableCell><TableCell>{t('admin.thTargetUser')}</TableCell><TableCell>{t('admin.thChange')}</TableCell><TableCell>{t('admin.thActor')}</TableCell><TableCell>{t('admin.thReason')}</TableCell></TableRow></TableHead><TableBody>{audits.map(item => <TableRow key={`${auditKind}-${item.id}`}><TableCell>{new Date(item.created_at).toLocaleString()}</TableCell><TableCell>#{item.target_user_id}</TableCell><TableCell>{t('admin.auditChange', { field: item.event_type || item.field_name || t('admin.auditKindUsername'), old: item.old_username || item.old_value || item.old_role || item.old_status || t('admin.auditEmpty'), new: item.new_username || item.new_value || item.new_role || item.new_status || t('admin.auditEmpty') })}</TableCell><TableCell>{item.changed_by_username || `#${item.actor_user_id || item.changed_by_user_id || '-'}`}</TableCell><TableCell>{item.reason || '-'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
        </Box>
      )}
    </Box>
  )
}

export default SuperAdminGovernance
