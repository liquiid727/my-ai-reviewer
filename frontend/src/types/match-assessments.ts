import type { APIResponse } from './resume'

/** Public match-assessment DTOs (RIP-014 §6.1, §9). These mirror the API
 * projection exactly; report components only ever receive these DTOs, never
 * adapter output or raw snapshots. */

export type MatchAssessmentStatus = 'queued' | 'evaluating' | 'completed' | 'failed'

export interface MatchAssessment {
  id: string
  job_target_id: string
  jd_version_id: string
  resume_version_id: string
  status: MatchAssessmentStatus
  policy_version: string
  run_id: string
  attempt: number
  reused: boolean
  error_code: string | null
  error_details: string | null
  retryable: boolean
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
  result: MatchAssessmentResult | null
  report?: MatchReport
}

export interface MatchAssessmentResult {
  policy_version: string
  schema_version: string
  total_score: number | null
  score_before_caps: number | null
  overall_confidence: number | null
  recommendation: string | null
  caps_applied: unknown[]
  dimension_scores: unknown[]
  rule_results: unknown[]
  gaps: unknown[]
  evidence_summary: Record<string, unknown>
  model_name: string | null
  model_version: string | null
  prompt_version: string | null
}

export interface MatchReport {
  version_facts: {
    policy_version: string
    schema_version: string
    jd_version_id: string
    resume_version_id: string
    jd_version_no: number | null
    resume_version_source_type: string | null
  }
  scores: {
    total_score: number | null
    score_before_caps: number | null
    caps_applied: unknown[]
    overall_confidence: number | null
    recommendation: string | null
  }
  dimensions: MatchDimension[]
  gap_classes: {
    counts_by_class: Record<string, number>
    counts_by_severity: Record<string, number>
    counts_by_action_type: Record<string, number>
  }
  evidence_sufficiency: {
    jd_evidence: number
    resume_evidence: number
    cited_ids: string[]
    unknown_citations: string[]
  }
  explicit_unknowns: Array<{ kind: string; evidence_id: string }>
  stale: {
    jd: string[]
    resume: string[]
    is_stale: boolean
  }
  actions: MatchAction[]
  model: {
    name: string | null
    version: string | null
    prompt_version: string | null
  }
  completed_at: string | null
}

export interface MatchDimension {
  key: string
  raw_score: number
  weighted_score: number
  weight: number
  confidence: number
  status: 'strong' | 'good' | 'weak' | 'unknown' | string
  cited_jd_evidence: string[]
  cited_resume_evidence: string[]
  explanation: string | null
  [key: string]: unknown
}

export interface MatchAction {
  id: 'resume_optimization' | 'plan' | 'interview' | string
  label: string
  eligible: boolean
  route: string
  method: 'navigate' | 'POST' | string
  destination: Record<string, string>
}

export interface MatchAssessmentCreateData {
  id: string
  job_target_id: string
  jd_version_id: string
  resume_version_id: string
  status: MatchAssessmentStatus
  policy_version: string
  run_id: string
  attempt: number
  reused: boolean
  created: boolean
  error_code: string | null
  error_details: string | null
  retryable: boolean
}

export interface MatchAssessmentListData {
  assessments: MatchAssessment[]
  next_before_created_at: string | null
  next_before_id: string | null
}

export interface MatchAssessmentResponse extends APIResponse {
  data: MatchAssessment
}

export interface MatchAssessmentCreateResponse extends APIResponse {
  data: MatchAssessmentCreateData
}

export interface MatchAssessmentListResponse extends APIResponse {
  data: MatchAssessmentListData
}
