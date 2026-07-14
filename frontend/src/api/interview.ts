import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type {
  InterviewCreatedData,
  QuestionPresentData,
  AnswerResultData,
  InterviewStatusData,
  InterviewReportData,
  InterviewListItem,
} from '@/types/interview'

export async function createInterview(
  resumeId: string,
  jdText?: string,
  questionCount?: number,
): Promise<APIResponse<InterviewCreatedData>> {
  return apiRequest('/interview/create', {
    method: 'POST',
    body: JSON.stringify({
      resume_id: resumeId,
      jd_text: jdText || null,
      question_count: questionCount ?? 5,
    }),
  })
}

export async function startInterview(
  interviewId: string,
): Promise<APIResponse<QuestionPresentData>> {
  return apiRequest(`/interview/${interviewId}/start`, {
    method: 'POST',
  })
}

export async function submitAnswer(
  interviewId: string,
  questionId: string,
  answerText: string,
): Promise<APIResponse<AnswerResultData>> {
  return apiRequest(`/interview/${interviewId}/answer`, {
    method: 'POST',
    body: JSON.stringify({
      question_id: questionId,
      answer_text: answerText,
    }),
  })
}

export async function getInterviewStatus(
  interviewId: string,
): Promise<APIResponse<InterviewStatusData>> {
  return apiRequest(`/interview/${interviewId}/status`)
}

export async function getInterviewReport(
  interviewId: string,
): Promise<APIResponse<InterviewReportData>> {
  return apiRequest(`/interview/${interviewId}/report`)
}

export async function listInterviews(
  resumeId?: string,
): Promise<APIResponse<InterviewListItem[]>> {
  const query = resumeId ? `?resume_id=${resumeId}` : ''
  return apiRequest(`/interview/list${query}`)
}
