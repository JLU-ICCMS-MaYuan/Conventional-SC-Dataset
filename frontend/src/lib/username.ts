export const USERNAME_PATTERN = /^[A-Za-z][A-Za-z0-9_]{2,31}$/

const RESERVED_USERNAMES = new Set([
  'admin', 'administrator', 'root', 'scwiki', 'superadmin', 'system',
])

export interface UsernameAvailability {
  available: boolean
  reason?: string
}

/**
 * 返回机器键而非文案：格式错误、sc_ 前缀保留、系统保留名分别对应
 * 'format' | 'sc_prefix' | 'reserved'，合法返回 ''。
 * 展示文案由 UsernameField 按 t('admin.usernameError.<key>') 映射。
 */
export type UsernameValidationErrorKey = '' | 'format' | 'sc_prefix' | 'reserved'
export const usernameValidationError = (username: string): UsernameValidationErrorKey => {
  if (!USERNAME_PATTERN.test(username)) {
    return 'format'
  }
  const normalized = username.toLowerCase()
  if (normalized.startsWith('sc_')) return 'sc_prefix'
  if (RESERVED_USERNAMES.has(normalized)) return 'reserved'
  return ''
}

export const checkUsernameAvailability = async (username: string): Promise<UsernameAvailability> => {
  const localError = usernameValidationError(username)
  if (localError) return { available: false, reason: localError }
  const response = await fetch(`/api/auth/username-availability?username=${encodeURIComponent(username)}`)
  if (!response.ok) throw new Error('checkFailed')
  return response.json()
}
