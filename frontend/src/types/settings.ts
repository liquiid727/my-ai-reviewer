export interface LLMCapabilities {
  supports_text: boolean
  supports_structured_output: boolean
  supports_vision: boolean
  max_images: number | null
  max_image_bytes: number | null
  transport: string
  verified_at?: string | null
}

export interface LLMConfig {
  id: string
  provider: string
  api_key: string // masked
  model_name: string
  base_url: string | null
  is_active: boolean
  verified: boolean
  last_verified_at: string | null
  capabilities: LLMCapabilities
  capabilities_verified_at: string | null
  created_at: string
  updated_at: string
}

export interface LLMTestResult {
  success: boolean
  models?: string[]
  capabilities?: LLMCapabilities
  error?: string
  /** models.list 不可用时回退 chat 验证的提示 */
  warning?: string
}
