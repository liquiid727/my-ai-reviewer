import { apiRequest } from './client'
import type {
  ScenarioDetailResponse,
  ScenarioListResponse,
  ScenarioKey,
} from '@/types/interview-scenarios'

export function listInterviewScenarios() {
  return apiRequest<ScenarioListResponse>('/interview-scenarios')
}

export function getInterviewScenario(key: ScenarioKey, version?: number) {
  const query = version !== undefined ? `?version=${version}` : ''
  return apiRequest<ScenarioDetailResponse>(`/interview-scenarios/${key}${query}`)
}
