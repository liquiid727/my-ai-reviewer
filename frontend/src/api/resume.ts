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
    const err = await res.json()
    throw new Error(err.message || 'Upload failed')
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
