async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init)
  if (!response.ok) {
    const message = await response.text()
    throw new Error(message || `HTTP ${response.status}`)
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

  postStream: (url: string, data?: unknown) =>
    fetch(url, {
      method: 'POST',
      headers: buildHeaders(data),
      body: buildBody(data),
    }),
}
