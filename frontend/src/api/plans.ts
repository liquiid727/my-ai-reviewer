import { apiRequest } from './client'
import type {
  EligibleResumeListData,
  PlanDetail,
  PlanListData,
  PlanMutationData,
  PlanResponse,
  PlanStatus,
  PlanTask,
  PlanTaskCategory,
  PlanTaskPriority,
  PlanTaskStatus,
} from '@/types/plans'

function query(params: Record<string, string | number | boolean | undefined>) {
  const values = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') values.set(key, String(value))
  })
  const encoded = values.toString()
  return encoded ? `?${encoded}` : ''
}

export function listPlans(params: { page?: number; pageSize?: number; q?: string; status?: PlanStatus | '' } = {}) {
  return apiRequest<PlanResponse<PlanListData>>(`/plans${query({
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
    q: params.q,
    status: params.status,
  })}`)
}

export function getPlan(id: string) {
  return apiRequest<PlanResponse<PlanDetail>>(`/plans/${id}`)
}

export function listEligibleResumes(params: { page?: number; pageSize?: number } = {}) {
  return apiRequest<PlanResponse<EligibleResumeListData>>(`/resume${query({
    has_profile: true,
    page: params.page ?? 1,
    page_size: params.pageSize ?? 20,
  })}`)
}

export function createPlan(input: {
  jd_id: string
  resume_id: string
  title?: string
  target_date?: string
  weekly_hours?: number
  supplemental_background?: string
  job_target_id?: string
  jd_version_id?: string
  resume_version_id?: string
  match_assessment_id?: string
}) {
  return apiRequest<PlanResponse<{ id: string; status: PlanStatus; revision: number; generation_error?: string | null }>>(
    '/plans',
    { method: 'POST', body: JSON.stringify(input) },
  )
}

export function retryPlan(id: string, expectedRevision: number) {
  return apiRequest<PlanResponse<{ id: string; status: PlanStatus; revision: number; generation_error?: string | null }>>(
    `/plans/${id}/retry`,
    { method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision }) },
  )
}

export function regeneratePlan(id: string, expectedRevision: number) {
  return apiRequest<PlanResponse<{ id: string; status: PlanStatus; revision: number; generation_error?: string | null }>>(
    `/plans/${id}/regenerate`,
    { method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision }) },
  )
}

export function patchPlan(id: string, input: {
  expected_revision: number
  title?: string
  target_date?: string | null
  weekly_hours?: number | null
  supplemental_background?: string | null
}) {
  return apiRequest<PlanResponse<PlanDetail>>(`/plans/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function createPlanTask(id: string, input: {
  expected_revision: number
  title: string
  category: PlanTaskCategory
  description?: string
  priority?: PlanTaskPriority
  status?: PlanTaskStatus
  due_date?: string | null
}) {
  return apiRequest<PlanResponse<PlanMutationData>>(`/plans/${id}/tasks`, {
    method: 'POST',
    body: JSON.stringify(input),
  })
}

export function patchPlanTask(id: string, taskId: string, input: {
  expected_revision: number
  title?: string
  category?: PlanTaskCategory
  description?: string
  priority?: PlanTaskPriority
  status?: PlanTaskStatus
  due_date?: string | null
}) {
  return apiRequest<PlanResponse<PlanMutationData>>(`/plans/${id}/tasks/${taskId}`, {
    method: 'PATCH',
    body: JSON.stringify(input),
  })
}

export function deletePlanTask(id: string, taskId: string, expectedRevision: number) {
  return apiRequest<PlanResponse<PlanMutationData>>(`/plans/${id}/tasks/${taskId}${query({ expected_revision: expectedRevision })}`, {
    method: 'DELETE',
  })
}

export function reorderPlanTasks(id: string, expectedRevision: number, taskIds: string[]) {
  return apiRequest<PlanResponse<PlanMutationData>>(`/plans/${id}/tasks/order`, {
    method: 'PUT',
    body: JSON.stringify({ expected_revision: expectedRevision, task_ids: taskIds }),
  })
}

export function deletePlan(id: string, expectedRevision: number) {
  return apiRequest<PlanResponse<unknown>>(`/plans/${id}${query({ expected_revision: expectedRevision })}`, {
    method: 'DELETE',
  })
}

export function asPlanTask(input: Partial<PlanTask>): PlanTask {
  return input as PlanTask
}
