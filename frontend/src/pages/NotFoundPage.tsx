import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Box, Button, Stack, Typography } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'
import { useLanguage } from '../context/LanguageContext'

// 前端地址可被用户任意输入或以相对路径误拼（例如 /upload/papers/999999），
// 未匹配路由必须给出明确提示，不能留白屏。
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { t } = useLanguage()

  return (
    <Box sx={{ textAlign: 'center', py: 8 }}>
      <Typography variant="h4" fontWeight={800} gutterBottom>{t('nav.notFoundTitle')}</Typography>
      <Typography color="text.secondary" gutterBottom>
        {t('nav.notFoundPath', { path: location.pathname })}
      </Typography>
      <Stack direction="row" spacing={1.5} justifyContent="center" sx={{ mt: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/news')}>{t('nav.backHome')}</Button>
        <Button variant="outlined" onClick={() => navigate('/upload')}>{t('nav.goUpload')}</Button>
      </Stack>
    </Box>
  )
}

export default NotFoundPage
