import { apiRequest } from './client'
import type {
  APIResponse,
  PrivacyReviewData,
  ResumeDetailData,
  ResumeStatusData,
  ResumeUploadData,
} from '@/types/resume'

// Upload/retry endpoints may wait for the bounded broker handoff (60s) before
// returning a durable dispatch failure, so their client budget is explicit.
export const RESUME_COMMAND_TIMEOUT_MS = 75_000

export async function uploadResume(
  file: File,
  signal?: AbortSignal,
): Promise<APIResponse<ResumeUploadData>> {
  const formData = new FormData()
  formData.append('file', file)

  return apiRequest('/resume/upload', {
    method: 'POST',
    body: formData,
    signal,
    timeoutMs: RESUME_COMMAND_TIMEOUT_MS,
  })
}

export async function getResumeStatus(
  resumeId: string,
  signal?: AbortSignal,
): Promise<APIResponse<ResumeStatusData>> {
  return apiRequest(`/resume/${resumeId}/status`, { signal })
}

/** 已解析出 profile 的简历选项（供发起面试时选择目标简历）。 */
export interface ResumeOption {
  id: string
  display_name: string
  updated_at: string | null
}

export async function listResumeOptions(): Promise<
  APIResponse<{ items: ResumeOption[]; page: number; page_size: number; total: number }>
> {
  return apiRequest('/resume?has_profile=true&page_size=100')
}

export async function retryResume(
  resumeId: string,
  signal?: AbortSignal,
): Promise<APIResponse<ResumeStatusData>> {
  return apiRequest(`/resume/${resumeId}/retry`, {
    method: 'POST',
    signal,
    timeoutMs: RESUME_COMMAND_TIMEOUT_MS,
  })
}

export async function getResumeDetail(resumeId: string): Promise<APIResponse<ResumeDetailData>> {
  return apiRequest(`/resume/${resumeId}`)
}

export async function getPrivacyReview(
  resumeId: string,
  signal?: AbortSignal,
): Promise<APIResponse<PrivacyReviewData>> {
  return apiRequest(`/resume/${resumeId}/privacy`, { signal })
}

export async function addPrivacyMasks(
  resumeId: string,
  baseRevision: number,
  spans: Array<{ start: number; end: number; entity_type: string }>,
  signal?: AbortSignal,
): Promise<APIResponse<PrivacyReviewData>> {
  return apiRequest(`/resume/${resumeId}/privacy/masks`, {
    method: 'POST',
    body: JSON.stringify({ base_revision: baseRevision, spans }),
    signal,
    timeoutMs: RESUME_COMMAND_TIMEOUT_MS,
  })
}

export async function approvePrivacy(
  resumeId: string,
  baseRevision: number,
  signal?: AbortSignal,
): Promise<APIResponse<{ resume_id: string; status: string; run_id?: string | null }>> {
  return apiRequest(`/resume/${resumeId}/privacy/approve`, {
    method: 'POST',
    body: JSON.stringify({ base_revision: baseRevision }),
    signal,
    timeoutMs: RESUME_COMMAND_TIMEOUT_MS,
  })
}
