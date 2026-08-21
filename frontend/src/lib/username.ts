export const USERNAME_PATTERN = /^[A-Za-z][A-Za-z0-9_]{2,31}$/

const RESERVED_USERNAMES = new Set([
  'admin', 'administrator', 'root', 'scwiki', 'superadmin', 'system',
])

export interface UsernameAvailability {
  available: boolean
  reason?: string
}
export const usernameValidationError = (username: string): string => {
  if (!USERNAME_PATTERN.test(username)) {
    return '用户名须为 3–32 位，以字母开头且只包含字母、数字和下划线'
  }
  const normalized = username.toLowerCase()
  if (normalized.startsWith('sc_')) return 'sc_ 前缀由系统保留'
  if (RESERVED_USERNAMES.has(normalized)) return '该用户名由系统保留'
  return ''
}

export const checkUsernameAvailability = async (username: string): Promise<UsernameAvailability> => {
  const localError = usernameValidationError(username)
  if (localError) return { available: false, reason: localError }
  const response = await fetch(`/api/auth/username-availability?username=${encodeURIComponent(username)}`)
  if (!response.ok) throw new Error('用户名检查失败')
  return response.json()
}
