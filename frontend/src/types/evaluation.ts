export interface DimensionScore {
  dimension: string
  score: number
  reason: string
  evidence: string[]
}

export interface StrengthItem {
  point: string
  evidence: string
}

export interface RiskItem {
  point: string
  evidence: string
  severity: 'high' | 'medium' | 'low'
}

export interface InterviewSuggestion {
  question?: string
  claim?: string
  direction?: string
  topic?: string
  reason?: string
  evidence?: string
  method?: string
}

export interface InterviewSuggestions {
  worth_asking: InterviewSuggestion[]
  likely_exaggerated: InterviewSuggestion[]
  verify_directions: InterviewSuggestion[]
  skip_topics: InterviewSuggestion[]
}

export interface EvaluationData {
  evaluation_id: string
  resume_id: string
  overall_score: number
  dimension_scores: DimensionScore[]
  strengths: StrengthItem[]
  risks: RiskItem[]
  interview_suggestions: InterviewSuggestions
  summary: string | null
  llm_model: string | null
  created_at: string
}
