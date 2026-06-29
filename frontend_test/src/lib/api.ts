const BASE = ''

async function request<T = any>(url: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('token')
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string> || {}),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }

  const response = await fetch(`${BASE}${url}`, {
    ...options,
    headers,
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const detail = data.detail || data
    const message = detail.message || detail.detail || `请求失败：HTTP ${response.status}`
    throw new Error(message)
  }

  return data
}

export const api = {
  get: <T = any>(url: string) => request<T>(url),

  post: <T = any>(url: string, body?: any) =>
    request<T>(url, {
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body),
    }),

  postStream: (url: string, body: any) =>
    fetch(`${BASE}${url}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(localStorage.getItem('token') ? { Authorization: `Bearer ${localStorage.getItem('token')}` } : {}),
      },
      body: JSON.stringify(body),
    }),
}
