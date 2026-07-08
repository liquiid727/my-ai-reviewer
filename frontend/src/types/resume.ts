export interface ResumeStatusData {
  status: string
  current_step: string
  completed_steps: string[]
  error: string | null
}

export interface ResumeUploadData {
  resume_id: string
  file_id: string
  status: string
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
  raw_text: string | null
  parsed_result: ParsedResult | null
  created_at: string
  updated_at: string
}
