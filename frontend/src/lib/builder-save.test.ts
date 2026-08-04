import { describe, expect, it } from 'vitest'
import { ApiRequestError } from '@/api/client'
import { AssistantApiError } from '@/api/builder'
import {
  builderSaveStatusLabelKey,
  mapBuilderSaveError,
  mapBuilderSaveResponse,
} from '@/lib/builder-save'

const FALLBACK = 'Failed to save'

describe('mapBuilderSaveResponse', () => {
  it('maps a successful envelope to a revision', () => {
    expect(
      mapBuilderSaveResponse(
        { code: 0, message: 'ok', data: { revision: 4 } },
        FALLBACK,
      ),
    ).toEqual({ kind: 'success', revision: 4 })
  })

  it('maps revision conflict code 1007', () => {
    expect(
      mapBuilderSaveResponse(
        { code: 1007, message: 'revision conflict' },
        FALLBACK,
      ),
    ).toEqual({ kind: 'conflict', message: 'revision conflict' })
  })

  it('maps generic non-zero envelopes to error', () => {
    expect(
      mapBuilderSaveResponse({ code: 5001, message: 'llm down' }, FALLBACK),
    ).toEqual({ kind: 'error', message: 'llm down' })
  })

  it('falls back when success payload lacks revision', () => {
    expect(mapBuilderSaveResponse({ code: 0, message: 'ok', data: {} }, FALLBACK)).toEqual({
      kind: 'error',
      message: FALLBACK,
    })
  })
})

describe('mapBuilderSaveError', () => {
  it('maps ApiRequestError conflict codes', () => {
    const err = new ApiRequestError('stale revision', 409, 1007)
    expect(mapBuilderSaveError(err, FALLBACK)).toEqual({
      kind: 'conflict',
      message: 'stale revision',
    })
  })

  it('maps AssistantApiError HTTP 409 as conflict', () => {
    const err = new AssistantApiError(409, { message: 'draft revised elsewhere' })
    expect(mapBuilderSaveError(err, FALLBACK)).toEqual({
      kind: 'conflict',
      message: 'Assistant API error (409)',
    })
  })

  it('maps AssistantApiError body code 1007 as conflict', () => {
    const err = new AssistantApiError(400, { code: 1007, message: 'base_revision mismatch' })
    expect(mapBuilderSaveError(err, FALLBACK)).toEqual({
      kind: 'conflict',
      message: 'base_revision mismatch',
    })
  })

  it('maps generic errors to error outcome', () => {
    expect(mapBuilderSaveError(new Error('network down'), FALLBACK)).toEqual({
      kind: 'error',
      message: 'network down',
    })
  })
})

describe('builderSaveStatusLabelKey', () => {
  it('returns i18n keys for toolbar states', () => {
    expect(builderSaveStatusLabelKey('saving')).toBe('builder.saving')
    expect(builderSaveStatusLabelKey('saved')).toBe('builder.saved')
    expect(builderSaveStatusLabelKey('error')).toBe('builder.saveFailed')
    expect(builderSaveStatusLabelKey('conflict')).toBe('builder.revisionConflict')
    expect(builderSaveStatusLabelKey('idle')).toBeNull()
  })
})
