import React from 'react'
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth, type User } from '../context/AuthContext'

interface Props {
  allow: User['role'][]
  children: React.ReactNode
  redirectSuperadminFromAdmin?: boolean
}

const RoleRoute: React.FC<Props> = ({ allow, children, redirectSuperadminFromAdmin = false }) => {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  if (loading) return <Box sx={{ minHeight: '55vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  if (!user) return <Navigate to="/news" replace />
  if (redirectSuperadminFromAdmin && user.role === 'superadmin') return <Navigate to="/superadmin" replace />
  if (!allow.includes(user.role)) {
    return (
      <Box sx={{ maxWidth: 640, mx: 'auto', mt: 8 }}>
        <Alert severity="error"><Typography fontWeight={700}>403 · 无权访问此页面</Typography></Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/account')}>返回用户中心</Button>
      </Box>
    )
  }
  return <>{children}</>
}

export default RoleRoute
