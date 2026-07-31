import { create } from 'zustand'

/** 本地简历历史记录 —— 按 PRD（llm-gate-and-my-resumes）为 localStorage-only 方案。 */
export interface ResumeHistoryEntry {
  resume_id: string
  file_name: string
  /** ISO 时间字符串 */
  uploaded_at: string
  /** 最新已知处理状态（进入列表页时会拉后端刷新） */
  status: string
}

const STORAGE_KEY = 'my-resumes'
/** 本地列表上限：超出时丢弃最早上传的记录 */
export const MAX_HISTORY = 10

function loadEntries(): ResumeHistoryEntry[] {
  if (typeof localStorage === 'undefined') return []
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return []
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return []
    return parsed.filter(
      (e): e is ResumeHistoryEntry =>
        typeof e?.resume_id === 'string' && typeof e?.file_name === 'string',
    )
  } catch {
    return []
  }
}

function persist(entries: ResumeHistoryEntry[]) {
  if (typeof localStorage === 'undefined') return
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(entries))
  } catch {
    // localStorage 满/被禁用时静默降级，不阻塞主流程
  }
}

/** 按上传时间倒序排序（最新在前），并截断到上限（丢弃最早的）。 */
function normalize(entries: ResumeHistoryEntry[]): ResumeHistoryEntry[] {
  const sorted = [...entries].sort(
    (a, b) => new Date(b.uploaded_at).getTime() - new Date(a.uploaded_at).getTime(),
  )
  return sorted.slice(0, MAX_HISTORY)
}

interface ResumeHistoryState {
  entries: ResumeHistoryEntry[]
  /** 新增记录（按 resume_id 去重：重复上传时更新既有记录而非新增） */
  addEntry: (entry: ResumeHistoryEntry) => void
  /** 更新某条记录的状态（轮询/进入列表页刷新时调用） */
  updateStatus: (resumeId: string, status: string) => void
  /** 删除本地记录（不调用后端） */
  removeEntry: (resumeId: string) => void
}

export const useResumeHistoryStore = create<ResumeHistoryState>((set) => ({
  entries: normalize(loadEntries()),
  addEntry: (entry) =>
    set((state) => {
      const rest = state.entries.filter((e) => e.resume_id !== entry.resume_id)
      const entries = normalize([entry, ...rest])
      persist(entries)
      return { entries }
    }),
  updateStatus: (resumeId, status) =>
    set((state) => {
      const entries = state.entries.map((e) =>
        e.resume_id === resumeId ? { ...e, status } : e,
      )
      persist(entries)
      return { entries }
    }),
  removeEntry: (resumeId) =>
    set((state) => {
      const entries = state.entries.filter((e) => e.resume_id !== resumeId)
      persist(entries)
      return { entries }
    }),
}))
