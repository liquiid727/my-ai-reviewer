import { create } from 'zustand'

interface ResumeState {
  resumeId: string | null
  status: string | null
  currentStep: string | null
  completedSteps: string[]
  error: string | null
  isPolling: boolean
  setResumeId: (id: string) => void
  setStatus: (status: string, currentStep: string, completedSteps: string[], error: string | null) => void
  setPolling: (polling: boolean) => void
  reset: () => void
}

export const useResumeStore = create<ResumeState>((set) => ({
  resumeId: null,
  status: null,
  currentStep: null,
  completedSteps: [],
  error: null,
  isPolling: false,
  setResumeId: (id) => set({ resumeId: id }),
  setStatus: (status, currentStep, completedSteps, error) =>
    set({ status, currentStep, completedSteps, error }),
  setPolling: (polling) => set({ isPolling: polling }),
  reset: () =>
    set({
      resumeId: null,
      status: null,
      currentStep: null,
      completedSteps: [],
      error: null,
      isPolling: false,
    }),
}))
