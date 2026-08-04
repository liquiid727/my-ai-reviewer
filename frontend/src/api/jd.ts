import { apiRequest } from './client'
import type { JDDetail, JDListData, JDPatchInput, JDResponse, JDSourceType, JDStatus } from '@/types/jd'

function query(params: Record<string, string | number | boolean | undefined>) {
  const values = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') values.set(key, String(value))
  })
  const encoded = values.toString()
  return encoded ? `?${encoded}` : ''
}

export function listJobDescriptions(params: {
  page?: number
  pageSize?: number
  q?: string
  sourceType?: JDSourceType | ''
  status?: JDStatus | ''
} = {}): Promise<JDResponse<JDListData>> {
  return apiRequest(`/jd${query({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    q: params.q,
    source_type: params.sourceType,
    status: params.status,
  })}`)
}

export function getJobDescription(id: string): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}`)
}

export function importJDText(input: {
  raw_text: string
  title?: string
  company?: string
  allow_duplicate?: boolean
}): Promise<JDResponse<JDDetail>> {
  return apiRequest('/jd/import/text', { method: 'POST', body: JSON.stringify(input) })
}

export function importJDUrl(input: {
  url: string
  allow_duplicate?: boolean
}): Promise<JDResponse<JDDetail>> {
  return apiRequest('/jd/import/url', { method: 'POST', body: JSON.stringify(input) })
}

export function importJDFile(file: File, allowDuplicate = false): Promise<JDResponse<JDDetail>> {
  const form = new FormData()
  form.append('file', file)
  return apiRequest(`/jd/import/file${query({ allow_duplicate: allowDuplicate })}`, {
    method: 'POST',
    body: form,
  })
}

export function patchJobDescription(id: string, input: JDPatchInput): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}`, { method: 'PATCH', body: JSON.stringify(input) })
}

export function retryJobDescription(id: string): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}/retry`, { method: 'POST' })
}

export function reextractJobDescription(id: string, overwriteManual = false): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}/reextract`, {
    method: 'POST',
    body: JSON.stringify({ overwrite_manual: overwriteManual }),
  })
}

export function confirmJDDuplicate(id: string): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}/duplicate/confirm`, { method: 'POST' })
}

export function cancelJDDuplicate(id: string): Promise<JDResponse<unknown>> {
  return apiRequest(`/jd/${id}/duplicate/cancel`, { method: 'POST' })
}

export function deleteJobDescription(id: string): Promise<JDResponse<unknown>> {
  return apiRequest(`/jd/${id}`, { method: 'DELETE' })
}

export function matchJobDescription(id: string, resumeId: string): Promise<JDResponse<{ id: string }>> {
  return apiRequest('/jd/match', {
    method: 'POST',
    body: JSON.stringify({ jd_id: id, resume_id: resumeId }),
  })
}
