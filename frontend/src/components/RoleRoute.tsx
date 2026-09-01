import React from 'react'
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAuth, type User } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'

interface Props {
  allow: User['role'][]
  children: React.ReactNode
  redirectSuperadminFromAdmin?: boolean
}

const RoleRoute: React.FC<Props> = ({ allow, children, redirectSuperadminFromAdmin = false }) => {
  const navigate = useNavigate()
  const { user, loading } = useAuth()
  const { t } = useLanguage()
  if (loading) return <Box sx={{ minHeight: '55vh', display: 'grid', placeItems: 'center' }}><CircularProgress /></Box>
  if (!user) return <Navigate to="/news" replace />
  if (redirectSuperadminFromAdmin && user.role === 'superadmin') return <Navigate to="/superadmin" replace />
  if (!allow.includes(user.role)) {
    return (
      <Box sx={{ maxWidth: 640, mx: 'auto', mt: 8 }}>
        <Alert severity="error"><Typography fontWeight={700}>{t('nav.forbidden')}</Typography></Alert>
        <Button sx={{ mt: 2 }} onClick={() => navigate('/account')}>{t('nav.backAccount')}</Button>
      </Box>
    )
  }
  return <>{children}</>
}

export default RoleRoute
