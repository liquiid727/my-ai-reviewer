export type ResumeStatus =
  | 'uploaded'
  | 'privacy_scanning'
  | 'privacy_review_required'
  | 'text_masked'
  | 'llm_parsing'
  | 'fact_extracted'
  | 'classified'
  | 'evaluating'
  | 'evaluated'
  | 'failed'

export interface ResumeStatusData {
  status: ResumeStatus
  current_step: string
  completed_steps: string[]
  error: string | null
  run_id: string | null
  error_code?: string | null
  retryable?: boolean
  last_progress_at?: string | null
  deadline_at?: string | null
  diagnostic?: ResumeFailureDiagnostic | null
}

export interface ResumeUploadData {
  resume_id: string
  status: ResumeStatus
  run_id: string | null
  error_code?: string | null
}

export interface ResumeFailureDiagnostic {
  error_code: string
  step: string | null
  attempt: number | null
  retryable: boolean
}

export interface PrivacyPlaceholder {
  token: string
  entity_type: string
  occurrence_count: number
  context?: string
}

export interface PrivacyReviewData {
  resume_id: string
  status: string
  revision: number
  masked_text: string | null
  placeholders: PrivacyPlaceholder[]
  risk_flags: string[]
  quarantine_expires_at: string | null
}

export interface APIResponse<T = unknown> {
  code: number
  message: string
  data: T
}

export interface Evidence {
  source_text: string
  page?: number
  confidence?: number
}

export interface Education {
  school: string
  degree?: string
  major?: string
  start_date?: string
  end_date?: string
  gpa?: string
  evidence?: Evidence[]
}

export interface WorkExperience {
  company: string
  title?: string
  start_date?: string
  end_date?: string
  description?: string
  achievements?: string[]
  evidence?: Evidence[]
}

export interface ProjectExperience {
  name: string
  role?: string
  tech_stack?: string[]
  description?: string
  highlights?: string[]
  evidence?: Evidence[]
}

export interface Skill {
  name: string
  level?: string
  category?: string
  evidence?: Evidence[]
}

export interface Certificate {
  name: string
  issuer?: string
  date?: string
  evidence?: Evidence[]
}

export interface CandidateProfile {
  name?: string
  email?: string
  phone?: string
  location?: string
  links?: string[]
  ability_tags?: string[]
  educations?: Education[]
  work_experiences?: WorkExperience[]
  project_experiences?: ProjectExperience[]
  skills?: Skill[]
  certificates?: Certificate[]
}

export interface ParsedResult {
  profile?: CandidateProfile
  classification?: {
    tech_direction_tags: string[]
    experience_level: string
    industry_tags: string[]
    stats: Record<string, number>
    classifier_version: string
  }
}

export interface ResumeDetailData {
  resume_id: string
  status: string
  masked_text: string | null
  parsed_result: ParsedResult | null
  created_at: string
  updated_at: string
}
