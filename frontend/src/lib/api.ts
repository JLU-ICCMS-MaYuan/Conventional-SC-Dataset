import { getStoredToken } from '../context/AuthContext'
import { buildLlmHeaders } from './llmProvider'

export interface ApiError extends Error {
  status?: number
  code?: string
  detail?: unknown
  existingPaperId?: number
}

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
      ...buildLlmHeaders(),
      ...(init?.headers as Record<string, string>),
    },
  })
  if (!response.ok) {
    const text = await response.text()
    let body: any = null
    try { body = text ? JSON.parse(text) : null } catch { /* plain text response */ }
    const detail = body?.detail ?? body
    const message = typeof detail === 'string'
      ? detail
      : detail?.message || detail?.detail || body?.error || body?.message || text || `HTTP ${response.status}`
    const error = new Error(message) as ApiError
    error.status = response.status
    error.code = detail?.code || body?.code
    error.detail = detail
    error.existingPaperId = detail?.existing_paper_id || body?.existing_paper_id
    throw error
  }
  if (response.status === 204) return undefined as T
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
  get: <T>(url: string, init?: RequestInit) => request<T>(url, init),

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

  download: async (url: string) => {
    const response = await fetch(url, { headers: authHeaders() })
    if (!response.ok) {
      const text = await response.text()
      throw new Error(text || `HTTP ${response.status}`)
    }
    return response.blob()
  },

  postStream: (url: string, data?: unknown) =>
    fetch(url, {
      method: 'POST',
      headers: { ...authHeaders(), ...buildLlmHeaders(), ...buildHeaders(data) },
      body: buildBody(data),
    }),
}
