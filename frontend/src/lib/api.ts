import { getStoredToken } from '../context/AuthContext'

function authHeaders(): HeadersInit {
  const token = getStoredToken()
  if (token) {
    return { Authorization: `Bearer ${token}` }
  }
  return {}
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...init,
    headers: {
      ...authHeaders(),
      ...(init?.headers as Record<string, string>),
    },
  })
  if (!response.ok) {
    const message = await response.text()
    const error = new Error(message || `HTTP ${response.status}`) as Error & { status?: number }
    error.status = response.status
    throw error
  }
  return response.json() as Promise<T>
}

function buildBody(data?: unknown): BodyInit | undefined {
  if (data == null) return undefined
  if (data instanceof FormData) return data
  return JSON.stringify(data)
}

function buildHeaders(data?: unknown): HeadersInit | undefined {
  if (data instanceof FormData) return undefined
  return { 'Content-Type': 'application/json' }
}

export const api = {
  get: <T>(url: string) => request<T>(url),

  post: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'POST',
      headers: buildHeaders(data),
      body: buildBody(data),
    }),

  put: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'PUT',
      headers: buildHeaders(data),
      body: buildBody(data),
    }),

  patch: <T>(url: string, data?: unknown) =>
    request<T>(url, {
      method: 'PATCH',
      headers: buildHeaders(data),
      body: buildBody(data),
    }),

  del: <T>(url: string) =>
    request<T>(url, { method: 'DELETE' }),

  postStream: (url: string, data?: unknown) =>
    fetch(url, {
      method: 'POST',
      headers: { ...authHeaders(), ...buildHeaders(data) },
      body: buildBody(data),
    }),
}
