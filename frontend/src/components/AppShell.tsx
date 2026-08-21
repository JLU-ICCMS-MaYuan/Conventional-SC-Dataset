import React, { useState } from 'react'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import {
  Box, AppBar, Toolbar, Typography, Button, Avatar,
  Menu, MenuItem, ListItemIcon, Divider, Chip, Dialog, DialogTitle,
  DialogContent, DialogActions, Alert, CircularProgress,
} from '@mui/material'
import {
  Person as PersonIcon,
  Logout as LogoutIcon,
  AdminPanelSettings as AdminIcon,
  DriveFileRenameOutline as RenameIcon,
} from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'
import AuthDialog from './AuthDialog'
import UsernameField from './UsernameField'

const NAV_ITEMS = [
  { label: '热点', path: '/news' },
  { label: '探索', path: '/search' },
  { label: '脉络', path: '/knowledge' },
  { label: '社区', path: '/share' },
  { label: '上传', path: '/upload' },
  { label: '对话', path: '/rag' },
  { label: '预测', path: '/tc-predict' },
]

const ROLE_LABELS: Record<string, string> = {
  superadmin: '超级管理员',
  admin: '管理员',
  user: '用户',
}

const AppShell: React.FC = () => {
  const navigate = useNavigate()
  const location = useLocation()
  const { user, logout, updateUsername } = useAuth()

  const [authOpen, setAuthOpen] = useState(false)
  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null)
  const [usernameOpen, setUsernameOpen] = useState(false)
  const [newUsername, setNewUsername] = useState('')
  const [usernameError, setUsernameError] = useState('')
  const [usernameSaving, setUsernameSaving] = useState(false)
  const menuOpen = Boolean(anchorEl)

  const handleMenuOpen = (e: React.MouseEvent<HTMLElement>) => setAnchorEl(e.currentTarget)
  const handleMenuClose = () => setAnchorEl(null)

  const handleLogout = () => {
    handleMenuClose()
    logout()
  }

  const handleUsernameUpdate = async () => {
    setUsernameError('')
    setUsernameSaving(true)
    try {
      await updateUsername(newUsername)
      setUsernameOpen(false)
      setNewUsername('')
    } catch (error) {
      setUsernameError((error as Error).message)
    } finally {
      setUsernameSaving(false)
    }
  }

  return (
    <Box sx={{ minHeight: '100vh', display: 'grid', gridTemplateColumns: '88px minmax(0, 1fr)', gridTemplateRows: '72px 1fr' }}>
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
            <Box sx={{ width: 40, height: 40, borderRadius: '12px', bgcolor: 'primary.main', color: 'primary.contrastText', display: 'grid', placeItems: 'center', boxShadow: 3, fontWeight: 700, cursor: 'pointer' }}
                 onClick={() => navigate('/')}
            >SC</Box>
            <Typography fontWeight={700} sx={{ cursor: 'pointer' }} onClick={() => navigate('/')}>SC-Wiki</Typography>
          </Box>

          {/* ── 右侧登录 / 用户菜单 ── */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            {user ? (
              <>
                <Button
                  onClick={handleMenuOpen}
                  sx={{ textTransform: 'none', color: 'text.primary', gap: 1 }}
                >
                  <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14, fontWeight: 600 }}>
                    {user.username.charAt(0).toUpperCase()}
                  </Avatar>
                  <Box sx={{ textAlign: 'left', display: { xs: 'none', sm: 'block' } }}>
                    <Typography variant="body2" fontWeight={600} lineHeight={1.3}>
                      {user.username}
                    </Typography>
                    <Typography variant="caption" color="text.secondary" lineHeight={1}>
                      {ROLE_LABELS[user.role] || user.role}
                    </Typography>
                  </Box>
                </Button>
                <Menu
                  anchorEl={anchorEl}
                  open={menuOpen}
                  onClose={handleMenuClose}
                  anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
                  transformOrigin={{ horizontal: 'right', vertical: 'top' }}
                  slotProps={{ paper: { sx: { minWidth: 200, mt: 1 } } }}
                >
                  <Box sx={{ px: 2, py: 1 }}>
                    <Typography variant="body2" fontWeight={600}>{user.username}</Typography>
                    <Typography variant="caption" color="text.secondary">{user.email}</Typography>
                    <Chip
                      size="small"
                      label={ROLE_LABELS[user.role] || user.role}
                      color={user.role === 'superadmin' ? 'error' : user.role === 'admin' ? 'primary' : 'default'}
                      sx={{ mt: 0.5, height: 20, fontSize: 11 }}
                    />
                  </Box>
                  <Divider />
                  {user.username_change_allowed && (
                    <>
                      <Box sx={{ px: 2, py: 1 }}>
                        <Alert severity="info" sx={{ py: 0 }}>可设置一次正式用户名</Alert>
                      </Box>
                      <MenuItem onClick={() => { handleMenuClose(); setUsernameOpen(true) }}>
                        <ListItemIcon><RenameIcon fontSize="small" /></ListItemIcon>
                        设置用户名
                      </MenuItem>
                    </>
                  )}
                  {(user.role === 'admin' || user.role === 'superadmin') && (
                    <MenuItem onClick={() => { handleMenuClose(); navigate('/admin') }}>
                      <ListItemIcon><AdminIcon fontSize="small" /></ListItemIcon>
                      管理后台
                    </MenuItem>
                  )}
                  <MenuItem onClick={handleLogout}>
                    <ListItemIcon><LogoutIcon fontSize="small" /></ListItemIcon>
                    退出登录
                  </MenuItem>
                </Menu>
              </>
            ) : (
              <Button
                variant="outlined"
                size="small"
                startIcon={<PersonIcon />}
                onClick={() => setAuthOpen(true)}
                sx={{ borderRadius: '12px', textTransform: 'none', fontWeight: 600 }}
              >
                登录
              </Button>
            )}
          </Box>
        </Toolbar>
      </AppBar>

      <Box component="nav" sx={{
        bgcolor: 'background.paper', borderRight: '1px solid', borderColor: 'divider',
        display: 'flex', flexDirection: 'column', gap: 1, p: '16px 10px', position: 'relative',
      }}>
        {/* Sliding pill — moves to active item */}
        <Box sx={{
          position: 'absolute', left: 10, top: 16,
          width: 68, height: 60, borderRadius: '18px',
          bgcolor: '#e0e7ff',
          transform: `translateY(${NAV_ITEMS.findIndex(i => location.pathname.startsWith(i.path)) * 68}px)`,
          transition: 'transform 0.35s cubic-bezier(0.4, 0, 0.2, 1)',
          ...(NAV_ITEMS.every(i => !location.pathname.startsWith(i.path)) && { opacity: 0 }),
        }} />
        {NAV_ITEMS.map((item) => {
          const isActive = location.pathname.startsWith(item.path)
          return (
            <Box
              key={item.label}
              component="button"
              onClick={() => navigate(item.path)}
              sx={{
                border: 0, width: 68, minHeight: 60, borderRadius: '18px',
                display: 'grid', placeItems: 'center', position: 'relative', zIndex: 1,
                color: isActive ? '#312e81' : 'text.secondary',
                bgcolor: 'transparent',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
                transition: 'color 0.25s',
                '&:hover': { color: '#312e81' },
              }}
            >
              {item.label}
            </Box>
          )
        })}
      </Box>

      <Box component="main" sx={{ p: { xs: 2, md: 4 }, minWidth: 0, maxWidth: 1440, width: '100%', boxSizing: 'border-box', mx: 'auto' }}>
        <Outlet />
      </Box>

      {/* 登录 / 注册弹窗 */}
      <AuthDialog open={authOpen} onClose={() => setAuthOpen(false)} />

      <Dialog open={usernameOpen} onClose={() => !usernameSaving && setUsernameOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>设置正式用户名</DialogTitle>
        <DialogContent sx={{ pt: '12px !important' }}>
          <Alert severity="warning" sx={{ mb: 2 }}>该用户名只能由你修改一次，提交前请仔细确认。</Alert>
          <UsernameField value={newUsername} onChange={setNewUsername} autoFocus />
          {usernameError && <Alert severity="error" sx={{ mt: 2 }}>{usernameError}</Alert>}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setUsernameOpen(false)} disabled={usernameSaving}>取消</Button>
          <Button variant="contained" onClick={() => void handleUsernameUpdate()} disabled={usernameSaving || !newUsername}>
            {usernameSaving ? <CircularProgress size={18} /> : '确认设置'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

export default AppShell
