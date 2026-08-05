const BASE_URL = '/api/v1'
export const API_REQUEST_TIMEOUT_MS = 15_000

export type ApiRequestInit = RequestInit & {
  /** Timeout for this request; the caller's AbortSignal is still respected. */
  timeoutMs?: number
}

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
  options?: ApiRequestInit,
): Promise<T> {
  const { timeoutMs = API_REQUEST_TIMEOUT_MS, signal: externalSignal, ...requestInit } = options || {}
  const headers = new Headers(requestInit.headers)
  if (!(requestInit.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  const controller = new AbortController()
  let timedOut = false
  const abortFromCaller = () => controller.abort(externalSignal?.reason)
  if (externalSignal) {
    if (externalSignal.aborted) abortFromCaller()
    else externalSignal.addEventListener('abort', abortFromCaller, { once: true })
  }
  const timeout = globalThis.setTimeout(() => {
    timedOut = true
    controller.abort()
  }, timeoutMs)

  try {
    const res = await fetch(`${BASE_URL}${path}`, {
      ...requestInit,
      headers,
      signal: controller.signal,
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
  } catch (error) {
    if (timedOut) {
      throw new ApiRequestError('Request timed out', 408)
    }
    throw error
  } finally {
    globalThis.clearTimeout(timeout)
    externalSignal?.removeEventListener('abort', abortFromCaller)
  }
}
