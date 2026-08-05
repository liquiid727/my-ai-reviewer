import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UploadPage } from '@/pages/UploadPage'
import { useResumeStore } from '@/stores/resumeStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { RESUME_POLL_MAX_MS } from '@/lib/polling'
import { act, fireEvent, renderWithProviders, screen } from '@/test/utils'

const resumeApi = vi.hoisted(() => ({
  uploadResume: vi.fn(),
  getResumeStatus: vi.fn(),
  getPrivacyReview: vi.fn(),
  addPrivacyMasks: vi.fn(),
  approvePrivacy: vi.fn(),
  retryResume: vi.fn(),
}))

vi.mock('@/api/resume', () => resumeApi)

describe('UploadPage LLM configuration prompt', () => {
  beforeEach(() => {
    vi.useRealTimers()
    Object.values(resumeApi).forEach((mock) => mock.mockReset())
    useResumeStore.getState().reset()
    useSettingsStore.setState({
      configs: [],
      llmReady: false,
      loading: false,
      loaded: false,
      refresh: vi.fn().mockResolvedValue(undefined),
    })
  })

  it('hides the configuration prompt when an effective LLM config is available', () => {
    useSettingsStore.setState({ loaded: true, llmReady: true })

    renderWithProviders(<UploadPage />)

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows the configuration prompt when no effective LLM config is available', () => {
    useSettingsStore.setState({ loaded: true, llmReady: false })

    renderWithProviders(<UploadPage />)

    expect(screen.getByRole('alert')).toHaveTextContent('AI Model Not Configured')
  })

  it('shows recovery actions when resume polling exceeds its ownership timeout', async () => {
    vi.useFakeTimers()
    useSettingsStore.setState({ loaded: true, llmReady: true })
    resumeApi.uploadResume.mockResolvedValue({
      code: 0,
      message: 'success',
      data: { resume_id: 'resume-timeout', status: 'uploaded' },
    })
    resumeApi.getResumeStatus.mockResolvedValue({
      code: 0,
      message: 'success',
      data: {
        status: 'text_masked',
        current_step: 'llm_parse',
        completed_steps: ['text_extract', 'privacy_scan'],
        error: null,
      },
    })

    try {
      renderWithProviders(<UploadPage />)
      const fileInput = document.querySelector('input[type="file"]')
      expect(fileInput).not.toBeNull()

      await act(async () => {
        fireEvent.change(fileInput as HTMLInputElement, {
          target: { files: [new File(['masked'], 'resume.txt', { type: 'text/plain' })] },
        })
        await Promise.resolve()
        await Promise.resolve()
      })

      await act(async () => {
        vi.setSystemTime(new Date(Date.now() + RESUME_POLL_MAX_MS + 1))
        await vi.advanceTimersByTimeAsync(5_000)
      })

      expect(screen.getByTestId('upload-timeout')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Check again' })).toBeInTheDocument()
      expect(screen.getByRole('button', { name: 'Retry task' })).toBeInTheDocument()

      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: 'Check again' }))
        await Promise.resolve()
        await Promise.resolve()
      })
      expect(screen.queryByTestId('upload-timeout')).not.toBeInTheDocument()
    } finally {
      vi.useRealTimers()
    }
  })
})
