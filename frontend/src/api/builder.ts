import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type {
  ExportPayload,
  PhotoBgColor,
  PhotoUploadResult,
  PolishResult,
  ResumeDraftData,
  ScoreResult,
  TemplateOptions,
  UpdateDraftPayload,
} from '@/types/builder'

const BASE = '/api/v1/builder'

export async function getTemplateOptions(): Promise<APIResponse<TemplateOptions>> {
  return apiRequest('/builder/templates')
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
  return apiRequest(`/builder/${draftId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  })
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

/** 预览 URL —— 直接给 iframe 的 src 使用（返回 text/html）。 */
export function previewUrl(draftId: string): string {
  return `${BASE}/${draftId}/preview`
}

/** 导出 PDF —— 返回二进制 Blob，供前端触发下载。 */
export async function exportDraftPdf(
  draftId: string,
  payload: ExportPayload,
): Promise<{ blob: Blob; pageCount: number; overflow: boolean }> {
  const res = await fetch(`${BASE}/${draftId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    throw new Error(`Export failed (${res.status})`)
  }
  const pageCount = Number(res.headers.get('X-Page-Count') ?? '1')
  const overflow = res.headers.get('X-Overflow') === 'true'
  const blob = await res.blob()
  return { blob, pageCount, overflow }
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
