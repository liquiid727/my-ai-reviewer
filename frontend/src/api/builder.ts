import { apiRequest } from './client'
import type { APIResponse } from '@/types/resume'
import type {
  ExportPayload,
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
