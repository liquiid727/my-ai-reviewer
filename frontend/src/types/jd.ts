import type { APIResponse } from './resume'

export type JDSourceType = 'text' | 'file' | 'url' | 'image' | 'manual'
export type JDStatus = 'processing' | 'duplicate_pending' | 'needs_review' | 'ready' | 'failed' | 'archived'
export type JDSeniority = 'junior' | 'mid' | 'senior' | 'expert'
export type JDProvenance = 'source' | 'llm' | 'manual'
export type JDMatchLifecycle = 'queued' | 'running' | 'ready' | 'failed' | 'stale'
export type JDMatchMode = 'rules_v1' | 'hybrid_v2'

export interface JDSkill {
  name: string
  critical?: boolean
  evidence?: string | null
}

export interface JDVersionSummary {
  id: string
  version_no: number
  content_hash: string
  schema_version: string
  parser_version: string | null
  publication_reason: string
  published_at: string | null
}

export interface JDVersionDetail extends JDVersionSummary {
  normalized_text: string
  structured: Record<string, unknown>
  evidence: Record<string, unknown>
  source_metadata: Record<string, unknown>
}

export interface JDReviewDraft {
  title?: string | null
  company?: string | null
  department?: string | null
  location?: string | null
  employment_type?: 'full_time' | 'part_time' | 'contract' | 'internship' | null
  seniority?: JDSeniority | null
  compensation?: { min_amount?: number | null; max_amount?: number | null; currency?: string | null; period?: 'yearly' | 'monthly' | 'hourly' | null } | null
  minimum_years?: number | null
  preferred_years?: number | null
  education?: string | null
  languages?: string[]
  certificates?: string[]
  location_constraint?: string | null
  responsibilities?: JDReviewItem[]
  required_skills?: JDReviewItem[]
  preferred_skills?: JDReviewItem[]
  hard_conditions?: JDReviewHardCondition[]
  domain_context?: string | null
  industry_context?: string | null
  interview_clues?: string[]
  notes?: string | null
  parser_version?: string | null
  model_name?: string | null
  prompt_version?: string | null
  schema_version?: string
  overall_confidence?: number
}

export interface JDReviewItem {
  key: string
  value: string
  evidence?: string | null
  evidence_status?: 'available' | 'unavailable'
  confidence?: number
  provenance?: JDProvenance
}

export interface JDReviewHardCondition extends JDReviewItem {
  category: 'years' | 'education' | 'language' | 'certificate' | 'location' | 'other'
}

export interface JDManualInput {
  title: string
  company?: string | null
  location?: string | null
  department?: string | null
  employment_type?: 'full_time' | 'part_time' | 'contract' | 'internship' | null
  responsibilities?: string[]
  required_skills?: JDSkill[]
  preferred_skills?: JDSkill[]
  notes?: string | null
  allow_duplicate?: boolean
}

export interface JDSourceAsset {
  id: string
  order: number
  media_type: string
  status: string
  width?: number
  height?: number
}

export interface JDVisionMetadata {
  provider?: string | null
  model?: string | null
  transcriber_version?: string | null
  warnings?: string[]
}

export interface JDListItem {
  id: string
  title: string | null
  company: string | null
  location: string | null
  source_type: JDSourceType
  status: JDStatus
  processing_step: string
  processing_error: string | null
  seniority: JDSeniority | null
  updated_at: string | null
  created_at: string | null
}

export interface JDDetail extends JDListItem {
  raw_text: string
  source_url: string | null
  source_file_id: string | null
  source_assets?: JDSourceAsset[]
  source_asset_count?: number | null
  vision?: JDVisionMetadata | null
  processing_run_id?: string | null
  responsibilities: string[]
  required_skills: JDSkill[]
  preferred_skills: JDSkill[]
  extraction_source: string | null
  duplicate_of_id: string | null
  field_sources: Record<string, string>
  parser_version: string | null
  review_revision: number
  review_draft: JDReviewDraft | null
  review_error: string | null
  current_version_id: string | null
  structured_revision?: number | null
  hard_requirements?: unknown[]
}

export interface JDVersionsData {
  versions: JDVersionSummary[]
}

export interface JDListData {
  items: JDListItem[]
  page: number
  page_size: number
  total: number
}

export interface JDPatchInput {
  expected_updated_at: string
  title?: string | null
  company?: string | null
  location?: string | null
  seniority?: JDSeniority | null
  responsibilities?: string[]
  required_skills?: JDSkill[]
  preferred_skills?: JDSkill[]
}

export interface JDMatchDimension {
  dimension: string
  weight: number
  score: number | null
  status: 'supported' | 'partial' | 'conflict' | 'unknown'
  reason: string
  jd_evidence_ids: string[]
  candidate_evidence_ids: string[]
  confidence: number
}

export interface JDHardFilter {
  requirement_id: string
  type: string
  status: 'pass' | 'fail' | 'unknown'
  reason: string
  jd_evidence_ids: string[]
  candidate_evidence_ids: string[]
  human_confirmation_required?: boolean
}

export interface JDMatchEvidence {
  id: string
  source: string
  kind: string
  label: string
  excerpt: string
  page?: number | null
  confidence?: number | null
}

export interface JDMatchResult {
  id: string
  resume_id: string
  jd_id: string
  status: JDMatchLifecycle
  mode: JDMatchMode
  match_score: number | null
  recommendation: string
  human_confirmation_required?: boolean | null
  hard_filters: JDHardFilter[]
  dimension_scores: JDMatchDimension[]
  evidence: JDMatchEvidence[]
  coverage: number | null
  confidence: number | null
  risk?: unknown[]
  gap?: unknown[]
  detail: string | null
  matcher_version: string | null
  hard_filter_policy_version?: string | null
  prompt_version: string | null
  schema_version: string | null
  model?: { provider?: string | null; name?: string | null } | null
  input_fingerprint: string | null
  stale: boolean
  stale_reasons: string[]
  failure_code?: string | null
  created_at: string
  updated_at?: string | null
}

export interface JDMatchListData {
  items: JDMatchResult[]
  page: number
  page_size: number
  total: number
}

export type JDResponse<T> = APIResponse<T>
