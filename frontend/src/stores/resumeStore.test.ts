import { beforeEach, describe, expect, it } from 'vitest'
import { useResumeStore } from '@/stores/resumeStore'

describe('resumeStore polling ownership flags', () => {
  beforeEach(() => {
    useResumeStore.getState().reset()
  })

  it('starts empty without an active poll', () => {
    const state = useResumeStore.getState()
    expect(state.resumeId).toBeNull()
    expect(state.status).toBeNull()
    expect(state.isPolling).toBe(false)
  })

  it('tracks synthetic resume id and processing status while polling', () => {
    const id = 'resume-00000000-0000-4000-8000-000000000001'
    useResumeStore.getState().setResumeId(id)
    useResumeStore.getState().setStatus('text_masked', 'llm_parse', ['text_extract'], null)
    useResumeStore.getState().setPolling(true)

    const state = useResumeStore.getState()
    expect(state.resumeId).toBe(id)
    expect(state.status).toBe('text_masked')
    expect(state.currentStep).toBe('llm_parse')
    expect(state.completedSteps).toEqual(['text_extract'])
    expect(state.isPolling).toBe(true)
  })

  it('records failure terminal state and clears poll ownership on stop', () => {
    useResumeStore.getState().setResumeId('resume-00000000-0000-4000-8000-000000000002')
    useResumeStore.getState().setPolling(true)
    useResumeStore.getState().setStatus('failed', 'evaluate', ['text_extract'], 'synthetic failure')
    useResumeStore.getState().setPolling(false)

    const state = useResumeStore.getState()
    expect(state.status).toBe('failed')
    expect(state.error).toBe('synthetic failure')
    expect(state.isPolling).toBe(false)
  })

  it('reset clears poll ownership and residual error', () => {
    useResumeStore.getState().setResumeId('resume-00000000-0000-4000-8000-000000000003')
    useResumeStore.getState().setStatus('failed', 'evaluate', [], 'err')
    useResumeStore.getState().setPolling(true)
    useResumeStore.getState().reset()

    const state = useResumeStore.getState()
    expect(state.resumeId).toBeNull()
    expect(state.status).toBeNull()
    expect(state.error).toBeNull()
    expect(state.isPolling).toBe(false)
    expect(state.completedSteps).toEqual([])
  })
})
