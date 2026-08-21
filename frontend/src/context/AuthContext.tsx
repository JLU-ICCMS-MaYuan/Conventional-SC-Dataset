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
  created_at: string | null
  approved_at: string | null
}

export interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  login: (email: string, password: string) => Promise<{ needApproval?: boolean }>
  register: (email: string, password: string, username: string, realName: string, isAdmin: boolean) => Promise<{ requiresEmailVerification: boolean }>
  updateUsername: (username: string) => Promise<void>
  replaceUser: (user: User) => void
  verifyEmail: (email: string, code: string) => Promise<void>
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

async function responseError(res: Response, fallback: string): Promise<Error> {
  const data = await res.json().catch(() => ({}))
  return new Error(data.error || data.detail || fallback)
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
        }
      } catch {
        clearAuth()
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const res = await fetch('/api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!res.ok) {
      throw await responseError(res, '登录失败')
    }
    const data = await res.json()
    const loggedUser: User = data.user
    saveAuth(data.access_token, loggedUser)
    setToken(data.access_token)
    setUser(loggedUser)
    return {}
  }, [])

  const register = useCallback(async (email: string, password: string, username: string, realName: string, isAdmin: boolean) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, username, real_name: realName || undefined, is_admin: isAdmin }),
    })
    if (!res.ok) {
      throw await responseError(res, '注册失败')
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
    const res = await fetch('/api/auth/username', {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${authToken}` },
      body: JSON.stringify({ username }),
    })
    if (!res.ok) throw await responseError(res, '用户名修改失败')
    const data = await res.json()
    const updatedUser: User = data.user
    replaceUser(updatedUser)
  }, [replaceUser, token])

  const verifyEmail = useCallback(async (email: string, code: string) => {
    const res = await fetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    })
    if (!res.ok) {
      throw await responseError(res, '验证失败')
    }
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, updateUsername, replaceUser, verifyEmail, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
