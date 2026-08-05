import type { APIResponse } from './resume'

export type ScenarioKey =
  | 'comprehensive'
  | 'hr_screen'
  | 'technical_first'
  | 'project_deep_dive'
  | 'system_design'
  | 'behavioral'
  | 'manager_round'

export type ScenarioStageKey =
  | 'introduction'
  | 'background'
  | 'motivation'
  | 'core_skills'
  | 'problem_solving'
  | 'project'
  | 'project_context'
  | 'project_decisions'
  | 'tradeoffs'
  | 'outcomes'
  | 'system_design'
  | 'clarification'
  | 'architecture'
  | 'data'
  | 'scaling'
  | 'reliability'
  | 'behavior'
  | 'ownership'
  | 'collaboration'
  | 'conflict'
  | 'learning'
  | 'prioritization'
  | 'leadership'
  | 'cross_functional'
  | 'growth'
  | 'candidate_questions'

export type ScenarioCoverageCategory =
  | 'core_skills'
  | 'problem_solving'
  | 'project_evidence'
  | 'system_design'
  | 'behavioral'
  | 'motivation'
  | 'culture_fit'
  | 'leadership'
  | 'ownership'
  | 'technical'
  | 'communication'
  | 'candidate_questions'

export type ScenarioDifficulty = 'basic' | 'standard' | 'challenge'
export type ScenarioLanguage = 'zh-CN' | 'en'

export interface ScenarioStageWeight {
  stage: ScenarioStageKey
  weight: number
  coverage_categories: ScenarioCoverageCategory[]
  allows_candidate_questions: boolean
}

export interface ScenarioDurationBudget {
  duration: 15 | 30 | 45 | 60
  main_questions: number
  total_followups: number
  max_followup_depth: number
  skip_allowance: number
}

export interface ScenarioScoring {
  dimensions: string[]
  prompt_policy_version: string
}

export interface ScenarioSummary {
  key: ScenarioKey
  version: number
  name_key: string
  description_key: string
  stage_keys: ScenarioStageKey[]
  main_emphasis: string
}

export interface ScenarioDetail {
  key: ScenarioKey
  version: number
  name_key: string
  description_key: string
  mode: 'text'
  stages: ScenarioStageWeight[]
  durations: ScenarioDurationBudget[]
  allowed_coverage_categories: ScenarioCoverageCategory[]
  allowed_difficulties: ScenarioDifficulty[]
  allowed_languages: ScenarioLanguage[]
  candidate_questions_min: number
  candidate_questions_max: number
  scoring: ScenarioScoring
}

export interface ScenarioListData {
  scenarios: ScenarioSummary[]
  allowed_global_options: {
    durations: number[]
    difficulties: ScenarioDifficulty[]
    languages: ScenarioLanguage[]
    max_followup_depth: number
  }
}

export interface ScenarioListResponse extends APIResponse {
  data: ScenarioListData
}

export interface ScenarioDetailResponse extends APIResponse {
  data: ScenarioDetail
}
