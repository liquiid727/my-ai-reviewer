export interface DimensionScore {
  name: string
  score: number
  reason: string
  evidence: string
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

export interface InterviewSuggestions {
  worth_asking: string[]
  suspicious: string[]
  verify_direction: string[]
  skip: string[]
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
