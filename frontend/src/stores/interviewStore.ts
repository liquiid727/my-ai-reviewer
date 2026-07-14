import { create } from 'zustand'
import type { ChatMessage, QuestionPresentData } from '@/types/interview'

interface InterviewState {
  interviewId: string | null
  status: string | null
  currentQuestion: QuestionPresentData | null
  messages: ChatMessage[]
  isSubmitting: boolean
  isFinished: boolean

  setInterviewId: (id: string) => void
  setStatus: (status: string) => void
  setCurrentQuestion: (question: QuestionPresentData | null) => void
  addMessage: (message: ChatMessage) => void
  setSubmitting: (submitting: boolean) => void
  setFinished: (finished: boolean) => void
  reset: () => void
}

export const useInterviewStore = create<InterviewState>((set) => ({
  interviewId: null,
  status: null,
  currentQuestion: null,
  messages: [],
  isSubmitting: false,
  isFinished: false,

  setInterviewId: (id) => set({ interviewId: id }),
  setStatus: (status) => set({ status }),
  setCurrentQuestion: (question) => set({ currentQuestion: question }),
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),
  setSubmitting: (submitting) => set({ isSubmitting: submitting }),
  setFinished: (finished) => set({ isFinished: finished }),
  reset: () =>
    set({
      interviewId: null,
      status: null,
      currentQuestion: null,
      messages: [],
      isSubmitting: false,
      isFinished: false,
    }),
}))
