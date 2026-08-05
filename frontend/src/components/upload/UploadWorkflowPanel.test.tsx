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
        status="llm_parsing"
        currentStep="llm_parse"
        completedSteps={['text_extract', 'privacy_scan']}
        error={null}
        privacyReview={null}
      />,
    )
    expect(screen.getByTestId('upload-processing')).toBeInTheDocument()
    // 状态徽章展示本地化阶段文案，而不是后端原始状态值
    expect(screen.getByTestId('upload-status-badge')).toHaveTextContent('AI parsing')
    // 当前阶段提示为具体进展描述，并带加载动画
    expect(screen.getByTestId('upload-current-step')).toHaveTextContent(
      'AI is structuring your resume content',
    )
    expect(screen.getByTestId('upload-current-step-spinner')).toBeInTheDocument()
    // 整体进度按 5 个流水线阶段折算（2/5 = 40%）
    expect(screen.getByText('40%')).toBeInTheDocument()
    // 分阶段清单：已完成步骤展示翻译后的名称，进行中步骤标记 aria-current
    expect(screen.getByTestId('upload-step-text_extract')).toHaveTextContent('Extract text')
    expect(screen.getByTestId('upload-step-privacy_scan')).toHaveTextContent('Privacy scan')
    expect(screen.getByTestId('upload-step-llm_parse')).toHaveAttribute('aria-current', 'step')
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

  it('replaces the spinner with recovery actions after polling times out', async () => {
    const user = userEvent.setup()
    const onRecheck = vi.fn()
    const onRetry = vi.fn()

    renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="llm_parsing"
        currentStep="llm_parse"
        completedSteps={['text_extract', 'privacy_scan']}
        error={null}
        privacyReview={null}
        pollTimedOut
        onRecheck={onRecheck}
        onRetry={onRetry}
      />,
    )

    expect(screen.getByTestId('upload-timeout')).toBeInTheDocument()
    expect(screen.queryByTestId('upload-current-step-spinner')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Check again' }))
    await user.click(screen.getByRole('button', { name: 'Retry task' }))
    expect(onRecheck).toHaveBeenCalledOnce()
    expect(onRetry).toHaveBeenCalledOnce()
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

  it('renders the safe failure code, stage, and processing run id', () => {
    renderWithProviders(
      <UploadWorkflowPanel
        resumeId={SYNTHETIC_RESUME_ID}
        status="failed"
        currentStep="failed"
        completedSteps={['text_extract', 'privacy_scan']}
        error="SoftTimeLimitExceeded"
        runId="run-00000000-0000-4000-8000-000000000002"
        diagnostic={{
          error_code: 'RESUME_PROCESSING_TIMEOUT',
          step: 'llm_parse',
          attempt: 3,
          retryable: true,
        }}
        privacyReview={null}
      />,
    )

    expect(screen.getByTestId('upload-failed')).toHaveTextContent(
      'Processing timed out after its retries. Please retry.',
    )
    expect(screen.getByTestId('upload-failed')).toHaveTextContent('Failed at: AI parsing')
    expect(screen.getByTestId('upload-run-id')).toHaveTextContent(
      'run-00000000-0000-4000-8000-000000000002',
    )
    expect(screen.getByRole('button', { name: 'Copy ID' })).toBeInTheDocument()
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
