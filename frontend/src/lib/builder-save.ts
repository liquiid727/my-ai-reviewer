import { ApiRequestError } from '@/api/client'
import { AssistantApiError } from '@/api/builder'

/** Builder draft save status shown in the toolbar. */
export type BuilderSaveStatus = 'idle' | 'saving' | 'saved' | 'error' | 'conflict'

export type BuilderSaveOutcome =
  | { kind: 'success'; revision: number }
  | { kind: 'conflict'; message: string }
  | { kind: 'error'; message: string }

/** Known envelope / HTTP signals for optimistic-concurrency failures. */
const CONFLICT_CODES = new Set([1007, 409])

function isConflictCode(code: number | undefined): boolean {
  return typeof code === 'number' && CONFLICT_CODES.has(code)
}

function messageFromUnknown(err: unknown, fallback: string): string {
  if (err instanceof Error && err.message) return err.message
  if (typeof err === 'string' && err.trim()) return err
  return fallback
}

/**
 * Map a successful HTTP envelope from updateDraft into a save outcome.
 * Non-zero business codes (including revision conflict 1007) become failures.
 */
export function mapBuilderSaveResponse(
  res: { code: number; message?: string; data?: { revision?: number } },
  fallbackMessage: string,
): BuilderSaveOutcome {
  if (isConflictCode(res.code)) {
    return {
      kind: 'conflict',
      message: res.message || fallbackMessage,
    }
  }
  if (res.code !== 0) {
    return {
      kind: 'error',
      message: res.message || fallbackMessage,
    }
  }
  const revision = res.data?.revision
  if (typeof revision !== 'number') {
    return { kind: 'error', message: fallbackMessage }
  }
  return { kind: 'success', revision }
}

export type BuilderSaveFailure =
  | { kind: 'conflict'; message: string }
  | { kind: 'error'; message: string }

/**
 * Map thrown client errors (ApiRequestError / AssistantApiError / generic) to outcomes.
 */
export function mapBuilderSaveError(err: unknown, fallbackMessage: string): BuilderSaveFailure {
  if (err instanceof AssistantApiError) {
    if (err.status === 409 || isConflictCode(err.status)) {
      return { kind: 'conflict', message: messageFromUnknown(err, fallbackMessage) }
    }
    const detail = err.detail
    if (detail && typeof detail === 'object' && detail !== null) {
      const body = detail as { code?: number; message?: string }
      if (isConflictCode(body.code)) {
        return { kind: 'conflict', message: body.message || fallbackMessage }
      }
      if (typeof body.message === 'string' && body.message) {
        return { kind: 'error', message: body.message }
      }
    }
    return { kind: 'error', message: messageFromUnknown(err, fallbackMessage) }
  }

  if (err instanceof ApiRequestError) {
    if (isConflictCode(err.code) || err.status === 409) {
      return { kind: 'conflict', message: err.message || fallbackMessage }
    }
    return { kind: 'error', message: err.message || fallbackMessage }
  }

  return { kind: 'error', message: messageFromUnknown(err, fallbackMessage) }
}

/** Toolbar label key fragment derived from save status. */
export function builderSaveStatusLabelKey(
  status: BuilderSaveStatus,
): 'builder.saving' | 'builder.saved' | 'builder.saveFailed' | 'builder.revisionConflict' | null {
  switch (status) {
    case 'saving':
      return 'builder.saving'
    case 'saved':
      return 'builder.saved'
    case 'error':
      return 'builder.saveFailed'
    case 'conflict':
      return 'builder.revisionConflict'
    default:
      return null
  }
}
