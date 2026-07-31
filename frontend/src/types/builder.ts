export type TemplateId = 'classic' | 'modern' | 'compact'
export type LayoutDensity = 'loose' | 'normal' | 'tight' | 'compact'

export interface DesignTokens {
  font_family: string
  density: LayoutDensity
  accent_color: string
  page_margin: string
}

export interface DraftItem {
  heading?: string | null
  subheading?: string | null
  date_range?: string | null
  bullets: string[]
}

export interface DraftSection {
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
  auto_one_page: boolean
  status: string
  identity: DraftIdentity
  summary: string | null
  sections: DraftSection[]
  design_tokens: DesignTokens
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

export interface ScoreResult {
  overall_score: number
  dimension_scores: ScoreDimension[]
  summary?: string | null
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
  auto_one_page?: boolean
}

export interface ExportPayload {
  template_id?: TemplateId
  auto_one_page?: boolean
  persist?: boolean
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
