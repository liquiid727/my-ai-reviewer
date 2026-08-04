import type { APIResponse } from './resume'

export type JDSourceType = 'text' | 'file' | 'url'
export type JDStatus = 'processing' | 'duplicate_pending' | 'ready' | 'failed'
export type JDSeniority = 'junior' | 'mid' | 'senior' | 'expert'

export interface JDSkill {
  name: string
  critical?: boolean
  evidence?: string | null
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
  responsibilities: string[]
  required_skills: JDSkill[]
  preferred_skills: JDSkill[]
  extraction_source: string | null
  duplicate_of_id: string | null
  field_sources: Record<string, string>
  parser_version: string | null
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

export type JDResponse<T> = APIResponse<T>
