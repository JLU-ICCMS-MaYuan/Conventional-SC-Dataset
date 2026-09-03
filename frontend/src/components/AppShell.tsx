import React, { useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { AppBar, Avatar, Box, Button, ListItemIcon, Menu, MenuItem, Toolbar, Typography } from '@mui/material'
import { Logout as LogoutIcon, Person as PersonIcon } from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import { useLanguage } from '../context/LanguageContext'
import type { Lang } from '../i18n'
import AuthDialog from './AuthDialog'
import LlmProviderSwitcher from './LlmProviderSwitcher'

// 导航项的标签走字典键，path 是路由契约不随语言变化。
const NAV_ITEMS = [
  { key: 'nav.news', path: '/news' },
  { key: 'nav.search', path: '/search' },
  { key: 'nav.knowledge', path: '/knowledge' },
  { key: 'nav.share', path: '/share' },
  { key: 'nav.upload', path: '/upload' },
  { key: 'nav.rag', path: '/rag' },
  { key: 'nav.tcPredict', path: '/tc-predict' },
]

const APP_BAR_HEIGHT = 72

const AppShell: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout } = useAuth()
  const { lang, setLang, t } = useLanguage()
  const [authOpen, setAuthOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const navItems = user
    ? [...NAV_ITEMS, { key: `enums.role.${user.role}`, path: '/account' }]
    : NAV_ITEMS
  const activeIndex = navItems.findIndex(item => location.pathname.startsWith(item.path))

  // 语言切换：两段式按钮。aria-pressed 表达当前生效语言——仅靠颜色高亮
  // 对读屏与色觉障碍用户不可达。
  const languageOptions: Array<{ value: Lang; shortKey: string; labelKey: string }> = [
    { value: 'zh', shortKey: 'nav.langZhShort', labelKey: 'nav.switchToZh' },
    { value: 'en', shortKey: 'nav.langEnShort', labelKey: 'nav.switchToEn' },
  ]

  const handleLogout = () => {
    setAnchorEl(null)
    logout()
    navigate('/news')
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '88px minmax(0, 1fr)', gridTemplateRows: `${APP_BAR_HEIGHT}px 1fr` }}>
      <AppBar position="sticky" color="inherit" sx={{ gridColumn: '1 / -1', zIndex: theme => theme.zIndex.appBar, minHeight: APP_BAR_HEIGHT, borderBottom: '1px solid', borderColor: 'divider', bgcolor: 'background.paper' }}>
        <Toolbar sx={{ minHeight: `${APP_BAR_HEIGHT}px !important`, px: 3, justifyContent: 'space-between' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box onClick={() => navigate('/')} sx={{ width: 40, height: 40, borderRadius: '12px', bgcolor: 'primary.main', color: 'primary.contrastText', display: 'grid', placeItems: 'center', boxShadow: 3, fontWeight: 700, cursor: 'pointer' }}>SC</Box>
            <Typography fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => navigate('/')}>SC-Wiki</Typography>
          </Box>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            {/* 语言切换控件位于头像左侧。Issue #73 的 AI 供应商切换器将排在本控件左侧。 */}
            <LlmProviderSwitcher />
            <Box
              role="group"
              aria-label={t('nav.languageGroup')}
              sx={{
                display: 'flex', border: '1px solid', borderColor: 'divider',
                borderRadius: '10px', overflow: 'hidden',
              }}
            >
              {languageOptions.map(option => {
                const isActive = lang === option.value
                return (
                  <Box
                    key={option.value}
                    component="button"
                    type="button"
                    aria-pressed={isActive}
                    aria-label={t(option.labelKey)}
                    onClick={() => setLang(option.value)}
                    sx={{
                      border: 0, px: 1.25, py: 0.5, cursor: 'pointer', fontSize: 12, fontWeight: 700,
                      bgcolor: isActive ? 'primary.main' : 'transparent',
                      color: isActive ? 'primary.contrastText' : 'text.secondary',
                      transition: 'background-color 0.2s, color 0.2s',
                      '&:hover': { bgcolor: isActive ? 'primary.dark' : 'action.hover' },
                      '&:focus-visible': { outline: '2px solid', outlineColor: 'primary.main', outlineOffset: 2 },
                    }}
                  >
                    {t(option.shortKey)}
                  </Box>
                )
              })}
            </Box>

            {user ? (
              <>
                <Button aria-label={t('nav.accountMenu')} onClick={event => setAnchorEl(event.currentTarget)} sx={{ minWidth: 44, p: 0.5, borderRadius: '50%' }}>
                  <Avatar src={user.avatar_url || undefined} sx={{ width: 36, height: 36, bgcolor: 'primary.main', fontSize: 14, fontWeight: 700 }}>
                    {user.username.charAt(0).toUpperCase()}
                  </Avatar>
                </Button>
                <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)} anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }} transformOrigin={{ horizontal: 'right', vertical: 'top' }} slotProps={{ paper: { sx: { minWidth: 160, mt: 1 } } }}>
                  <MenuItem onClick={handleLogout} sx={{ color: 'error.main' }}>
                    <ListItemIcon><LogoutIcon fontSize="small" color="error" /></ListItemIcon>
                    {t('nav.logout')}
                  </MenuItem>
                </Menu>
              </>
            ) : (
              <Button variant="outlined" size="small" startIcon={<PersonIcon />} onClick={() => setAuthOpen(true)} sx={{ borderRadius: '12px', textTransform: 'none', fontWeight: 600 }}>{t('nav.login')}</Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" aria-label={t('nav.mainNav')} sx={{
        bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider',
        display: 'flex', flexDirection: 'column', gap: 1, p: '16px 10px',
        position: 'sticky', top: `${APP_BAR_HEIGHT}px`, alignSelf: 'start',
        height: `calc(100vh - ${APP_BAR_HEIGHT}px)`, boxSizing: 'border-box', overflowY: 'auto',
        zIndex: theme => theme.zIndex.appBar - 1,
      }}>
        {activeIndex >= 0 && <Box sx={{ position: 'absolute', left: 10, top: 16, width: 68, height: 60, borderRadius: '18px', bgcolor: '#e0e7ff', transform: `translateY(${activeIndex * 68}px)`, transition: 'transform 0.35s cubic-bezier(0.4, 0, 0.2, 1)' }} />}
        {navItems.map(item => {
          const isActive = location.pathname.startsWith(item.path)
          return (
            <Box key={item.path} component="button" onClick={() => navigate(item.path)} sx={{ border: 0, width: 68, minHeight: 60, borderRadius: '18px', display: 'grid', placeItems: 'center', position: 'relative', zIndex: 1, color: isActive ? '#312e81' : 'text.secondary', bgcolor: 'transparent', fontSize: 11, fontWeight: 600, cursor: 'pointer', transition: 'color 0.25s', '&:hover': { color: '#312e81' } }}>
              {t(item.key)}
            </Box>
          )
        })}
      </Box>

      <Box component="main" sx={{ p: { xs: 2, md: 4 }, minWidth: 0, maxWidth: 1440, width: '100%', boxSizing: 'border-box', mx: 'auto' }}>
        <Outlet />
      </Box>
      <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} />
    </Box>
  )
}

export default AppShell
