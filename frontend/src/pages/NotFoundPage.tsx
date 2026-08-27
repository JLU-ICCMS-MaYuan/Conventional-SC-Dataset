import React from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { Box, Button, Stack, Typography } from '@mui/material'
import ArrowBackIcon from '@mui/icons-material/ArrowBack'

// 前端地址可被用户任意输入或以相对路径误拼（例如 /upload/papers/999999），
// 未匹配路由必须给出明确提示，不能留白屏。
const NotFoundPage: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Box sx={{ textAlign: 'center', py: 8 }}>
      <Typography variant="h4" fontWeight={800} gutterBottom>页面不存在</Typography>
      <Typography color="text.secondary" gutterBottom>
        找不到地址 {location.pathname}
      </Typography>
      <Stack direction="row" spacing={1.5} justifyContent="center" sx={{ mt: 2 }}>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/news')}>返回首页</Button>
        <Button variant="outlined" onClick={() => navigate('/upload')}>前往上传</Button>
      </Stack>
    </Box>
  )
}

export default NotFoundPage
