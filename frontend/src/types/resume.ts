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
