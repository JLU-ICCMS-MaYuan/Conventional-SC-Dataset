const BASE = ''

export function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request(method: string, url: string, body?: any): Promise<any> {
  const headers: Record<string, string> = {}
  const token = getToken()
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (body && !(body instanceof FormData)) {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BASE}${url}`, {
    method,
    headers,
    body: body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`${res.status}: ${text.slice(0, 200)}`)
  }
  return res.json()
}

export async function requestJson(url: string, opts?: Record<string, any>): Promise<any> {
  const method = opts?.method || 'GET'
  const body = opts?.body
  return request(method, url, body)
}

export async function postJson<T = any>(url: string, body?: any): Promise<T> {
  return request('POST', url, body)
}

export async function putJson<T = any>(url: string, body: any): Promise<T> {
  return request('PUT', url, body)
}
