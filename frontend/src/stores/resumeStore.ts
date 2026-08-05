import { create } from 'zustand'
import type { ResumeFailureDiagnostic, ResumeStatus } from '@/types/resume'

interface ResumeState {
  resumeId: string | null
  runId: string | null
  status: ResumeStatus | null
  currentStep: string | null
  completedSteps: string[]
  error: string | null
  diagnostic: ResumeFailureDiagnostic | null
  isPolling: boolean
  setResumeId: (id: string) => void
  setStatus: (
    status: ResumeStatus,
    currentStep: string,
    completedSteps: string[],
    error: string | null,
    runId?: string | null,
    diagnostic?: ResumeFailureDiagnostic | null,
  ) => void
  setPolling: (polling: boolean) => void
  reset: () => void
}

export const useResumeStore = create<ResumeState>((set) => ({
  resumeId: null,
  runId: null,
  status: null,
  currentStep: null,
  completedSteps: [],
  error: null,
  diagnostic: null,
  isPolling: false,
  setResumeId: (id) => set({ resumeId: id }),
  setStatus: (status, currentStep, completedSteps, error, runId = null, diagnostic = null) =>
    set({ status, currentStep, completedSteps, error, runId, diagnostic }),
  setPolling: (polling) => set({ isPolling: polling }),
  reset: () =>
    set({
      resumeId: null,
      runId: null,
      status: null,
      currentStep: null,
      completedSteps: [],
      error: null,
      diagnostic: null,
      isPolling: false,
    }),
}))
