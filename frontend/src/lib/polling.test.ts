import { describe, expect, it } from 'vitest'
import {
  PLAN_POLL_MAX_MS,
  RESUME_POLL_FAST_MS,
  RESUME_POLL_MAX_MS,
  RESUME_POLL_SLOW_AFTER_MS,
  RESUME_POLL_SLOW_MS,
  isPlanGeneratingStatus,
  isPollTimedOut,
  isResumeTerminalStatus,
  nextPollIntervalMs,
  shouldContinuePolling,
} from '@/lib/polling'

describe('polling ownership helpers', () => {
  it('marks resume terminal statuses that must stop the loop', () => {
    expect(isResumeTerminalStatus('evaluated')).toBe(true)
    expect(isResumeTerminalStatus('failed')).toBe(true)
    expect(isResumeTerminalStatus('privacy_review_required')).toBe(true)
    expect(isResumeTerminalStatus('text_masked')).toBe(false)
    expect(isResumeTerminalStatus(null)).toBe(false)
  })

  it('identifies plan generating statuses that own the poll loop', () => {
    expect(isPlanGeneratingStatus('generating')).toBe(true)
    expect(isPlanGeneratingStatus('regenerating')).toBe(true)
    expect(isPlanGeneratingStatus('active')).toBe(false)
    expect(isPlanGeneratingStatus('failed')).toBe(false)
  })

  it('detects ownership timeout after the configured max duration', () => {
    expect(isPollTimedOut(RESUME_POLL_MAX_MS, RESUME_POLL_MAX_MS)).toBe(false)
    expect(isPollTimedOut(RESUME_POLL_MAX_MS + 1, RESUME_POLL_MAX_MS)).toBe(true)
    expect(isPollTimedOut(PLAN_POLL_MAX_MS + 1, PLAN_POLL_MAX_MS)).toBe(true)
  })

  it('slows the poll interval after the fast window elapses', () => {
    expect(
      nextPollIntervalMs(0, RESUME_POLL_SLOW_AFTER_MS, RESUME_POLL_FAST_MS, RESUME_POLL_SLOW_MS),
    ).toBe(RESUME_POLL_FAST_MS)
    expect(
      nextPollIntervalMs(
        RESUME_POLL_SLOW_AFTER_MS,
        RESUME_POLL_SLOW_AFTER_MS,
        RESUME_POLL_FAST_MS,
        RESUME_POLL_SLOW_MS,
      ),
    ).toBe(RESUME_POLL_SLOW_MS)
  })

  it('continues only while mounted, in-progress, owned, visible, and under timeout', () => {
    expect(
      shouldContinuePolling({
        mounted: true,
        timedOut: false,
        terminal: false,
        ownershipLost: false,
        visible: true,
      }),
    ).toBe(true)
  })

  it('stops on unmount cleanup ownership loss', () => {
    expect(
      shouldContinuePolling({
        mounted: false,
        timedOut: false,
        terminal: false,
      }),
    ).toBe(false)
  })

  it('stops on terminal success/failure without scheduling another tick', () => {
    expect(
      shouldContinuePolling({
        mounted: true,
        timedOut: false,
        terminal: true,
      }),
    ).toBe(false)
  })

  it('stops on timeout so ownership does not leak forever', () => {
    expect(
      shouldContinuePolling({
        mounted: true,
        timedOut: true,
        terminal: false,
      }),
    ).toBe(false)
  })

  it('stops when revision ownership is lost', () => {
    expect(
      shouldContinuePolling({
        mounted: true,
        timedOut: false,
        terminal: false,
        ownershipLost: true,
      }),
    ).toBe(false)
  })

  it('pauses while the tab is hidden without treating it as terminal', () => {
    expect(
      shouldContinuePolling({
        mounted: true,
        timedOut: false,
        terminal: false,
        visible: false,
      }),
    ).toBe(false)
  })
})
