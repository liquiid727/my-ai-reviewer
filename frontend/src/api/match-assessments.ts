import { apiRequest } from './client'
import type {
  MatchAssessmentCreateData,
  MatchAssessmentCreateResponse,
  MatchAssessmentListResponse,
  MatchAssessmentResponse,
} from '@/types/match-assessments'

function query(params: Record<string, string | number | boolean | undefined | null>) {
  const values = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') values.set(key, String(value))
  })
  const encoded = values.toString()
  return encoded ? `?${encoded}` : ''
}

export function createMatchAssessment(input: {
  job_target_id?: string
  jd_version_id?: string
  resume_version_id?: string
  policy_version?: string
  force?: boolean
}) {
  return apiRequest<MatchAssessmentCreateResponse>('/match-assessments', {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function retryMatchAssessment(assessmentId: string) {
  return apiRequest<MatchAssessmentCreateResponse>(`/match-assessments/${assessmentId}/retry`, {
    method: 'POST',
  })
}

export function getMatchAssessment(assessmentId: string) {
  return apiRequest<MatchAssessmentResponse>(`/match-assessments/${assessmentId}`)
}

export function listTargetMatchAssessments(
  targetId: string,
  params: {
    status?: string
    limit?: number
    before_created_at?: string | null
    before_id?: string | null
  } = {},
) {
  return apiRequest<MatchAssessmentListResponse>(
    `/job-targets/${targetId}/match-assessments${query({
      status: params.status,
      limit: params.limit ?? 20,
      before_created_at: params.before_created_at,
      before_id: params.before_id,
    })}`,
  )
}

export function asMatchAssessmentCreateData(
  input: Partial<MatchAssessmentCreateData>,
): MatchAssessmentCreateData {
  return input as MatchAssessmentCreateData
}
