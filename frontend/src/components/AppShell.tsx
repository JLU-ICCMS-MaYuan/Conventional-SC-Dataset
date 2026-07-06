import React from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import { Box, AppBar, Toolbar, Typography } from '@mui/material'

const NAV_ITEMS = [
  { label: '热点', path: '/charts' },
  { label: '探索', path: '/search' },
  { label: '分享', path: '/share' },
  { label: '对话', path: '/rag' },
  { label: '预测', path: '/tc-predict' },
]

const AppShell: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '88px 1fr', gridTemplateRows: '72px 1fr' }}>
      <AppBar
        position="sticky"
        color="inherit"
        sx={{
          gridColumn: '1 / -1', zIndex: 10, minHeight: 72,
          borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'background.paper',
        }}
      >
        <Toolbar sx={{ minHeight: '72px !important', px: 3, justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ width: 40, height: 40, borderRadius: '12px', bgcolor: 'primary.main', color: 'primary.contrastText', display: 'grid', placeItems: 'center', boxShadow: 3, fontWeight: 700 }}>SC</Box>
            <Typography fontWeight={700}>SC-Wiki</Typography>
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{ bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider', display: 'flex', flexDirection: 'column', gap: 1, p: '16px 10px' }}>
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname.startsWith(item.path)
          return (
            <Box
              key={item.label}
              component="button"
              onClick={() => navigate(item.path)}
              sx={{
                border: 0, width: 68, minHeight: 60, borderRadius: '18px',
                display: 'grid', placeItems: 'center',
                color: isActive ? '#312e81' : 'text.secondary',
                bgcolor: isActive ? '#e0e7ff' : 'transparent',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
                '&:hover': { bgcolor: isActive ? '#e0e7ff' : 'action.hover' },
              }}
            >
              {item.label}
            </Box>
          )
        })}
      </Box>

      <Box component="main" sx={{ p: 4, maxWidth: 1440, width: '100%', mx: 'auto' }}>
        <Outlet />
      </Box>
    </Box>
  )
}

export default AppShell
