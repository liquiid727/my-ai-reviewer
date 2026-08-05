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

export interface CreateInterviewParams {
  /** 已评估简历发起（与 draftId 二选一） */
  resumeId?: string
  /** 简历草稿发起：以草稿当前内容作为出题依据 */
  draftId?: string
  jdText?: string
  questionCount?: number
}

export async function createInterview(
  params: CreateInterviewParams,
): Promise<APIResponse<InterviewCreatedData>> {
  return apiRequest('/interview/create', {
    method: 'POST',
    body: JSON.stringify({
      resume_id: params.resumeId ?? null,
      draft_id: params.draftId ?? null,
      jd_text: params.jdText || null,
      question_count: params.questionCount ?? 5,
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
