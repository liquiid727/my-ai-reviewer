import { apiRequest } from './client'
import type {
  JobTargetListResponse,
  JobTargetResponse,
  JdVersionSummary,
  ResumeVersionSummary,
} from '@/types/job-targets'

export function ensureJobTarget(payload: {
  jd_id: string
  default_jd_version_id?: string | null
  default_resume_version_id?: string | null
}) {
  return apiRequest<JobTargetResponse>('/job-targets', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export function listJobTargets(includeArchived = false) {
  const q = includeArchived ? '?include_archived=true' : ''
  return apiRequest<JobTargetListResponse>(`/job-targets${q}`)
}

export function getJobTarget(targetId: string) {
  return apiRequest<JobTargetResponse>(`/job-targets/${targetId}`)
}

export function updateJobTargetDefaults(
  targetId: string,
  payload: {
    expected_revision: number
    default_jd_version_id?: string | null
    default_resume_version_id?: string | null
  },
) {
  return apiRequest<JobTargetResponse>(`/job-targets/${targetId}`, {
    method: 'PATCH',
    body: JSON.stringify(payload),
  })
}

export function archiveJobTarget(targetId: string, expectedRevision: number) {
  return apiRequest<JobTargetResponse>(`/job-targets/${targetId}/archive`, {
    method: 'POST',
    body: JSON.stringify({ expected_revision: expectedRevision }),
  })
}

export function listResumeVersions(params: { resume_id?: string; draft_id?: string } = {}) {
  const q = new URLSearchParams()
  if (params.resume_id) q.set('resume_id', params.resume_id)
  if (params.draft_id) q.set('draft_id', params.draft_id)
  const qs = q.toString()
  return apiRequest<{ code: number; data: { versions: ResumeVersionSummary[] } }>(
    `/resume-versions${qs ? `?${qs}` : ''}`,
  )
}

export function listJdVersions(jdId: string) {
  return apiRequest<{ code: number; data: { versions: JdVersionSummary[] } }>(
    `/jd/${jdId}/versions`,
  )
}
