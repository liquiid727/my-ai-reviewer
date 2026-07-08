import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type { EvaluationData } from '@/types/evaluation'

export async function getEvaluation(resumeId: string): Promise<APIResponse<EvaluationData>> {
  return apiRequest(`/resume/${resumeId}/evaluation`)
}
