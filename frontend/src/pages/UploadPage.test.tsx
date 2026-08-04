import { beforeEach, describe, expect, it, vi } from 'vitest'
import { UploadPage } from '@/pages/UploadPage'
import { useResumeStore } from '@/stores/resumeStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { renderWithProviders, screen } from '@/test/utils'

describe('UploadPage LLM configuration prompt', () => {
  beforeEach(() => {
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
})
