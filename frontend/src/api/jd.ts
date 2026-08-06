import { apiRequest } from './client'
import type {
  JDDetail,
  JDListData,
  JDMatchListData,
  JDMatchResult,
  JDManualInput,
  JDPatchInput,
  JDResponse,
  JDReviewDraft,
  JDSourceType,
  JDStatus,
  JDVersionDetail,
  JDVersionsData,
} from '@/types/jd'

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

export function importJDImage(file: File, allowDuplicate = false): Promise<JDResponse<JDDetail>> {
  const form = new FormData()
  form.append('file', file)
  return apiRequest(`/jd/import/image${query({ allow_duplicate: allowDuplicate })}`, {
    method: 'POST',
    body: form,
  })
}

export function importJDManual(input: JDManualInput): Promise<JDResponse<JDDetail>> {
  return apiRequest('/jd/import/manual', { method: 'POST', body: JSON.stringify(input) })
}

export function importJDImages(input: {
  images: File[]
  title?: string
  company?: string
  allowDuplicate?: boolean
  acknowledgeExternalVision: boolean
}): Promise<JDResponse<JDDetail>> {
  const form = new FormData()
  input.images.forEach((image) => form.append('images', image))
  if (input.title) form.append('title', input.title)
  if (input.company) form.append('company', input.company)
  form.append('allow_duplicate', String(Boolean(input.allowDuplicate)))
  form.append('acknowledge_external_vision', String(input.acknowledgeExternalVision))
  return apiRequest('/jd/import/images', { method: 'POST', body: form })
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

export function saveJDReviewDraft(
  id: string,
  input: { expected_review_revision: number; draft: JDReviewDraft },
): Promise<JDResponse<JDDetail>> {
  return apiRequest(`/jd/${id}/review`, { method: 'PATCH', body: JSON.stringify(input) })
}

export function publishJDVersion(
  id: string,
  input: { expected_review_revision: number; publication_reason?: string },
): Promise<JDResponse<{ id: string; version_no: number; content_hash: string; schema_version: string; publication_reason: string; published_at: string | null }>> {
  return apiRequest(`/jd/${id}/publish`, { method: 'POST', body: JSON.stringify(input) })
}

export function reparseJobDescription(
  id: string,
  overwriteManual = false,
): Promise<JDResponse<{ run_id: string; status: string }>> {
  return apiRequest(`/jd/${id}/reparse`, {
    method: 'POST',
    body: JSON.stringify({ overwrite_manual: overwriteManual }),
  })
}

export function abandonJDDraft(id: string): Promise<JDResponse<unknown>> {
  return apiRequest(`/jd/${id}/draft/abandon`, { method: 'POST' })
}

export function archiveJobDescription(id: string): Promise<JDResponse<unknown>> {
  return apiRequest(`/jd/${id}/archive`, { method: 'POST' })
}

export function listJDVersions(id: string, limit = 50): Promise<JDResponse<JDVersionsData>> {
  return apiRequest(`/jd/${id}/versions${query({ limit })}`)
}

export function getJDVersion(id: string, versionId: string): Promise<JDResponse<JDVersionDetail>> {
  return apiRequest(`/jd/${id}/versions/${versionId}`)
}

export function matchJobDescription(id: string, resumeId: string): Promise<JDResponse<{ id: string }>> {
  return apiRequest('/jd/match', {
    method: 'POST',
    body: JSON.stringify({ jd_id: id, resume_id: resumeId }),
  })
}

export function createJDMatch(input: { jdId: string; resumeId: string; force?: boolean }): Promise<JDResponse<{
  id: string
  status: string
  mode: string
  input_fingerprint: string | null
  reused: boolean
}>> {
  return apiRequest('/jd/matches', {
    method: 'POST',
    body: JSON.stringify({ jd_id: input.jdId, resume_id: input.resumeId, force: Boolean(input.force) }),
  })
}

export function getJDMatch(id: string): Promise<JDResponse<JDMatchResult>> {
  return apiRequest(`/jd/matches/${id}`)
}

export function listJDMatches(params: {
  jdId: string
  resumeId?: string
  status?: string
  mode?: string
  page?: number
  pageSize?: number
}): Promise<JDResponse<JDMatchListData>> {
  return apiRequest(`/jd/${params.jdId}/matches${query({
    resume_id: params.resumeId,
    status: params.status,
    mode: params.mode,
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  })}`)
}

export function recomputeJDMatch(id: string): Promise<JDResponse<{
  id: string
  status: string
  mode: string
  input_fingerprint: string | null
  reused: boolean
}>> {
  return apiRequest(`/jd/matches/${id}/recompute`, { method: 'POST' })
}
