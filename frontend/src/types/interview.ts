export interface QuestionPresentData {
  question_id: string
  question_text: string
  stage: string
  difficulty: string
  current_num: number
  total_count: number
  is_followup: boolean
  followup_round: number
}

export interface AnswerResultData {
  score: number
  feedback: string
  key_points_hit: string[]
  key_points_missed: string[]
  next: QuestionPresentData | null
  is_finished: boolean
}

export interface InterviewCreatedData {
  interview_id: string
  status: string
}

export interface InterviewStatusData {
  interview_id: string
  status: string
  current_question_num: number | null
  total_questions: number | null
  answered_count: number
}

export interface DimensionScore {
  name: string
  score: number
  reason: string
}

export interface QuestionSummary {
  question_num: number
  question_text: string
  final_score: number
  summary: string
}

export interface StrengthWeakness {
  point: string
  evidence: string
}

export interface InterviewReportData {
  interview_id: string
  overall_score: number
  dimension_scores: DimensionScore[]
  per_question_summary: QuestionSummary[]
  strengths: StrengthWeakness[]
  weaknesses: StrengthWeakness[]
  recommendation: string
  summary: string | null
  llm_model: string | null
  created_at: string
}

export interface InterviewListItem {
  interview_id: string
  resume_id: string
  status: string
  question_count: number
  overall_score: number | null
  recommendation: string | null
  created_at: string
}

export type InterviewStatus =
  | 'pending'
  | 'generating'
  | 'in_progress'
  | 'report_generating'
  | 'completed'
  | 'failed'

export interface ChatMessage {
  id: string
  type: 'question' | 'answer' | 'evaluation' | 'followup' | 'system'
  content: string
  data?: QuestionPresentData | AnswerResultData
  timestamp: number
}
