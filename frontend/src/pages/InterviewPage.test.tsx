import { StrictMode } from 'react'
import { describe, expect, it, vi } from 'vitest'
import { MemoryRouter, Route, Routes } from 'react-router'
import { I18nextProvider } from 'react-i18next'
import { render, waitFor } from '@testing-library/react'

import { InterviewPage } from '@/pages/InterviewPage'
import i18n from '@/i18n/config'

const interviewApi = vi.hoisted(() => ({
  startInterview: vi.fn(),
  submitAnswer: vi.fn(),
}))

vi.mock('@/api/interview', () => interviewApi)

describe('InterviewPage startup', () => {
  it('reuses the startup request when StrictMode re-runs the effect', async () => {
    interviewApi.startInterview.mockResolvedValue({
      code: 0,
      message: 'success',
      data: {
        question_id: 'question-1',
        question_text: 'Describe a recent project.',
        stage: 'project',
        difficulty: 'medium',
        current_num: 1,
        total_count: 5,
        is_followup: false,
        followup_round: 0,
      },
    })

    render(
      <StrictMode>
        <I18nextProvider i18n={i18n}>
          <MemoryRouter initialEntries={['/interview/interview-1']}>
            <Routes>
              <Route path="/interview/:id" element={<InterviewPage />} />
            </Routes>
          </MemoryRouter>
        </I18nextProvider>
      </StrictMode>,
    )

    await waitFor(() => expect(interviewApi.startInterview).toHaveBeenCalledTimes(1))
  })
})
