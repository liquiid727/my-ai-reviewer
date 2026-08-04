import React from 'react'
import { describe, expect, it, vi } from 'vitest'
import userEvent from '@testing-library/user-event'
import { UploadWorkflowPanel } from '@/components/upload/UploadWorkflowPanel'
import { renderWithProviders, screen } from '@/test/utils'
import type { PrivacyReviewData } from '@/types/resume'

const SYNTHETIC_RESUME_ID = 'resume-00000000-0000-4000-8000-000000000001'

const privacyReview: PrivacyReviewData = {
  resume_id: SYNTHETIC_RESUME_ID,
  status: 'privacy_review_required',
  revision: 1,
  masked_text: 'Candidate [[PERSON_01]] worked at [[ORG_01]].',
  placeholders: [
    { token: '[[PERSON_01]]', entity_type: 'person', occurrence_count: 1 },
    { token: '[[ORG_01]]', entity_type: 'organization', occurrence_count: 1 },
  ],
  risk_flags: [],
  quarantine_expires_at: null,
}

describe('UploadWorkflowPanel states', () => {
  it('renders nothing for empty upload state', () => {
    const { container } = renderWithProviders(
      <UploadWorkflowPanel
        resumeId={null}
        status={null}
        currentStep={null}
        completedSteps={[]}
        error={null}
        privacyReview={null}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('renders processing/loading progress for in-flight pipeline status', () => {
    renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="text_masked"
        currentStep="llm_parse"
        completedSteps={['text_extract', 'privacy_scan']}
        error={null}
        privacyReview={null}
      />,
    )
    expect(screen.getByTestId('upload-processing')).toBeInTheDocument()
    expect(screen.getByTestId('upload-status-badge')).toHaveTextContent('text_masked')
    expect(screen.getByTestId('upload-current-step')).toHaveTextContent('Parsing with AI')
    expect(screen.getByText('text_extract')).toBeInTheDocument()
    expect(screen.getByText('privacy_scan')).toBeInTheDocument()
  })

  it('renders privacy review with synthetic masked placeholders only', () => {
    renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="privacy_review_required"
        currentStep="privacy_scan"
        completedSteps={['text_extract']}
        error={null}
        privacyReview={privacyReview}
      />,
    )
    expect(screen.getByTestId('upload-privacy-review')).toBeInTheDocument()
    expect(screen.getByText('Privacy review')).toBeInTheDocument()
    expect(screen.getByTestId('upload-privacy-masked-text')).toHaveValue(
      'Candidate [[PERSON_01]] worked at [[ORG_01]].',
    )
    expect(screen.queryByText(/@|1\d{10}/)).not.toBeInTheDocument()
  })

  it('renders failure state with retry and reset actions', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    const onReset = vi.fn()
    renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="failed"
        currentStep="evaluate"
        completedSteps={['text_extract']}
        error="synthetic pipeline failure"
        privacyReview={null}
        onRetry={onRetry}
        onReset={onReset}
      />,
    )
    expect(screen.getByTestId('upload-failed')).toBeInTheDocument()
    expect(screen.getByText('Processing Failed')).toBeInTheDocument()
    expect(screen.getByText('synthetic pipeline failure')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Retry' }))
    await user.click(screen.getByRole('button', { name: 'Upload Another' }))
    expect(onRetry).toHaveBeenCalledTimes(1)
    expect(onReset).toHaveBeenCalledTimes(1)
  })

  it('hides the panel after successful evaluation', () => {
    const { container } = renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="evaluated"
        currentStep="done"
        completedSteps={['text_extract', 'llm_parse', 'classify', 'evaluate']}
        error={null}
        privacyReview={null}
      />,
    )
    expect(container).toBeEmptyDOMElement()
  })
})
