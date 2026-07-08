import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type { LLMConfig, LLMTestResult } from '@/types/settings'

export async function listLLMConfigs(): Promise<APIResponse<LLMConfig[]>> {
  return apiRequest('/settings/llm')
}

export async function createLLMConfig(data: {
  provider: string
  api_key: string
  model_name: string
  base_url?: string | null
}): Promise<APIResponse<LLMConfig>> {
  return apiRequest('/settings/llm', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}

export async function updateLLMConfig(
  id: string,
  data: {
    provider?: string
    api_key?: string
    model_name?: string
    base_url?: string | null
  },
): Promise<APIResponse<LLMConfig>> {
  return apiRequest(`/settings/llm/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  })
}

export async function deleteLLMConfig(
  id: string,
): Promise<APIResponse<null>> {
  return apiRequest(`/settings/llm/${id}`, {
    method: 'DELETE',
  })
}

export async function testLLMConnection(data: {
  provider: string
  api_key: string
  model_name: string
  base_url?: string | null
}): Promise<APIResponse<LLMTestResult>> {
  return apiRequest('/settings/llm/test', {
    method: 'POST',
    body: JSON.stringify(data),
  })
}
