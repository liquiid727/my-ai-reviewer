import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiRequestError, apiRequest } from './client'

describe('apiRequest cancellation and timeout ownership', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  it('converts a request timeout into a safe 408 error and aborts fetch', async () => {
    let requestSignal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: string, init?: RequestInit) => {
        requestSignal = init?.signal ?? undefined
        return new Promise((_resolve, reject) => {
          requestSignal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {
            once: true,
          })
        })
      }),
    )

    const request = apiRequest('/slow', { timeoutMs: 100 })
    const result = expect(request).rejects.toBeInstanceOf(ApiRequestError)
    await vi.advanceTimersByTimeAsync(100)

    await result
    expect(requestSignal?.aborted).toBe(true)
    await expect(request).rejects.toMatchObject({ status: 408 })
  })

  it('preserves caller cancellation instead of misreporting it as a timeout', async () => {
    let requestSignal: AbortSignal | undefined
    vi.stubGlobal(
      'fetch',
      vi.fn((_input: string, init?: RequestInit) => {
        requestSignal = init?.signal ?? undefined
        return new Promise((_resolve, reject) => {
          requestSignal?.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {
            once: true,
          })
        })
      }),
    )

    const caller = new AbortController()
    const request = apiRequest('/cancelled', { timeoutMs: 1000, signal: caller.signal })
    caller.abort()

    await expect(request).rejects.not.toMatchObject({ status: 408 })
    expect(requestSignal?.aborted).toBe(true)
  })
})
