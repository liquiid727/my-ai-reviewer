export type TemplateId = 'classic' | 'modern' | 'compact'
export type LayoutDensity = 'loose' | 'normal' | 'tight' | 'compact'
export type LayoutMode = 'auto_pages' | 'target_pages'

export interface LayoutPolicy {
  mode: LayoutMode
  target_page_count: number | null
}

export interface DesignTokens {
  font_family: string
  density: LayoutDensity
  accent_color: string
  page_margin: string
  /** 用户自定义 CSS（注入模板末尾，可覆盖默认样式） */
  custom_css: string
}

export interface DraftItem {
  item_id: string
  heading?: string | null
  subheading?: string | null
  date_range?: string | null
  bullets: string[]
}

export interface DraftSection {
  section_id: string
  section_type: string
  title: string
  items: DraftItem[]
  visible: boolean
  order: number
}

export interface DraftIdentity {
  name?: string
  email?: string
  phone?: string
  location?: string
  links?: string[]
  /** 证件照对象名（服务端受控，仅由 confirm/delete 写入） */
  photo?: string | null
  [key: string]: unknown
}

export interface ResumeDraftData {
  draft_id: string
  resume_id: string | null
  title: string
  template_id: TemplateId
  layout_policy: LayoutPolicy
  status: string
  revision: number
  identity: DraftIdentity
  summary: string | null
  sections: DraftSection[]
  design_tokens: DesignTokens
  privacy_placeholders: PrivacyPlaceholder[]
}

export interface PrivacyPlaceholder {
  token: string
  entity_type: string
  occurrence_count: number
  context?: string
}

export interface PolishResult {
  original_items: string[]
  polished_items: string[]
  notes: string | null
}

export interface ScoreDimension {
  name: string
  score: number
  reason?: string
  evidence?: string
}

export interface ScoreStrength {
  point: string
  evidence?: string
}

export interface ScoreRisk {
  point: string
  evidence?: string
  severity?: 'high' | 'medium' | 'low' | string
}

/** 面向候选人的可执行改进建议，支持一键采纳并由 AI 修改 */
export interface ScoreImprovement {
  point: string
  detail?: string
}

export interface ScoreInterviewSuggestions {
  worth_asking?: string[]
  suspicious?: string[]
  verify_direction?: string[]
  skip?: string[]
}

export interface ScoreResult {
  overall_score: number
  dimension_scores: ScoreDimension[]
  strengths?: ScoreStrength[]
  risks?: ScoreRisk[]
  improvements?: ScoreImprovement[]
  interview_suggestions?: ScoreInterviewSuggestions
  summary?: string | null
  /** 持久化评分的元信息（仅后端保存过的评分携带） */
  scored_at?: string | null
  scored_revision?: number | null
}

export interface TemplateOptions {
  templates: { id: TemplateId }[]
  densities: { id: LayoutDensity }[]
}

/** 内置参考简历模板（可一键创建可编辑草稿） */
export interface ReferenceTemplateItem {
  key: string
  name: string
  description: string
  tags: string[]
}

/** 草稿列表项（简历列表页展示用的概要） */
export interface DraftListItem {
  draft_id: string
  resume_id: string | null
  title: string
  template_id: TemplateId
  status: string
  sort_order: number
  overall_score?: number | null
  scored_at?: string | null
  created_at: string
  updated_at: string
}

export interface UpdateDraftPayload {
  title?: string
  identity?: DraftIdentity
  summary?: string | null
  sections?: DraftSection[]
  template_id?: TemplateId
  design_tokens?: DesignTokens
  layout_policy?: LayoutPolicy
  base_revision?: number
}

export interface ExportPayload {
  template_id?: TemplateId
  layout_policy?: LayoutPolicy
  persist?: boolean
  replacements?: Record<string, string>
  photo_data_uri?: string | null
}

export type PhotoBgColor = 'white' | 'blue' | 'red'

export interface PhotoUploadResult {
  original_object: string
  processed_object: string
  original_url: string
  processed_url: string
  background_replaced: boolean
  degraded_reason: string | null
  bg_color: PhotoBgColor
}

export type AssistantEditKind =
  | 'replace_summary'
  | 'replace_identity_field'
  | 'replace_item_field'
  | 'replace_bullet'
  | 'add_bullet'
  | 'remove_bullet'

export interface AssistantEditOperation {
  operation_id: string
  kind: AssistantEditKind
  section_id: string | null
  item_id: string | null
  bullet_index: number | null
  field: string | null
  before: string | null
  after: string | null
  reason: string
}

export type AssistantProposalStatus = 'proposed' | 'applied' | 'rejected' | 'undone'

export interface AssistantMessage {
  message_id: string
  sequence: number
  role: 'user' | 'assistant'
  content: string
  created_at: string | null
}

export interface AssistantProposal {
  proposal_id: string
  base_revision: number
  assistant_message: string
  operations: AssistantEditOperation[]
  selected_operation_ids: string[]
  status: AssistantProposalStatus
  model: string | null
  usage: Record<string, unknown>
  applied_revision: number | null
  created_at: string | null
}

export interface AssistantConversation {
  conversation_id: string
  status: string
  messages: AssistantMessage[]
  proposals: AssistantProposal[]
}
