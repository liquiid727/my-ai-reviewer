import type { APIResponse } from './resume'

export type PlanStatus = 'generating' | 'regenerating' | 'active' | 'completed' | 'failed'
export type PlanTaskCategory =
  | 'gap_priority'
  | 'resume'
  | 'skill'
  | 'evidence_project'
  | 'interview'
  | 'application_review'
export type PlanTaskPriority = 'high' | 'medium' | 'low'
export type PlanTaskStatus = 'todo' | 'in_progress' | 'done'

export interface PlanProgress {
  done: number
  total: number
  percent: number
}

export interface PlanTask {
  id: string
  plan_id: string
  title: string
  category: PlanTaskCategory
  description: string
  basis: Array<{ id?: string; label?: string; excerpt?: string }>
  source: 'ai' | 'manual'
  priority: PlanTaskPriority
  status: PlanTaskStatus
  due_date: string | null
  sort_order: number
  updated_at: string | null
}

export interface PlanSummary {
  id: string
  title: string
  status: PlanStatus
  revision: number
  jd: { title: string | null; company: string | null }
  resume: { display_name: string }
  progress: PlanProgress
  next_due_task: string | null
  updated_at: string | null
}

export interface PlanListData {
  items: PlanSummary[]
  page: number
  page_size: number
  total: number
}

export interface PlanMatchContext {
  id: string
  mode: string
  input_fingerprint: string | null
  fresh: boolean
  stale_reasons: string[]
  matcher_version?: string | null
  hard_filter_policy_version?: string | null
  prompt_version?: string | null
  schema_version?: string | null
  provider?: string | null
  model?: string | null
}

export interface PlanDetail extends Omit<PlanSummary, 'next_due_task'> {
  target_date: string | null
  weekly_hours: number | null
  supplemental_background: string | null
  generation_error: string | null
  generated_at: string | null
  is_generation_stale: boolean
  match: PlanMatchContext | null
  jd: { id: string; title: string | null; company: string | null }
  resume: { id: string; display_name: string }
  tasks: PlanTask[]
}

export interface EligibleResume {
  id: string
  display_name: string
  updated_at?: string | null
}

export interface EligibleResumeListData {
  items: EligibleResume[]
  page: number
  page_size: number
  total: number
}

export interface PlanMutationData {
  revision: number
  progress: PlanProgress
  task?: PlanTask
}

export type PlanResponse<T> = APIResponse<T>
