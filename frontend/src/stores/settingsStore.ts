import { create } from 'zustand'
import { listLLMConfigs } from '@/api/settings'
import type { LLMConfig } from '@/types/settings'

interface SettingsState {
  configs: LLMConfig[]
  /** LLM 就绪 = 存在已激活且已验证（测试通过）的配置，上传门禁与齿轮指示共用 */
  llmReady: boolean
  loading: boolean
  /** 是否已成功加载过配置列表（避免首屏未加载时误判未就绪） */
  loaded: boolean
  refresh: () => Promise<void>
}

export const useSettingsStore = create<SettingsState>((set) => ({
  configs: [],
  llmReady: false,
  loading: false,
  loaded: false,
  refresh: async () => {
    set({ loading: true })
    try {
      const res = await listLLMConfigs()
      if (res.code === 0) {
        set({
          configs: res.data,
          llmReady: res.data.some((c) => c.is_active && c.verified),
          loaded: true,
        })
      }
    } catch {
      // 网络异常时保留现有状态，后端 428 门禁兜底
    } finally {
      set({ loading: false })
    }
  },
}))
