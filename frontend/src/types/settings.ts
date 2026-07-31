export interface LLMConfig {
  id: string
  provider: string
  api_key: string // masked
  model_name: string
  base_url: string | null
  is_active: boolean
  verified: boolean
  last_verified_at: string | null
  created_at: string
  updated_at: string
}

export interface LLMTestResult {
  success: boolean
  models?: string[]
  error?: string
}
