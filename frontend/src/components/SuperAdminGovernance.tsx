import React, { useCallback, useEffect, useState } from 'react'
import {
  Alert, Box, Button, Chip, CircularProgress, FormControl, InputLabel, MenuItem,
  Paper, Select, Stack, Tab, Table, TableBody, TableCell, TableContainer, TableHead,
  TableRow, Tabs, Typography,
} from '@mui/material'
import { api } from '../lib/api'
import { useAuth } from '../context/AuthContext'

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

const roleLabel = { user: '用户', admin: '管理员', superadmin: '超级管理员' }
const statusLabel = { active: '正常', banned: '已封禁', deactivated: '已注销' }

const SuperAdminGovernance: React.FC = () => {
  const { user } = useAuth()
  const [section, setSection] = useState(0)
  const [users, setUsers] = useState<GovernanceUser[]>([])
  const [applications, setApplications] = useState<AdminApplication[]>([])
  const [audits, setAudits] = useState<AuditEvent[]>([])
  const [auditKind, setAuditKind] = useState('governance')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

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
    const value = window.prompt(`${label}原因（必填，将永久写入审计记录）`)?.trim()
    return value || null
  }

  const changeRole = (target: GovernanceUser, role: GovernanceUser['role']) => {
    if (role === target.role) return
    const why = reason(`将 ${target.username} 的角色改为${roleLabel[role]}`)
    if (!why || !window.confirm(`确认修改 ${target.username} 的角色？该用户现有登录会立即失效。`)) return
    void act(() => api.post(`/api/superadmin/users/${target.id}/role`, { role, reason: why }))
  }

  const changeStatus = (target: GovernanceUser, action: 'ban' | 'unban' | 'deactivate') => {
    const labels = { ban: '封禁', unban: '解除封禁', deactivate: '注销账号' }
    const why = reason(`${labels[action]} ${target.username}`)
    if (!why || !window.confirm(`确认${labels[action]}账号 ${target.username}？此操作会立即撤销其登录状态。`)) return
    void act(() => api.post(`/api/superadmin/users/${target.id}/${action}`, { reason: why }))
  }

  return (
    <Box>
      <Tabs value={section} onChange={(_, value) => setSection(value)} sx={{ mb: 2 }}>
        <Tab label={`管理员申请${applications.filter(item => item.status === 'pending').length ? ` (${applications.filter(item => item.status === 'pending').length})` : ''}`} />
        <Tab label="用户与权限" />
        <Tab label="审计记录" />
      </Tabs>
      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
      {loading && <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}><CircularProgress size={24} /></Box>}

      {section === 0 && !loading && (
        <TableContainer component={Paper} variant="outlined"><Table size="small">
          <TableHead><TableRow><TableCell>申请人快照</TableCell><TableCell>机构 / ORCID</TableCell><TableCell>状态</TableCell><TableCell>提交时间</TableCell><TableCell align="right">操作</TableCell></TableRow></TableHead>
          <TableBody>{applications.map(item => <TableRow key={item.id} hover><TableCell><Typography fontWeight={650}>{item.real_name_snapshot}</Typography><Typography variant="caption" color="text.secondary">用户 #{item.user_id}</Typography></TableCell><TableCell>{item.affiliation_snapshot}<br /><Typography variant="caption">{item.orcid_snapshot || '未填写 ORCID'}</Typography></TableCell><TableCell><Chip size="small" label={item.status === 'pending' ? '待审核' : item.status === 'approved' ? '已通过' : item.status === 'rejected' ? '已拒绝' : '已撤回'} color={item.status === 'pending' ? 'warning' : item.status === 'approved' ? 'success' : 'default'} />{item.rejection_reason && <Typography variant="caption" color="error" display="block">{item.rejection_reason}</Typography>}</TableCell><TableCell>{new Date(item.submitted_at).toLocaleString()}</TableCell><TableCell align="right">{item.status === 'pending' && <Stack direction="row" spacing={1} justifyContent="flex-end"><Button size="small" color="success" onClick={() => { if (window.confirm('确认批准该管理员申请？申请人角色将立即变为管理员。')) void act(() => api.post(`/api/superadmin/admin-applications/${item.id}/approve`)) }}>通过</Button><Button size="small" color="error" onClick={() => { const why = reason('拒绝管理员申请'); if (why) void act(() => api.post(`/api/superadmin/admin-applications/${item.id}/reject`, { reason: why })) }}>拒绝</Button></Stack>}</TableCell></TableRow>)}</TableBody>
        </Table></TableContainer>
      )}

      {section === 1 && !loading && (
        <TableContainer component={Paper} variant="outlined"><Table size="small">
          <TableHead><TableRow><TableCell>用户</TableCell><TableCell>实名 / 机构</TableCell><TableCell>角色</TableCell><TableCell>状态</TableCell><TableCell align="right">治理操作</TableCell></TableRow></TableHead>
          <TableBody>{users.map(item => <TableRow key={item.id} hover><TableCell><Typography fontWeight={650}>{item.username}{item.id === user?.id ? '（当前账号）' : ''}</Typography><Typography variant="caption" color="text.secondary">{item.email}</Typography></TableCell><TableCell>{item.real_name || '-'}<br /><Typography variant="caption" color="text.secondary">{item.affiliation || '-'}</Typography></TableCell><TableCell><FormControl size="small" sx={{ minWidth: 128 }} disabled={item.id === user?.id || item.account_status !== 'active'}><InputLabel>角色</InputLabel><Select value={item.role} label="角色" onChange={event => changeRole(item, event.target.value as GovernanceUser['role'])}><MenuItem value="user">用户</MenuItem><MenuItem value="admin">管理员</MenuItem><MenuItem value="superadmin">超级管理员</MenuItem></Select></FormControl></TableCell><TableCell><Chip size="small" label={statusLabel[item.account_status]} color={item.account_status === 'active' ? 'success' : item.account_status === 'banned' ? 'warning' : 'default'} /></TableCell><TableCell align="right">{item.id !== user?.id && item.account_status === 'active' && <><Button size="small" color="warning" onClick={() => changeStatus(item, 'ban')}>封禁</Button><Button size="small" color="error" onClick={() => changeStatus(item, 'deactivate')}>注销</Button></>}{item.id !== user?.id && item.account_status === 'banned' && <><Button size="small" onClick={() => changeStatus(item, 'unban')}>解除封禁</Button><Button size="small" color="error" onClick={() => changeStatus(item, 'deactivate')}>注销</Button></>}</TableCell></TableRow>)}</TableBody>
        </Table></TableContainer>
      )}

      {section === 2 && !loading && (
        <Box>
          <Stack direction="row" spacing={1} sx={{ mb: 2 }}><Chip label="角色与账号" clickable color={auditKind === 'governance' ? 'primary' : 'default'} onClick={() => { setAuditKind('governance'); void loadAudits('governance') }} /><Chip label="实名与机构" clickable color={auditKind === 'profile' ? 'primary' : 'default'} onClick={() => { setAuditKind('profile'); void loadAudits('profile') }} /><Chip label="用户名" clickable color={auditKind === 'username' ? 'primary' : 'default'} onClick={() => { setAuditKind('username'); void loadAudits('username') }} /></Stack>
          <TableContainer component={Paper} variant="outlined"><Table size="small"><TableHead><TableRow><TableCell>时间</TableCell><TableCell>目标用户</TableCell><TableCell>变更</TableCell><TableCell>操作人</TableCell><TableCell>原因</TableCell></TableRow></TableHead><TableBody>{audits.map(item => <TableRow key={`${auditKind}-${item.id}`}><TableCell>{new Date(item.created_at).toLocaleString()}</TableCell><TableCell>#{item.target_user_id}</TableCell><TableCell>{item.event_type || item.field_name || '用户名'}：{item.old_username || item.old_value || item.old_role || item.old_status || '空'} → {item.new_username || item.new_value || item.new_role || item.new_status || '空'}</TableCell><TableCell>{item.changed_by_username || `#${item.actor_user_id || item.changed_by_user_id || '-'}`}</TableCell><TableCell>{item.reason || '-'}</TableCell></TableRow>)}</TableBody></Table></TableContainer>
        </Box>
      )}
    </Box>
  )
}

export default SuperAdminGovernance
