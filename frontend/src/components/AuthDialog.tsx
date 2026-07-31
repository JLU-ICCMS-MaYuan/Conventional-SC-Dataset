import React, { useState } from 'react'
import {
  Dialog, DialogTitle, DialogContent, DialogActions,
  Button, TextField, Typography, Tabs, Tab, Box, IconButton,
  InputAdornment, CircularProgress, Alert, Checkbox, FormControlLabel,
} from '@mui/material'
import {
  Visibility, VisibilityOff, Close, Login as LoginIcon,
} from '@mui/icons-material'
import { useAuth } from '../context/AuthContext'

type Step = 'form' | 'verify' | 'done'

interface Props {
  open: boolean
  onClose: () => void
}

const AuthDialog: React.FC<Props> = ({ open, onClose }) => {
  const { login, register, verifyEmail } = useAuth()

  // tab
  const [tab, setTab] = useState(0)  // 0=login, 1=register

  // login
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [showLoginPw, setShowLoginPw] = useState(false)

  // register
  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regName, setRegName] = useState('')
  const [regIsAdmin, setRegIsAdmin] = useState(false)
  const [showRegPw, setShowRegPw] = useState(false)

  // verify
  const [verifyCode, setVerifyCode] = useState('')

  // shared
  const [step, setStep] = useState<Step>('form')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [doneMessage, setDoneMessage] = useState('')

  const reset = () => {
    setStep('form')
    setTab(0)
    setLoginEmail(''); setLoginPassword(''); setShowLoginPw(false)
    setRegEmail(''); setRegPassword(''); setRegName(''); setRegIsAdmin(false); setShowRegPw(false)
    setVerifyCode('')
    setError('')
    setDoneMessage('')
  }

  const handleClose = () => {
    reset()
    onClose()
  }

  // ── Login ─────────────────────────────────────────
  const handleLogin = async () => {
    setError('')
    if (!loginEmail || !loginPassword) { setError('请填写邮箱和密码'); return }
    setLoading(true)
    try {
      const result = await login(loginEmail, loginPassword)
      if (result.needApproval) {
        setDoneMessage('登录失败：您的管理员申请尚未通过审批')
        setStep('done')
      } else {
        handleClose()
      }
    } catch (e: unknown) {
      setError((e as Error).message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  // ── Register → verify ─────────────────────────────
  const handleRegister = async () => {
    setError('')
    if (!regEmail || !regPassword || !regName) { setError('请填写所有必填项'); return }
    if (regPassword.length < 6) { setError('密码至少 6 位'); return }
    setLoading(true)
    try {
      await register(regEmail, regPassword, regName, regIsAdmin)
      setStep('verify')
    } catch (e: unknown) {
      setError((e as Error).message || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async () => {
    setError('')
    if (!verifyCode) { setError('请输入验证码'); return }
    setLoading(true)
    try {
      await verifyEmail(regEmail, verifyCode)
      setDoneMessage(regIsAdmin
        ? '邮箱验证成功！管理员申请已提交，请等待超级管理员审批'
        : '注册成功！您现在可以登录了')
      setStep('done')
    } catch (e: unknown) {
      setError((e as Error).message || '验证失败')
    } finally {
      setLoading(false)
    }
  }

  // ═══════════════════════════════════════════════════
  // Render helpers
  // ═══════════════════════════════════════════════════
  const loginForm = (
    <Box component="form" sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}
         onSubmit={e => { e.preventDefault(); handleLogin() }}>
      <TextField
        label="邮箱" type="email" autoFocus fullWidth size="small"
        value={loginEmail} onChange={e => setLoginEmail(e.target.value)}
      />
      <TextField
        label="密码" type={showLoginPw ? 'text' : 'password'} fullWidth size="small"
        value={loginPassword} onChange={e => setLoginPassword(e.target.value)}
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton size="small" onClick={() => setShowLoginPw(!showLoginPw)} edge="end">
                {showLoginPw ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
      {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
      <Button
        variant="contained" fullWidth type="submit" disabled={loading}
        startIcon={loading ? <CircularProgress size={18} color="inherit" /> : <LoginIcon />}
      >
        登录
      </Button>
    </Box>
  )

  const registerForm = (
    <Box component="form" sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}
         onSubmit={e => { e.preventDefault(); handleRegister() }}>
      <TextField
        label="姓名" fullWidth size="small" autoFocus
        value={regName} onChange={e => setRegName(e.target.value)}
      />
      <TextField
        label="邮箱" type="email" fullWidth size="small"
        value={regEmail} onChange={e => setRegEmail(e.target.value)}
      />
      <TextField
        label="密码" type={showRegPw ? 'text' : 'password'} fullWidth size="small"
        value={regPassword} onChange={e => setRegPassword(e.target.value)}
        helperText="至少 6 位"
        InputProps={{
          endAdornment: (
            <InputAdornment position="end">
              <IconButton size="small" onClick={() => setShowRegPw(!showRegPw)} edge="end">
                {showRegPw ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
              </IconButton>
            </InputAdornment>
          ),
        }}
      />
      <FormControlLabel
        control={<Checkbox checked={regIsAdmin} onChange={e => setRegIsAdmin(e.target.checked)} size="small" />}
        label={<Typography variant="body2" color="text.secondary">申请成为管理员（需超级管理员审批）</Typography>}
      />
      {error && <Alert severity="error" sx={{ py: 0 }}>{error}</Alert>}
      <Button
        variant="outlined" fullWidth type="submit" disabled={loading}
        startIcon={loading ? <CircularProgress size={18} color="inherit" /> : undefined}
      >
        注册
      </Button>
    </Box>
  )

  const verifyStep = (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1, alignItems: 'center' }}>
      <Alert severity="info" sx={{ width: '100%' }}>
        验证码已发送至 <strong>{regEmail}</strong>，请查收邮件
      </Alert>
      <TextField
        label="6 位验证码" autoFocus fullWidth size="small"
        value={verifyCode} onChange={e => setVerifyCode(e.target.value)}
        inputProps={{ maxLength: 6 }}
        sx={{ maxWidth: 220 }}
      />
      {error && <Alert severity="error" sx={{ py: 0, width: '100%' }}>{error}</Alert>}
      <Button
        variant="contained" fullWidth sx={{ maxWidth: 220 }}
        onClick={handleVerify} disabled={loading}
        startIcon={loading ? <CircularProgress size={18} color="inherit" /> : undefined}
      >
        验证
      </Button>
    </Box>
  )

  const doneStep = (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1, alignItems: 'center' }}>
      <Alert severity="success" sx={{ width: '100%' }}>{doneMessage}</Alert>
      <Button variant="contained" onClick={handleClose} sx={{ minWidth: 120 }}>
        {regIsAdmin ? '关闭' : '前往登录'}
      </Button>
    </Box>
  )

  // ═══════════════════════════════════════════════════
  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', pb: 0, fontSize: '1.25rem', fontWeight: 600 }}>
        <Box component="span">
          {step === 'verify' ? '验证邮箱' : step === 'done' ? '完成' : '登录 / 注册'}
        </Box>
        <IconButton size="small" onClick={handleClose}><Close fontSize="small" /></IconButton>
      </DialogTitle>

      <DialogContent>
        {step === 'form' && (
          <>
            <Tabs value={tab} onChange={(_, v) => { setTab(v); setError('') }}
                  variant="fullWidth" sx={{ mb: 1 }}>
              <Tab label="登录" />
              <Tab label="注册" />
            </Tabs>
            {tab === 0 ? loginForm : registerForm}
          </>
        )}
        {step === 'verify' && verifyStep}
        {step === 'done' && doneStep}
      </DialogContent>

      {step === 'form' && (
        <DialogActions sx={{ justifyContent: 'center', pb: 2 }}>
          <Typography variant="caption" color="text.disabled">
            {tab === 0 ? '还没有账号？切换到「注册」标签' : '已有账号？切换到「登录」标签'}
          </Typography>
        </DialogActions>
      )}
    </Dialog>
  )
}

export default AuthDialog
