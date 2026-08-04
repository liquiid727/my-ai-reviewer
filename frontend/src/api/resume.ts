import { apiRequest } from './client'
import type {
  APIResponse,
  PrivacyReviewData,
  ResumeDetailData,
  ResumeStatusData,
  ResumeUploadData,
} from '@/types/resume'

export async function uploadResume(file: File): Promise<APIResponse<ResumeUploadData>> {
  const formData = new FormData()
  formData.append('file', file)

  const res = await fetch('/api/v1/resume/upload', {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) {
    let message = `Upload failed (${res.status})`
    try {
      const err = await res.json()
      message = err.message || message
    } catch {
      // Response body is not JSON (e.g., HTML error from proxy)
    }
    throw new Error(message)
  }
  return res.json()
}

export async function getResumeStatus(resumeId: string): Promise<APIResponse<ResumeStatusData>> {
  return apiRequest(`/resume/${resumeId}/status`)
}

export async function retryResume(resumeId: string): Promise<APIResponse<ResumeStatusData>> {
  return apiRequest(`/resume/${resumeId}/retry`, { method: 'POST' })
}

export async function getResumeDetail(resumeId: string): Promise<APIResponse<ResumeDetailData>> {
  return apiRequest(`/resume/${resumeId}`)
}

export async function getPrivacyReview(resumeId: string): Promise<APIResponse<PrivacyReviewData>> {
  return apiRequest(`/resume/${resumeId}/privacy`)
}

export async function addPrivacyMasks(
  resumeId: string,
  baseRevision: number,
  spans: Array<{ start: number; end: number; entity_type: string }>,
): Promise<APIResponse<PrivacyReviewData>> {
  return apiRequest(`/resume/${resumeId}/privacy/masks`, {
    method: 'POST',
    body: JSON.stringify({ base_revision: baseRevision, spans }),
  })
}

export async function approvePrivacy(
  resumeId: string,
  baseRevision: number,
): Promise<APIResponse<{ resume_id: string; status: string }>> {
  return apiRequest(`/resume/${resumeId}/privacy/approve`, {
    method: 'POST',
    body: JSON.stringify({ base_revision: baseRevision }),
  })
}
