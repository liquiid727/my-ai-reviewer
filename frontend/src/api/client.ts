const BASE_URL = '/api/v1'

export class ApiRequestError extends Error {
  readonly status: number
  readonly code?: number
  readonly data?: unknown

  constructor(message: string, status: number, code?: number, data?: unknown) {
    super(message)
    this.name = 'ApiRequestError'
    this.status = status
    this.code = code
    this.data = data
  }
}

export async function apiRequest<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const headers = new Headers(options?.headers)
  if (!(options?.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers,
  })
  const responseBody = await res.json().catch(() => undefined)
  if (!res.ok) {
    const body = responseBody as { code?: number; message?: string; data?: unknown } | undefined
    throw new ApiRequestError(
      body?.message || `API error: ${res.status}`,
      res.status,
      body?.code,
      body?.data,
    )
  }
  return responseBody as T
}
