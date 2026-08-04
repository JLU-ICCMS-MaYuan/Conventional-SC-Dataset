import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

export interface User {
  id: number
  email: string
  real_name: string
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
  register: (email: string, password: string, realName: string, isAdmin: boolean) => Promise<void>
  verifyEmail: (email: string, code: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthState>({
  user: null,
  token: null,
  loading: true,
  login: async () => ({}),
  register: async () => {},
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
        setToken(savedToken)
        setUser(parsed)
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
      const err = await res.json().catch(() => ({ detail: '登录失败' }))
      throw new Error(err.detail || '登录失败')
    }
    const data = await res.json()
    const loggedUser: User = data.user
    saveAuth(data.access_token, loggedUser)
    setToken(data.access_token)
    setUser(loggedUser)
    return {}
  }, [])

  const register = useCallback(async (email: string, password: string, realName: string, isAdmin: boolean) => {
    const res = await fetch('/api/auth/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, real_name: realName, is_admin: isAdmin }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '注册失败' }))
      throw new Error(err.detail || '注册失败')
    }
  }, [])

  const verifyEmail = useCallback(async (email: string, code: string) => {
    const res = await fetch('/api/auth/verify-email', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, code }),
    })
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: '验证失败' }))
      throw new Error(err.detail || '验证失败')
    }
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setToken(null)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, verifyEmail, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
