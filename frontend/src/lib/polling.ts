/** Shared polling ownership helpers for resume upload and plan generation. */

import type { ResumeStatus } from '@/types/resume'

export const RESUME_POLL_MAX_MS = 10 * 60 * 1000
export const RESUME_POLL_FAST_MS = 2000
export const RESUME_POLL_SLOW_MS = 5000
export const RESUME_POLL_SLOW_AFTER_MS = 3 * 60 * 1000

export const PLAN_POLL_FAST_MS = 2000
export const PLAN_POLL_SLOW_MS = 5000
export const PLAN_POLL_SLOW_AFTER_MS = 60_000
/** Soft ownership timeout so a stuck generating plan does not poll forever. */
export const PLAN_POLL_MAX_MS = 15 * 60 * 1000

/** Resume pipeline statuses that end the client poll loop. */
export function isResumeTerminalStatus(status: ResumeStatus | null | undefined): boolean {
  return (
    status === 'evaluated' ||
    status === 'failed' ||
    status === 'privacy_review_required'
  )
}

/** Plan statuses that require background polling. */
export function isPlanGeneratingStatus(status: string | null | undefined): boolean {
  return status === 'generating' || status === 'regenerating'
}

export function isPollTimedOut(elapsedMs: number, maxMs: number): boolean {
  return elapsedMs > maxMs
}

export function nextPollIntervalMs(
  elapsedMs: number,
  slowAfterMs: number,
  fastMs: number,
  slowMs: number,
): number {
  return elapsedMs >= slowAfterMs ? slowMs : fastMs
}

export type PollContinueInput = {
  /** Component still mounted / effect not cleaned up. */
  mounted: boolean
  /** Elapsed time already exceeded the ownership timeout. */
  timedOut: boolean
  /** Server reached a terminal status for this poll loop. */
  terminal: boolean
  /** Revision ownership lost or epoch invalidated — stop scheduled work. */
  ownershipLost?: boolean
  /** Tab hidden; callers may pause without losing ownership. */
  visible?: boolean
}

/**
 * Single decision point for whether a poll tick should schedule another request.
 * Cleanup (unmount), terminal status, timeout, and lost ownership all stop polling.
 */
export function shouldContinuePolling(input: PollContinueInput): boolean {
  if (!input.mounted) return false
  if (input.timedOut) return false
  if (input.terminal) return false
  if (input.ownershipLost) return false
  if (input.visible === false) return false
  return true
}
