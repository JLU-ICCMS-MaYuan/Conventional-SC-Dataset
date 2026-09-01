import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

export interface User {
  id: number
  email: string
  username: string
  username_change_allowed: boolean
  role: 'user' | 'admin' | 'superadmin'
  is_admin: boolean
  is_superadmin: boolean
  is_approved: boolean
  is_email_verified: boolean
  account_status: 'active' | 'banned' | 'deactivated'
  avatar_url?: string | null
  created_at: string | null
  approved_at: string | null
}

export interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<{ needApproval?: boolean }>
  register: (email: string, password: string, username: string, realName: string) => Promise<{ requiresEmailVerification: boolean }>
  updateUsername: (username: string) => Promise<void>
  replaceUser: (user: User) => void
  verifyEmail: (email: string, code: string) => Promise<void>
  resendVerification: (email: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: async () => ({}),
  register: async () => ({ requiresEmailVerification: false }),
  updateUsername: async () => {},
  replaceUser: () => {},
  verifyEmail: async () => {},
  resendVerification: async () => {},
  logout: () => {},
})

export const useAuth = () => useContext(AuthContext)

const TOKEN_KEY = 'auth_token'
const USER_KEY = 'auth_user'

function saveAuth(token: string, user: User) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

/**
 * 认证错误码机制。
 *
 * AuthContext 是模块（非组件渲染路径），不能使用 useLanguage。因此本文件抛出的
 * Error.message 一律是稳定的机器键（如 'loginFailed'、'invalidCredentials'），
 * 由消费组件（AuthDialog / AccountPage）在渲染时用 `t('account.' + message)`
 * 映射为界面文案，从而随语言切换。
 *
 * 后端返回的中文 detail 是服务端数据（backend/api/auth_routes.py 的常量），
 * 此处按已知常量归类为机器键；未知名回退到调用方传入的 fallback 机器键，
 * 保证前端永远不直接展示后端原文。
 */
const SERVER_DETAIL_TO_CODE: Record<string, string> = {
  '邮箱或密码错误': 'invalidCredentials',
  '邮箱未验证，请先完成邮箱验证': 'emailNotVerified',
  '您的管理员申请尚未通过审批，请耐心等待': 'approvalPending',
  '该邮箱已注册': 'emailRegistered',
  '该邮箱已占用其他用户名': 'emailTaken',
  '用户名已被占用': 'usernameTaken',
  '邮箱或用户名已被占用': 'emailOrUsernameTaken',
  '发送验证码失败，请稍后重试': 'sendCodeFailed',
  '用户不存在，请先注册': 'userNotFound',
  '邮箱已验证，请直接登录': 'alreadyVerified',
  '验证码错误': 'invalidCode',
  '验证码已过期，请重新获取': 'codeExpired',
  '登录已失效': 'sessionExpired',
}

async function responseError(res: Response, fallback: string): Promise<Error> {
  const data = await res.json().catch(() => ({}))
  const detail = data.error || data.detail
  const code = typeof detail === 'string' ? SERVER_DETAIL_TO_CODE[detail] : undefined
  return new Error(code || fallback)
}

/** 包装 fetch：网络层失败（TypeError）统一归类为机器键，避免浏览器英文原文透出。 */
async function authFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(input, init)
  } catch {
    throw new Error('networkError')
  }
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const savedToken = localStorage.getItem(TOKEN_KEY)
    const savedUser = localStorage.getItem(USER_KEY)
    if (savedToken && savedUser) {
      try {
        const parsed = JSON.parse(savedUser) as User
        if (!parsed.username) {
          clearAuth()
        } else {
          setToken(savedToken)
          setUser(parsed)
          void authFetch('/api/auth/me', { headers: { Authorization: `Bearer ${savedToken}` } })
            .then(async response => {
              if (!response.ok) throw new Error('sessionExpired')
              const data = await response.json()
              saveAuth(savedToken, data.user)
              setUser(data.user)
            })
            .catch(() => {
              clearAuth()
              setToken(null)
              setUser(null)
            })
        }
      } catch {
        clearAuth()
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await authFetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      throw await responseError(res, 'loginFailed')
    }
    const data = await res.json()
    const loggedUser: User = data.user
    saveAuth(data.access_token, loggedUser)
    setToken(data.access_token)
    setUser(loggedUser)
    return {}
  }, [])

  const register = useCallback(async (email: string, password: string, username: string, realName: string) => {
    const res = await authFetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username, real_name: realName || undefined }),
    })
    if (!res.ok) {
      throw await responseError(res, 'registerFailed')
    }
    const data = await res.json()
    return { requiresEmailVerification: Boolean(data.requires_email_verification) }
  }, [])

  const replaceUser = useCallback((nextUser: User) => {
    const authToken = token || getStoredToken()
    if (authToken) saveAuth(authToken, nextUser)
    setUser(nextUser)
  }, [token])

  const updateUsername = useCallback(async (username: string) => {
    const authToken = token || getStoredToken()
    const res = await authFetch('/api/auth/username', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ username }),
    })
    if (!res.ok) throw await responseError(res, 'usernameUpdateFailed')
    const data = await res.json()
    const updatedUser: User = data.user
    replaceUser(updatedUser)
  }, [replaceUser, token])

  const verifyEmail = useCallback(async (email: string, code: string) => {
    const res = await authFetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    })
    if (!res.ok) {
      throw await responseError(res, 'verifyFailed')
    }
    const data = await res.json()
    saveAuth(data.access_token, data.user)
    setToken(data.access_token)
    setUser(data.user)
  }, [])

  const resendVerification = useCallback(async (email: string) => {
    const res = await authFetch('/api/auth/resend-verification', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    })
    if (!res.ok) throw await responseError(res, 'resendFailed')
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, updateUsername, replaceUser, verifyEmail, resendVerification, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
