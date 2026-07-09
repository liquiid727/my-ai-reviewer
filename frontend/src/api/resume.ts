import { apiRequest } from './client'
import type { APIResponse, ResumeDetailData, ResumeStatusData, ResumeUploadData } from '@/types/resume'

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
