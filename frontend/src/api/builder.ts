import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type {
  AssistantConversation,
  DraftListItem,
  ExportPayload,
  PhotoBgColor,
  PhotoUploadResult,
  PolishResult,
  ReferenceTemplateItem,
  ResumeDraftData,
  ScoreResult,
  TemplateOptions,
  UpdateDraftPayload,
} from '@/types/builder'

const BASE = '/api/v1/builder'

export async function getTemplateOptions(): Promise<APIResponse<TemplateOptions>> {
  return apiRequest('/builder/templates')
}

export async function listReferenceTemplates(): Promise<APIResponse<ReferenceTemplateItem[]>> {
  return apiRequest('/builder/reference-templates')
}

export async function listDrafts(): Promise<APIResponse<DraftListItem[]>> {
  return apiRequest('/builder/drafts')
}

export async function reorderDrafts(draftIds: string[]): Promise<APIResponse<DraftListItem[]>> {
  return apiRequest('/builder/drafts/order', {
    method: 'PUT',
    body: JSON.stringify({ draft_ids: draftIds }),
  })
}

export async function createDraftFromReference(
  templateKey: string,
): Promise<APIResponse<{ draft_id: string }>> {
  return apiRequest(`/builder/from-reference/${templateKey}`, { method: 'POST' })
}

export async function createDraftFromResume(
  resumeId: string,
): Promise<APIResponse<{ draft_id: string }>> {
  return apiRequest(`/builder/from-resume/${resumeId}`, { method: 'POST' })
}

export async function getDraft(draftId: string): Promise<APIResponse<ResumeDraftData>> {
  return apiRequest(`/builder/${draftId}`)
}

export async function updateDraft(
  draftId: string,
  payload: UpdateDraftPayload,
): Promise<APIResponse<ResumeDraftData>> {
  return assistantRequest(`/${draftId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
}

export class AssistantApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(`Assistant API error (${status})`)
    this.status = status
    this.detail = detail
  }
}

async function assistantRequest<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new AssistantApiError(res.status, body?.detail ?? body)
  return body
}

export async function getAssistantConversation(
  draftId: string,
): Promise<APIResponse<AssistantConversation | null>> {
  return assistantRequest(`/${draftId}/assistant`)
}

export async function createAssistantTurn(
  draftId: string,
  payload: {
    message: string
    base_revision: number
    client_request_id: string
    conversation_id?: string
  },
): Promise<APIResponse<AssistantConversation>> {
  return assistantRequest(`/${draftId}/assistant/turns`, {
    method: 'POST',
    body: JSON.stringify(payload),
  })
}

export async function applyAssistantProposal(
  draftId: string,
  proposalId: string,
  baseRevision: number,
  selectedOperationIds: string[],
): Promise<APIResponse<ResumeDraftData>> {
  return assistantRequest(`/${draftId}/assistant/proposals/${proposalId}/apply`, {
    method: 'POST',
    body: JSON.stringify({
      base_revision: baseRevision,
      selected_operation_ids: selectedOperationIds,
    }),
  })
}

export async function rejectAssistantProposal(
  draftId: string,
  proposalId: string,
): Promise<APIResponse<{ proposal_id: string; status: string }>> {
  return assistantRequest(`/${draftId}/assistant/proposals/${proposalId}/reject`, {
    method: 'POST',
  })
}

export async function undoAssistantProposal(
  draftId: string,
  proposalId: string,
): Promise<APIResponse<ResumeDraftData>> {
  return assistantRequest(`/${draftId}/assistant/proposals/${proposalId}/undo`, {
    method: 'POST',
  })
}

export async function deleteDraft(
  draftId: string,
): Promise<APIResponse<{ draft_id: string }>> {
  return apiRequest(`/builder/${draftId}`, { method: 'DELETE' })
}

export async function polishSection(
  draftId: string,
  sectionType: string,
  items: string[],
  context?: string,
): Promise<APIResponse<PolishResult>> {
  return apiRequest(`/builder/${draftId}/polish`, {
    method: 'POST',
    body: JSON.stringify({ section_type: sectionType, items, context }),
  })
}

export async function scoreDraft(draftId: string): Promise<APIResponse<ScoreResult>> {
  return apiRequest(`/builder/${draftId}/score`, { method: 'POST' })
}

/** 生成临时预览 PDF；替换值只存在于本次请求和浏览器 Blob URL。 */
export async function previewDraftPdf(
  draftId: string,
  payload: ExportPayload,
): Promise<Blob> {
  const res = await fetch(`${BASE}/${draftId}/preview`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) throw new Error(`Preview failed (${res.status})`)
  return res.blob()
}

/** Legacy read-only preview URL used by the resume list thumbnail. */
export function previewUrl(draftId: string): string {
  return `${BASE}/${draftId}/preview`
}

/** 导出 PDF —— 返回二进制 Blob，供前端触发下载。 */
export async function exportDraftPdf(
  draftId: string,
  payload: ExportPayload,
): Promise<{ blob: Blob; pageCount: number; targetMet: boolean; appliedDensity: string }> {
  const res = await fetch(`${BASE}/${draftId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(`Export failed (${res.status})`)
  }
  const pageCount = Number(res.headers.get('X-Page-Count') ?? '1')
  const targetMet = res.headers.get('X-Target-Met') !== 'false'
  const appliedDensity = res.headers.get('X-Layout-Density') ?? 'normal'
  const blob = await res.blob()
  return { blob, pageCount, targetMet, appliedDensity }
}

/** 照片接口错误——携带 HTTP 状态码与后端 detail，供前端差异化文案。 */
export class PhotoApiError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(`Photo API error (${status}): ${detail}`)
    this.status = status
    this.detail = detail
  }
}

async function throwPhotoError(res: Response): Promise<never> {
  let detail = ''
  try {
    const body = (await res.json()) as { detail?: string; message?: string }
    detail = body.detail ?? body.message ?? ''
  } catch {
    // 非 JSON 响应，detail 保持空字符串
  }
  throw new PhotoApiError(res.status, detail)
}

/** 上传生活照并处理为证件照（不写入草稿，需 confirm）。 */
export async function uploadPhoto(
  draftId: string,
  file: File,
  bgColor: PhotoBgColor,
): Promise<PhotoUploadResult> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE}/${draftId}/photo?bg_color=${bgColor}`, {
    method: 'POST',
    body: form,
  })
  if (!res.ok) await throwPhotoError(res)
  const body = (await res.json()) as APIResponse<PhotoUploadResult>
  return body.data
}

/** 确认采用处理后的证件照，写入草稿 identity.photo。 */
export async function confirmPhoto(
  draftId: string,
  objectName: string,
): Promise<ResumeDraftData> {
  const res = await fetch(`${BASE}/${draftId}/photo/confirm`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ object_name: objectName }),
  })
  if (!res.ok) await throwPhotoError(res)
  const body = (await res.json()) as APIResponse<ResumeDraftData>
  return body.data
}

/** 移除草稿的证件照引用。 */
export async function deletePhoto(draftId: string): Promise<ResumeDraftData> {
  const res = await fetch(`${BASE}/${draftId}/photo`, { method: 'DELETE' })
  if (!res.ok) await throwPhotoError(res)
  const body = (await res.json()) as APIResponse<ResumeDraftData>
  return body.data
}
