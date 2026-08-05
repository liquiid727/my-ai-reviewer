import type { APIResponse } from './resume'

export interface JobTargetSummary {
  id: string
  job_description_id: string
  default_jd_version_id: string | null
  default_resume_version_id: string | null
  revision: number
  created_at: string | null
  updated_at: string | null
  archived_at: string | null
}

export interface JobTargetDetail extends JobTargetSummary {
  created: boolean
  job?: { title: string | null; company: string | null } | null
  current_jd_version?: { id: string; version_no: number; published_at: string | null } | null
  default_resume_version?: { id: string; source_type: string; published_at: string | null } | null
}

export interface JobTargetListData {
  targets: JobTargetSummary[]
}

export interface JobTargetResponse extends APIResponse {
  data: JobTargetDetail
}

export interface JobTargetListResponse extends APIResponse {
  data: JobTargetListData
}

export interface ResumeVersionSummary {
  id: string
  source_type: string
  source_revision: number
  content_hash: string
  schema_version: string
  published_at: string | null
}

export interface JdVersionSummary {
  id: string
  version_no: number
  content_hash: string
  schema_version: string
  parser_version: string
  publication_reason: string
  published_at: string | null
}
