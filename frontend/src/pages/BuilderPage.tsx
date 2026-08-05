import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { ChangeEvent } from 'react'
import { useParams, useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
} from 'recharts'
import {
  ArrowLeft,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  Eye,
  EyeOff,
  Sparkles,
  Download,
  BarChart3,
  Loader2,
  X,
  Check,
  Camera,
  CircleAlert,
  FileText,
  Palette,
  ZoomIn,
  ZoomOut,
  Maximize,
  Maximize2,
  Minimize2,
  PanelLeftClose,
  PanelLeftOpen,
  Bot,
  RefreshCw,
  CircleCheck,
} from 'lucide-react'

import { BuilderSaveStatus } from '@/components/builder/BuilderSaveStatus'
import {
  mapBuilderSaveError,
  mapBuilderSaveResponse,
  type BuilderSaveStatus as SaveStatusKind,
} from '@/lib/builder-save'
import {
  getDraft,
  updateDraft,
  polishSection,
  scoreDraft,
  getDraftScore,
  createAssistantTurn,
  applyAssistantProposal,
  AssistantApiError,
  exportDraftPdf,
  previewDraftPdf,
  previewUrl,
  uploadPhoto,
  confirmPhoto,
  deletePhoto,
  PhotoApiError,
} from '@/api/builder'
import type {
  ResumeDraftData,
  DraftSection,
  DraftItem,
  DesignTokens,
  LayoutDensity,
  LayoutMode,
  TemplateId,
  PolishResult,
  ScoreResult,
  ScoreImprovement,
  UpdateDraftPayload,
  PhotoBgColor,
  PhotoUploadResult,
} from '@/types/builder'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { ExportPreviewDialog } from '@/components/ExportPreviewDialog'
import { ResumeAssistantPanel } from '@/components/ResumeAssistantPanel'
import { useSettingsStore } from '@/stores/settingsStore'

const TEMPLATES: TemplateId[] = ['classic', 'modern', 'compact']
const DENSITIES: LayoutDensity[] = ['loose', 'normal', 'tight', 'compact']
const PHOTO_BGS: PhotoBgColor[] = ['white', 'blue', 'red']
const PHOTO_ACCEPT_TYPES = ['image/jpeg', 'image/png']
const PHOTO_MAX_SIZE = 10 * 1024 * 1024
const LLM_NOT_READY_CODE = 428

// A4 页面宽度（96dpi 下 210mm ≈ 794px），预览按此宽度等比缩放
const A4_WIDTH = 794
// 预览画布内边距（px）
const PREVIEW_PADDING = 16

// 样式面板的字体预设（key 对应 i18n builder.font_*）
const FONT_OPTIONS = [
  { key: 'sans', value: "'Noto Sans SC', 'Helvetica Neue', Arial, sans-serif" },
  { key: 'serif', value: "'Noto Serif SC', 'Songti SC', 'SimSun', serif" },
  { key: 'system', value: "-apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif" },
] as const

// 页边距预设（key 对应 i18n builder.margin_*）
const MARGIN_OPTIONS = [
  { key: 'narrow', value: '32px' },
  { key: 'normal', value: '48px' },
  { key: 'wide', value: '64px' },
] as const

// 主题色快捷色板
const ACCENT_PRESETS = ['#2563eb', '#0f766e', '#7c3aed', '#b91c1c', '#c2410c', '#0f172a']

const SELECT_CLASS =
  'rounded-base border-2 border-border bg-white px-3 py-1.5 text-sm font-base shadow-shadow focus:outline-none'

// 左侧板块导航项：点击打开对应编辑面板
const SIDEBAR_ITEM_CLASS =
  'flex shrink-0 cursor-pointer items-center gap-2 rounded-base border-2 border-border px-3 py-2 text-sm font-heading shadow-shadow transition-colors hover:bg-main/50'

// 编辑面板内的字段标签
const FIELD_LABEL_CLASS = 'mb-1 block text-xs font-heading text-gray-500'

// 编辑面板可编辑目标：样式 / 证件照 / 简介 / 某个 section 下标
type PanelKey = 'style' | 'photo' | 'summary' | number

// 评分进度弹窗展示的阶段性文案（实际完成时机由 API 返回驱动）
const SCORE_STEP_KEYS = ['scoreStep1', 'scoreStep2', 'scoreStep3'] as const

interface PolishTarget {
  sectionIdx: number
  itemIdx: number
  result: PolishResult
  accepted: boolean[]
}

export function BuilderPage() {
  const { draftId } = useParams()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [draft, setDraft] = useState<ResumeDraftData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saveStatus, setSaveStatus] = useState<SaveStatusKind>('idle')
  const [saveConflictMessage, setSaveConflictMessage] = useState<string | null>(null)
  const [previewNonce, setPreviewNonce] = useState(0)
  const [polishTarget, setPolishTarget] = useState<PolishTarget | null>(null)
  const [polishingKey, setPolishingKey] = useState<string | null>(null)
  const [polishingAll, setPolishingAll] = useState(false)
  const [scoring, setScoring] = useState(false)
  const [score, setScore] = useState<ScoreResult | null>(null)
  const [scoreOpen, setScoreOpen] = useState(false)
  // 上次持久化评分（后端保存的最新结果），再次点击“AI 打分”时直接展示
  const [savedScore, setSavedScore] = useState<ScoreResult | null>(null)
  // 评分进度弹窗状态：running 显示分步进度，done 短暂显示完成后打开报告抽屉
  const [scoreProgress, setScoreProgress] = useState<'closed' | 'running' | 'done'>('closed')
  const [scoreStepIdx, setScoreStepIdx] = useState(0)
  // “简历已更新，是否重新评分？”确认弹窗
  const [rescoreDialogOpen, setRescoreDialogOpen] = useState(false)
  // 正在采纳的改进建议索引；null 表示空闲
  const [adoptingIdx, setAdoptingIdx] = useState<number | null>(null)
  const [exporting, setExporting] = useState(false)
  const [exportPreviewOpen, setExportPreviewOpen] = useState(false)
  const [exportReplacements, setExportReplacements] = useState<Record<string, string>>({})
  const [previewSrc, setPreviewSrc] = useState('')
  const [previewRequestKey, setPreviewRequestKey] = useState(0)
  // 预览 iframe 加载态：src 变化（首次加载 / 保存后刷新）时显示占位，onLoad 后切换为真实内容
  const [previewLoading, setPreviewLoading] = useState(true)

  // 当前打开的编辑面板； null 表示关闭（预览独占）
  const [activePanel, setActivePanel] = useState<PanelKey | null>(null)
  // 编辑模式：填写模式（板块导航）/ AI 助手模式（左侧变为与 AI Agent 的对话）
  const [editorMode, setEditorMode] = useState<'form' | 'assistant'>('form')
  // 左侧内容区（板块导航 + 编辑面板）可整体收起，给预览更多空间
  const [editorVisible, setEditorVisible] = useState(true)

  const togglePanel = useCallback((panel: PanelKey) => {
    setActivePanel((current) => (current === panel ? null : panel))
  }, [])

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setActivePanel(null)
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [])

  // 预览缩放：'fit' 自动适应宽度；数字为手动倍率
  const [zoom, setZoom] = useState<'fit' | number>('fit')
  const [previewBox, setPreviewBox] = useState({ width: 0, height: 0 })
  const [isPreviewFullscreen, setIsPreviewFullscreen] = useState(false)
  const previewElementRef = useRef<HTMLDivElement | null>(null)
  const previewRoRef = useRef<ResizeObserver | null>(null)
  // callback ref：预览容器挂载/卸载时维护 ResizeObserver；挂载时先同步量一次，不依赖首帧回调
  const previewBoxRef = useCallback((el: HTMLDivElement | null) => {
    previewRoRef.current?.disconnect()
    previewRoRef.current = null
    previewElementRef.current = el
    if (!el) return
    setPreviewBox({ width: el.clientWidth, height: el.clientHeight })
    const ro = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect
      if (rect) setPreviewBox({ width: rect.width, height: rect.height })
    })
    ro.observe(el)
    previewRoRef.current = ro
  }, [])

  useEffect(() => {
    const handleFullscreenChange = () => {
      setIsPreviewFullscreen(document.fullscreenElement === previewElementRef.current)
    }

    document.addEventListener('fullscreenchange', handleFullscreenChange)
    return () => document.removeEventListener('fullscreenchange', handleFullscreenChange)
  }, [])

  const [photoBg, setPhotoBg] = useState<PhotoBgColor>('white')
  const [photoUploading, setPhotoUploading] = useState(false)
  const [photoResult, setPhotoResult] = useState<PhotoUploadResult | null>(null)
  const [photoConfirming, setPhotoConfirming] = useState(false)
  const [photoRemoving, setPhotoRemoving] = useState(false)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const photoInputRef = useRef<HTMLInputElement | null>(null)
  const photoFileRef = useRef<File | null>(null)

  // LLM 门禁：AI 润色/打分依赖已激活且已验证的配置，与上传页共用 settingsStore
  const {
    configs: llmConfigs,
    llmReady,
    loaded: settingsLoaded,
    refresh: refreshSettings,
  } = useSettingsStore()
  const [gateOpen, setGateOpen] = useState(false)
  const gateShownRef = useRef(false)
  const llmBlocked = settingsLoaded && !llmReady

  const dirtyRef = useRef(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const revisionRef = useRef(1)
  const draftRef = useRef<ResumeDraftData | null>(null)
  const saveQueueRef = useRef<Promise<void>>(Promise.resolve())

  const activeLlmModel = useMemo(() => {
    const active = llmConfigs
      .filter((config) => config.is_active && config.verified)
      .sort((a, b) => Date.parse(b.updated_at) - Date.parse(a.updated_at))[0]
    return active?.model_name ?? null
  }, [llmConfigs])

  // ─────────────────────────── 加载 ───────────────────────────
  useEffect(() => {
    if (!draftId) return
    let alive = true
    setLoading(true)
    setError(null)
    // 切换草稿时清理上一草稿的照片临时状态，避免错带旧对象名 confirm
    setPhotoResult(null)
    setPhotoError(null)
    photoFileRef.current = null
    getDraft(draftId)
      .then((res) => {
        if (!alive) return
        if (res.code !== 0) {
          setError(res.message || t('builder.loadFailed'))
          return
        }
        revisionRef.current = res.data.revision
        draftRef.current = res.data
        setDraft(res.data)
      })
      .catch((err: unknown) => {
        if (alive) setError((err as Error).message || t('builder.loadFailed'))
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [draftId, t])

  useEffect(() => {
    if (!exportPreviewOpen || !draftId || !draft) return
    let alive = true
    let objectUrl = ''
    setPreviewSrc('')
    previewDraftPdf(draftId, {
      layout_policy: draft.layout_policy,
      replacements: exportReplacements,
    })
      .then((blob) => {
        if (!alive) return
        objectUrl = URL.createObjectURL(blob)
        setPreviewSrc(objectUrl)
      })
      .catch(() => {
        if (alive) setPreviewSrc('')
      })
    return () => {
      alive = false
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [draftId, draft, exportPreviewOpen, exportReplacements, previewRequestKey])

  useEffect(() => {
    draftRef.current = draft
  }, [draft])

  // 进入编辑器时拉取 LLM 配置就绪状态，供门禁判定
  useEffect(() => {
    void refreshSettings()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 首次检测到未就绪时自动弹出配置引导弹窗（每次进入仅提醒一次）
  useEffect(() => {
    if (llmBlocked && !gateShownRef.current) {
      gateShownRef.current = true
      setGateOpen(true)
    }
  }, [llmBlocked])

  const handleLlmNotReady = useCallback(
    (code: number): boolean => {
      if (code !== LLM_NOT_READY_CODE) return false
      void refreshSettings()
      setGateOpen(true)
      return true
    },
    [refreshSettings],
  )

  // 未就绪时拦截 AI 动作，弹窗引导配置；返回是否放行
  const ensureLlmReady = useCallback((): boolean => {
    const state = useSettingsStore.getState()
    if (state.loaded && state.llmReady) return true
    setGateOpen(true)
    return false
  }, [])

  // ─────────────────────────── 保存 ───────────────────────────
  const buildPatch = useCallback((d: ResumeDraftData): UpdateDraftPayload => {
    return {
      title: d.title,
      identity: d.identity,
      summary: d.summary,
      sections: d.sections,
      template_id: d.template_id,
      design_tokens: d.design_tokens,
      layout_policy: d.layout_policy,
    }
  }, [])

  const persist = useCallback(
    (d: ResumeDraftData): Promise<number> => {
      if (!draftId) return Promise.resolve(revisionRef.current)
      const run = saveQueueRef.current
        .catch(() => undefined)
        .then(async () => {
          setSaveStatus('saving')
          setSaveConflictMessage(null)
          try {
            const res = await updateDraft(draftId, {
              ...buildPatch(d),
              base_revision: revisionRef.current,
            })
            const outcome = mapBuilderSaveResponse(res, t('builder.saveFailed'))
            if (outcome.kind === 'conflict') {
              setSaveStatus('conflict')
              setSaveConflictMessage(outcome.message || t('builder.revisionConflict'))
              toast.error(outcome.message || t('builder.revisionConflict'))
              throw new Error(outcome.message || t('builder.revisionConflict'))
            }
            if (outcome.kind === 'error') {
              setSaveStatus('error')
              toast.error(outcome.message || t('builder.saveFailed'))
              throw new Error(outcome.message || t('builder.saveFailed'))
            }
            revisionRef.current = outcome.revision
            setDraft((current) =>
              current ? { ...current, revision: outcome.revision } : res.data,
            )
            setSaveStatus('saved')
            setPreviewNonce((n) => n + 1)
            return outcome.revision
          } catch (err) {
            // Envelope failures already set status + toast above; only map thrown API errors.
            if (err && typeof err === 'object' && 'status' in err) {
              const outcome = mapBuilderSaveError(err, t('builder.saveFailed'))
              if (outcome.kind === 'conflict') {
                setSaveStatus('conflict')
                setSaveConflictMessage(outcome.message || t('builder.revisionConflict'))
              } else {
                setSaveStatus('error')
              }
              toast.error(outcome.message || t('builder.saveFailed'))
            }
            throw err
          }
        })
      saveQueueRef.current = run.then(() => undefined, () => undefined)
      return run
    },
    [draftId, buildPatch, t],
  )

  const flushDraft = useCallback(async (): Promise<number> => {
    if (saveTimer.current) {
      clearTimeout(saveTimer.current)
      saveTimer.current = null
    }
    if (dirtyRef.current && draftRef.current) {
      dirtyRef.current = false
      await persist(draftRef.current)
    }
    await saveQueueRef.current
    return revisionRef.current
  }, [persist])

  const acceptServerDraft = useCallback((nextDraft: ResumeDraftData) => {
    if (saveTimer.current) clearTimeout(saveTimer.current)
    saveTimer.current = null
    dirtyRef.current = false
    revisionRef.current = nextDraft.revision
    draftRef.current = nextDraft
    setDraft(nextDraft)
    setSaveStatus('saved')
    setSaveConflictMessage(null)
    setPreviewNonce((nonce) => nonce + 1)
  }, [])

  const reloadDraft = useCallback(async () => {
    if (!draftId) return
    await saveQueueRef.current
    const response = await getDraft(draftId)
    if (response.code !== 0) throw new Error(response.message || t('builder.loadFailed'))
    acceptServerDraft(response.data)
  }, [acceptServerDraft, draftId, t])

  // 修改本地草稿并调度防抖保存
  const mutate = useCallback(
    (mutator: (prev: ResumeDraftData) => ResumeDraftData, immediate = false) => {
      setDraft((prev) => {
        if (!prev) return prev
        const next = mutator(prev)
        dirtyRef.current = true
        if (saveTimer.current) clearTimeout(saveTimer.current)
        saveTimer.current = setTimeout(
          () => {
            dirtyRef.current = false
            void persist(next).catch(() => undefined)
          },
          immediate ? 0 : 1000,
        )
        return next
      })
    },
    [persist],
  )

  useEffect(() => {
    return () => {
      if (saveTimer.current) clearTimeout(saveTimer.current)
    }
  }, [])

  // ─────────────────────────── section / item 编辑 ───────────────────────────
  const updateSection = useCallback(
    (sectionIdx: number, patch: Partial<DraftSection>) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) =>
          i === sectionIdx ? { ...s, ...patch } : s,
        )
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const updateItem = useCallback(
    (sectionIdx: number, itemIdx: number, patch: Partial<DraftItem>) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) => {
          if (i !== sectionIdx) return s
          const items = s.items.map((it, j) => (j === itemIdx ? { ...it, ...patch } : it))
          return { ...s, items }
        })
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const moveSection = useCallback(
    (sectionIdx: number, dir: -1 | 1) => {
      mutate((prev) => {
        const target = sectionIdx + dir
        if (target < 0 || target >= prev.sections.length) return prev
        const sections = [...prev.sections]
        const tmp = sections[sectionIdx]
        sections[sectionIdx] = sections[target]
        sections[target] = tmp
        return { ...prev, sections: sections.map((s, i) => ({ ...s, order: i })) }
      })
      // 抽屉跟随被移动的板块，保持编辑焦点不变
      setActivePanel((p) => {
        if (typeof p !== 'number' || !draft) return p
        const target = sectionIdx + dir
        if (target < 0 || target >= draft.sections.length) return p
        if (p === sectionIdx) return target
        if (p === target) return sectionIdx
        return p
      })
    },
    [mutate, draft],
  )

  const addItem = useCallback(
    (sectionIdx: number) => {
      const empty: DraftItem = {
        item_id: globalThis.crypto.randomUUID(),
        heading: '',
        subheading: '',
        date_range: '',
        bullets: [''],
      }
      mutate((prev) => {
        const sections = prev.sections.map((s, i) =>
          i === sectionIdx ? { ...s, items: [...s.items, empty] } : s,
        )
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const removeItem = useCallback(
    (sectionIdx: number, itemIdx: number) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) =>
          i === sectionIdx ? { ...s, items: s.items.filter((_, j) => j !== itemIdx) } : s,
        )
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const updateBullet = useCallback(
    (sectionIdx: number, itemIdx: number, bulletIdx: number, value: string) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) => {
          if (i !== sectionIdx) return s
          const items = s.items.map((it, j) => {
            if (j !== itemIdx) return it
            const bullets = it.bullets.map((b, k) => (k === bulletIdx ? value : b))
            return { ...it, bullets }
          })
          return { ...s, items }
        })
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const addBullet = useCallback(
    (sectionIdx: number, itemIdx: number) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) => {
          if (i !== sectionIdx) return s
          const items = s.items.map((it, j) =>
            j === itemIdx ? { ...it, bullets: [...it.bullets, ''] } : it,
          )
          return { ...s, items }
        })
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  const removeBullet = useCallback(
    (sectionIdx: number, itemIdx: number, bulletIdx: number) => {
      mutate((prev) => {
        const sections = prev.sections.map((s, i) => {
          if (i !== sectionIdx) return s
          const items = s.items.map((it, j) =>
            j === itemIdx
              ? { ...it, bullets: it.bullets.filter((_, k) => k !== bulletIdx) }
              : it,
          )
          return { ...s, items }
        })
        return { ...prev, sections }
      })
    },
    [mutate],
  )

  // ─────────────────────────── 模板与样式设置 ───────────────────────────
  const changeTemplate = useCallback(
    (id: TemplateId) => mutate((prev) => ({ ...prev, template_id: id }), true),
    [mutate],
  )
  // 样式面板：更新设计令牌（密度 / 主题色 / 字体 / 页边距 / 自定义 CSS）
  const updateTokens = useCallback(
    (patch: Partial<DesignTokens>, immediate = true) =>
      mutate(
        (prev) => ({ ...prev, design_tokens: { ...prev.design_tokens, ...patch } }),
        immediate,
      ),
    [mutate],
  )
  const changeLayoutMode = useCallback(
    (mode: LayoutMode) =>
      mutate(
        (prev) => ({
          ...prev,
          layout_policy: {
            mode,
            target_page_count:
              mode === 'target_pages' ? (prev.layout_policy.target_page_count ?? 1) : null,
          },
        }),
        true,
      ),
    [mutate],
  )
  const changeTargetPageCount = useCallback(
    (targetPageCount: number) =>
      mutate(
        (prev) => ({
          ...prev,
          layout_policy: {
            mode: 'target_pages',
            target_page_count: targetPageCount,
          },
        }),
        true,
      ),
    [mutate],
  )

  // ─────────────────────────── AI 润色 ───────────────────────────
  const runPolish = useCallback(
    async (sectionIdx: number, itemIdx: number): Promise<PolishResult | null> => {
      if (!draftId || !draft) return null
      const section = draft.sections[sectionIdx]
      const item = section.items[itemIdx]
      const bullets = item.bullets.filter((b) => b.trim())
      if (bullets.length === 0) return null
      const res = await polishSection(draftId, section.section_type, bullets, section.title)
      if (res.code !== 0) {
        if (handleLlmNotReady(res.code)) return null
        toast.error(res.message || t('builder.polishFailed'))
        return null
      }
      return res.data
    },
    [draftId, draft, handleLlmNotReady, t],
  )

  const openPolish = useCallback(
    async (sectionIdx: number, itemIdx: number) => {
      if (!ensureLlmReady()) return
      const key = `${sectionIdx}-${itemIdx}`
      setPolishingKey(key)
      try {
        const result = await runPolish(sectionIdx, itemIdx)
        if (!result) return
        setPolishTarget({
          sectionIdx,
          itemIdx,
          result,
          accepted: result.polished_items.map(() => false),
        })
      } catch (err) {
        toast.error((err as Error).message || t('builder.polishFailed'))
      } finally {
        setPolishingKey(null)
      }
    },
    [runPolish, ensureLlmReady, t],
  )

  // 采用润色结果：把 polished bullets 写回对应 item（仅覆盖有原文的条目）
  const applyPolish = useCallback(
    (onlyIndex?: number) => {
      if (!polishTarget) return
      const { sectionIdx, itemIdx, result } = polishTarget
      mutate((prev) => {
        const sections = prev.sections.map((s, i) => {
          if (i !== sectionIdx) return s
          const items = s.items.map((it, j) => {
            if (j !== itemIdx) return it
            // 原始非空 bullet 的下标序列，与 polished_items 一一对应
            const nonEmptyIdx: number[] = []
            it.bullets.forEach((b, k) => {
              if (b.trim()) nonEmptyIdx.push(k)
            })
            const bullets = [...it.bullets]
            result.polished_items.forEach((polished, p) => {
              if (onlyIndex !== undefined && p !== onlyIndex) return
              const targetK = nonEmptyIdx[p]
              if (targetK !== undefined) bullets[targetK] = polished
            })
            return { ...it, bullets }
          })
          return { ...s, items }
        })
        return { ...prev, sections }
      })
      if (onlyIndex === undefined) {
        setPolishTarget(null)
      } else {
        setPolishTarget((prev) =>
          prev
            ? { ...prev, accepted: prev.accepted.map((a, i) => (i === onlyIndex ? true : a)) }
            : prev,
        )
      }
    },
    [polishTarget, mutate],
  )

  const polishAll = useCallback(async () => {
    if (!draft) return
    if (!ensureLlmReady()) return
    setPolishingAll(true)
    let applied = 0
    try {
      // 顺序润色每个 section 的每个 item，直接采用（显式批量动作）
      const nextSections: DraftSection[] = draft.sections.map((s) => ({
        ...s,
        items: s.items.map((it) => ({ ...it, bullets: [...it.bullets] })),
      }))
      for (let si = 0; si < draft.sections.length; si++) {
        const section = draft.sections[si]
        if (!section.visible) continue
        for (let ii = 0; ii < section.items.length; ii++) {
          const result = await runPolish(si, ii)
          if (!result) continue
          const nonEmptyIdx: number[] = []
          nextSections[si].items[ii].bullets.forEach((b, k) => {
            if (b.trim()) nonEmptyIdx.push(k)
          })
          result.polished_items.forEach((polished, p) => {
            const targetK = nonEmptyIdx[p]
            if (targetK !== undefined) {
              nextSections[si].items[ii].bullets[targetK] = polished
              applied++
            }
          })
        }
      }
      if (applied > 0) {
        mutate((prev) => ({ ...prev, sections: nextSections }), true)
      }
      toast.success(t('builder.polished'))
    } catch (err) {
      toast.error((err as Error).message || t('builder.polishFailed'))
    } finally {
      setPolishingAll(false)
    }
  }, [draft, runPolish, mutate, ensureLlmReady, t])

  // ─────────────────────────── AI 打分 ───────────────────────────
  // 挂载时拉取持久化的最新评分（存在时再次点击“AI 打分”直接展示上次结果）
  useEffect(() => {
    if (!draftId) return
    let cancelled = false
    getDraftScore(draftId)
      .then((res) => {
        if (!cancelled && res.code === 0 && res.data) setSavedScore(res.data)
      })
      .catch(() => {
        // 拉取失败退回首次评分行为，不打扰用户
      })
    return () => {
      cancelled = true
    }
  }, [draftId])

  // 评分进行中时按间隔推进进度步骤，传达持续处理感（真正完成由 API 返回驱动）
  useEffect(() => {
    if (scoreProgress !== 'running') return
    setScoreStepIdx(0)
    const timer = window.setInterval(() => {
      setScoreStepIdx((idx) => Math.min(idx + 1, SCORE_STEP_KEYS.length - 1))
    }, 3500)
    return () => window.clearInterval(timer)
  }, [scoreProgress])

  const runScoring = useCallback(async () => {
    if (!draftId) return
    if (!ensureLlmReady()) return
    setScoring(true)
    setScoreProgress('running')
    try {
      const res = await scoreDraft(draftId)
      if (res.code !== 0) {
        setScoreProgress('closed')
        if (handleLlmNotReady(res.code)) return
        toast.error(res.message || t('builder.scoreFailed'))
        return
      }
      setSavedScore(res.data)
      setScoreProgress('done')
      // 短暂展示完成态后再打开报告抽屉
      window.setTimeout(() => {
        setScoreProgress('closed')
        setScore(res.data)
        setScoreOpen(true)
      }, 900)
    } catch (err) {
      setScoreProgress('closed')
      toast.error((err as Error).message || t('builder.scoreFailed'))
    } finally {
      setScoring(false)
    }
  }, [draftId, ensureLlmReady, handleLlmNotReady, t])

  // 点击“AI 打分”：无历史 → 直接评分；最新 → 展示上次结果；已过期 → 询问是否重新评分
  const doScore = useCallback(() => {
    if (!ensureLlmReady()) return
    if (!savedScore) {
      void runScoring()
      return
    }
    const stale =
      savedScore.scored_revision != null &&
      draft != null &&
      savedScore.scored_revision !== draft.revision
    if (stale) {
      setRescoreDialogOpen(true)
      return
    }
    setScore(savedScore)
    setScoreOpen(true)
  }, [draft, savedScore, ensureLlmReady, runScoring])

  // 采纳改进建议：复用 assistant proposal 流程（flush → 以建议为指令 → 应用全部变更）
  const adoptSuggestion = useCallback(
    async (item: ScoreImprovement, index: number) => {
      if (!draftId || !draft) return
      if (!ensureLlmReady()) return
      setAdoptingIdx(index)
      try {
        const baseRevision = await flushDraft()
        const instruction = item.detail
          ? `请根据以下改进建议修改简历。\n建议：${item.point}\n具体要求：${item.detail}`
          : `请根据以下改进建议修改简历：${item.point}`
        const turnRes = await createAssistantTurn(draftId, {
          message: instruction,
          base_revision: baseRevision,
          client_request_id: crypto.randomUUID(),
        })
        if (turnRes.code !== 0) {
          toast.error(turnRes.message || t('builder.suggestionAdoptFailed'))
          return
        }
        const proposal = [...turnRes.data.proposals]
          .reverse()
          .find((p) => p.status === 'proposed')
        if (!proposal || proposal.operations.length === 0) {
          toast.info(t('builder.suggestionNoChanges'))
          return
        }
        const applyRes = await applyAssistantProposal(
          draftId,
          proposal.proposal_id,
          baseRevision,
          proposal.operations.map((op) => op.operation_id),
        )
        if (applyRes.code !== 0) {
          toast.error(applyRes.message || t('builder.suggestionAdoptFailed'))
          return
        }
        acceptServerDraft(applyRes.data)
        toast.success(t('builder.suggestionAdopted'))
      } catch (err) {
        if (err instanceof AssistantApiError && err.status === 409) {
          // revision 冲突时重新拉取最新草稿，用户确认内容后可再次尝试
          await reloadDraft()
        }
        toast.error((err as Error).message || t('builder.suggestionAdoptFailed'))
      } finally {
        setAdoptingIdx(null)
      }
    },
    [draftId, draft, ensureLlmReady, flushDraft, acceptServerDraft, reloadDraft, t],
  )

  // ─────────────────────────── 导出 PDF ───────────────────────────
  const openExportPreview = useCallback(() => {
    if (!draftId || !draft) return
    setExportReplacements(
      Object.fromEntries(draft.privacy_placeholders.map((placeholder) => [placeholder.token, ''])),
    )
    setExportPreviewOpen(true)
  }, [draftId, draft])

  const doExport = useCallback(async () => {
    if (!draftId || !draft) return
    setExporting(true)
    try {
      const { blob, pageCount, targetMet } = await exportDraftPdf(draftId, {
        layout_policy: draft.layout_policy,
        replacements: exportReplacements,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${draft.title || 'resume'}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      setExportPreviewOpen(false)
      if (!targetMet) {
        toast.warning(t('builder.targetUnmet', { count: pageCount }))
      } else {
        toast.success(t('builder.exportedPages', { count: pageCount }))
      }
    } catch (err) {
      toast.error((err as Error).message || t('builder.exportFailed'))
    } finally {
      setExporting(false)
    }
  }, [draftId, draft, exportReplacements, t])

  const printPreview = useCallback(() => {
    if (!previewSrc) return
    const printWindow = window.open(previewSrc, '_blank', 'noopener,noreferrer')
    printWindow?.addEventListener('load', () => printWindow.print(), { once: true })
  }, [previewSrc])

  const src = draftId ? `${previewUrl(draftId)}?v=${previewNonce}` : ''

  useEffect(() => {
    if (src) setPreviewLoading(true)
  }, [src])

  // ─────────────────────────── 证件照 ───────────────────────────
  // 后端错误差异化文案：501 未安装图像组件 / 422 未检测到人脸 / 400 解码失败等
  const photoErrorText = useCallback(
    (err: unknown): string => {
      if (err instanceof PhotoApiError) {
        if (err.status === 501) return t('builder.photo.notAvailable')
        // 422 仅在后端明确返回 FACE_NOT_FOUND 时提示人脸，FastAPI 参数校验型 422 落入通用文案
        if (err.status === 422 && err.detail === 'FACE_NOT_FOUND') {
          return t('builder.photo.faceNotFound')
        }
        if (err.status === 400 && err.detail === 'PHOTO_DECODE_FAILED') {
          return t('builder.photo.decodeFailed')
        }
      }
      return t('builder.photo.uploadFailed')
    },
    [t],
  )

  const doUploadPhoto = useCallback(
    async (file: File, bgColor: PhotoBgColor) => {
      if (!draftId) return
      // 前端先行校验：类型 + 大小，避免无效请求
      if (!PHOTO_ACCEPT_TYPES.includes(file.type)) {
        setPhotoError(t('builder.photo.invalidType'))
        return
      }
      if (file.size > PHOTO_MAX_SIZE) {
        setPhotoError(t('builder.photo.tooLarge'))
        return
      }
      photoFileRef.current = file
      setPhotoError(null)
      setPhotoResult(null)
      setPhotoUploading(true)
      try {
        const result = await uploadPhoto(draftId, file, bgColor)
        setPhotoResult(result)
      } catch (err) {
        setPhotoError(photoErrorText(err))
      } finally {
        setPhotoUploading(false)
      }
    },
    [draftId, photoErrorText, t],
  )

  const onPhotoSelected = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0]
      // 重置 input，允许重新选择同一文件
      e.target.value = ''
      if (file) void doUploadPhoto(file, photoBg)
    },
    [doUploadPhoto, photoBg],
  )

  // 切换背景色：若已有待确认结果，用同一张原图自动重新处理
  const changePhotoBg = useCallback(
    (bgColor: PhotoBgColor) => {
      setPhotoBg(bgColor)
      if (photoResult && photoFileRef.current) {
        void doUploadPhoto(photoFileRef.current, bgColor)
      }
    },
    [photoResult, doUploadPhoto],
  )

  const doConfirmPhoto = useCallback(async () => {
    if (!draftId || !photoResult) return
    setPhotoConfirming(true)
    try {
      await flushDraft()
      const data = await confirmPhoto(draftId, photoResult.processed_object)
      acceptServerDraft(data)
      setPhotoResult(null)
      photoFileRef.current = null
      toast.success(t('builder.photo.confirmed'))
    } catch (err) {
      void err
      toast.error(t('builder.photo.confirmFailed'))
    } finally {
      setPhotoConfirming(false)
    }
  }, [acceptServerDraft, draftId, flushDraft, photoResult, t])

  const doRemovePhoto = useCallback(async () => {
    if (!draftId) return
    setPhotoRemoving(true)
    try {
      await flushDraft()
      const data = await deletePhoto(draftId)
      acceptServerDraft(data)
    } catch (err) {
      void err
      toast.error(t('builder.photo.removeFailed'))
    } finally {
      setPhotoRemoving(false)
    }
  }, [acceptServerDraft, draftId, flushDraft, t])

  // ─────────────────────────── 渲染辅助 ───────────────────────────
  const sectionLabel = useCallback(
    (section: DraftSection): string => {
      const key = `builder.section.${section.section_type}`
      const label = t(key)
      return label === key ? section.title : label
    },
    [t],
  )

  const radarData = useMemo(() => {
    if (!score) return []
    return score.dimension_scores.map((d) => ({ name: d.name, score: d.score }))
  }, [score])

  // 当前展示的评分是否基于旧版本简历（评分后内容又发生了变化）
  const isScoreStale = Boolean(
    score?.scored_revision != null && draft && score.scored_revision !== draft.revision,
  )

  const togglePreviewFullscreen = useCallback(async () => {
    const element = previewElementRef.current
    if (!element) return

    if (!element.requestFullscreen) {
      toast.error(t('builder.fullscreenFailed'))
      return
    }

    try {
      if (document.fullscreenElement === element) {
        await document.exitFullscreen()
        return
      }
      if (document.fullscreenElement) await document.exitFullscreen()
      await element.requestFullscreen()
    } catch (err) {
      void err
      toast.error(t('builder.fullscreenFailed'))
    }
  }, [t])

  // 预览缩放：fit 模式按画布宽度自适应；手动模式用固定倍率（0.2 ~ 2）
  const fitScale =
    previewBox.width > 0
      ? Math.min(2, Math.max(0.2, (previewBox.width - PREVIEW_PADDING * 2) / A4_WIDTH))
      : 1
  // 全屏时自动适配不放大超过 100%，保持标准 A4 CSS 尺寸；手动缩放仍按用户选择执行
  const previewScale =
    zoom === 'fit' ? (isPreviewFullscreen ? Math.min(1, fitScale) : fitScale) : zoom
  const previewViewH = Math.max(previewBox.height - PREVIEW_PADDING * 2, 200)

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-12 w-full" />
        <div className="flex gap-4">
          <Skeleton className="hidden h-96 w-56 shrink-0 lg:block" />
          <Skeleton className="h-96 flex-1" />
        </div>
      </div>
    )
  }

  if (error || !draft) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <h1 className="text-3xl font-black">{t('builder.title')}</h1>
        <Alert variant="destructive">
          <CircleAlert />
          <AlertDescription>{error ?? t('builder.loadFailed')}</AlertDescription>
        </Alert>
        <Button variant="neutral" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </Button>
      </div>
    )
  }

  // 抽屉当前编辑的 section（仅当 activePanel 为下标时）
  const activeSection = typeof activePanel === 'number' ? draft.sections[activePanel] : null

  return (
    <div className="flex h-full min-h-[560px] flex-col gap-3">
      {/* 顶栏（右侧 pr-14 给固定定位的导航切换按钮留出空间） */}
      <div className="flex flex-wrap items-center gap-2 rounded-base border-2 border-border bg-background p-3 pr-14 shadow-shadow">
        <Button variant="neutral" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Input
          value={draft.title}
          onChange={(e) => mutate((prev) => ({ ...prev, title: e.target.value }))}
          className="w-48"
        />
        <Button
          type="button"
          variant="neutral"
          size="icon"
          aria-label={editorVisible ? t('builder.hideEditor') : t('builder.showEditor')}
          aria-pressed={editorVisible}
          title={editorVisible ? t('builder.hideEditor') : t('builder.showEditor')}
          onClick={() => setEditorVisible((visible) => !visible)}
        >
          {editorVisible ? (
            <PanelLeftClose className="h-4 w-4" />
          ) : (
            <PanelLeftOpen className="h-4 w-4" />
          )}
        </Button>
        <BuilderSaveStatus
          status={saveStatus}
          conflictMessage={saveConflictMessage}
          onReload={() => void reloadDraft().catch(() => undefined)}
        />

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <div className="flex items-center" role="group" aria-label={t('builder.pagination')}>
            <Button
              variant={draft.layout_policy.mode === 'auto_pages' ? 'default' : 'neutral'}
              onClick={() => changeLayoutMode('auto_pages')}
              className="rounded-r-none"
            >
              {t('builder.autoPages')}
            </Button>
            <Button
              variant={draft.layout_policy.mode === 'target_pages' ? 'default' : 'neutral'}
              onClick={() => changeLayoutMode('target_pages')}
              className="rounded-l-none border-l-0"
            >
              {t('builder.targetPages')}
            </Button>
          </div>
          {draft.layout_policy.mode === 'target_pages' && (
            <div className="flex items-center gap-1.5">
              <Input
                type="number"
                min={1}
                max={10}
                step={1}
                inputMode="numeric"
                aria-label={t('builder.targetPageCount')}
                value={draft.layout_policy.target_page_count ?? 1}
                onChange={(event) => {
                  const value = event.currentTarget.valueAsNumber
                  if (Number.isInteger(value) && value >= 1 && value <= 10) {
                    changeTargetPageCount(value)
                  }
                }}
                onBlur={(event) => {
                  const value = event.currentTarget.valueAsNumber
                  if (!Number.isInteger(value) || value < 1 || value > 10) {
                    event.currentTarget.value = String(
                      draft.layout_policy.target_page_count ?? 1,
                    )
                  }
                }}
                className="h-9 w-20 text-center"
              />
              <span className="text-sm font-heading">{t('builder.pageUnit')}</span>
            </div>
          )}

          <Button variant="neutral" onClick={polishAll} disabled={polishingAll}>
            {polishingAll ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {t('builder.polishAll')}
            {llmBlocked && (
              <span className="text-xs font-base text-red-700">
                {t('llmGate.notConfiguredShort')}
              </span>
            )}
          </Button>

          <Button variant="neutral" onClick={doScore} disabled={scoring}>
            {scoring ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BarChart3 className="h-4 w-4" />
            )}
            {savedScore ? t('builder.lastScore') : t('builder.score')}
            {llmBlocked && (
              <span className="text-xs font-base text-red-700">
                {t('llmGate.notConfiguredShort')}
              </span>
            )}
          </Button>

          <Button onClick={openExportPreview} disabled={exporting}>
            <Download className="h-4 w-4" />
            {t('builder.export')}
          </Button>
        </div>
      </div>

      {/* LLM 未就绪时的常驻提示：弹窗关闭后仍可从这里重新打开配置 */}
      {llmBlocked && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>{t('llmGate.title')}</AlertTitle>
          <AlertDescription>
            {t('llmGate.builderDescription')}{' '}
            <button
              type="button"
              onClick={() => setGateOpen(true)}
              className="font-bold underline"
            >
              {t('llmGate.configureNow')}
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* 工作台：左侧板块导航 / 右侧大预览 */}
      <div className="flex min-h-0 flex-1 flex-col gap-3 lg:flex-row">
        {editorVisible && (
          <>
            {/* 左：模式切换 + 板块导航（填写模式）/ AI 助手对话（助手模式） */}
            <aside
              className={`flex shrink-0 flex-col gap-2 p-1 lg:min-h-0 ${
                editorMode === 'assistant' ? 'lg:w-[420px]' : 'lg:w-56'
              }`}
            >
              {/* 填写模式 / AI 助手模式自由切换 */}
              <div className="flex shrink-0 gap-1 rounded-base border-2 border-border bg-white p-1 shadow-shadow">
                <button
                  type="button"
                  onClick={() => setEditorMode('form')}
                  aria-pressed={editorMode === 'form'}
                  className={`flex-1 rounded-sm px-2 py-1 text-xs font-heading transition-colors ${
                    editorMode === 'form' ? 'bg-main' : 'hover:bg-main/40'
                  }`}
                >
                  {t('builder.modeFill')}
                </button>
                <button
                  type="button"
                  onClick={() => setEditorMode('assistant')}
                  aria-pressed={editorMode === 'assistant'}
                  className={`flex flex-1 items-center justify-center gap-1 rounded-sm px-2 py-1 text-xs font-heading transition-colors ${
                    editorMode === 'assistant' ? 'bg-main' : 'hover:bg-main/40'
                  }`}
                >
                  <Bot className="h-3.5 w-3.5 shrink-0" />
                  {t('builder.modeAssistant')}
                </button>
              </div>
              {editorMode === 'assistant' ? (
                <section className="flex min-h-[60vh] flex-1 flex-col overflow-hidden rounded-base border-2 border-border bg-background shadow-shadow lg:min-h-0">
                  <div className="flex shrink-0 items-center gap-2 border-b-2 border-border p-3">
                    <h2 className="min-w-0 flex-1 truncate font-heading text-lg">
                      {t('builder.assistant.title')}
                    </h2>
                    <span
                      className={`h-2 w-2 shrink-0 rounded-full border border-black ${
                        llmReady ? 'bg-green-500' : 'bg-red-400'
                      }`}
                      title={t(llmReady ? 'builder.assistant.ready' : 'builder.assistant.notReady')}
                    />
                  </div>
                  <div className="flex min-h-0 flex-1 overflow-hidden">
                    {draftId && (
                      <ResumeAssistantPanel
                        draftId={draftId}
                        revision={draft.revision}
                        llmReady={llmReady}
                        modelLabel={activeLlmModel}
                        ensureLlmReady={ensureLlmReady}
                        flushDraft={flushDraft}
                        onDraftChanged={acceptServerDraft}
                        onConflict={reloadDraft}
                      />
                    )}
                  </div>
                </section>
              ) : (
              <div className="flex min-h-0 flex-1 flex-row gap-2 overflow-x-auto lg:flex-col lg:overflow-x-hidden lg:overflow-y-auto lg:pr-1">
                <p className="hidden shrink-0 text-xs font-heading text-gray-500 lg:block">
                  {t('builder.blocks')}
                </p>
              <button
                type="button"
                onClick={() => togglePanel('style')}
                aria-pressed={activePanel === 'style'}
                className={`${SIDEBAR_ITEM_CLASS} ${activePanel === 'style' ? 'bg-main' : 'bg-white'}`}
              >
                <Palette className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate text-left">{t('builder.design')}</span>
              </button>
              <button
                type="button"
                onClick={() => togglePanel('photo')}
                aria-pressed={activePanel === 'photo'}
                className={`${SIDEBAR_ITEM_CLASS} ${activePanel === 'photo' ? 'bg-main' : 'bg-white'}`}
              >
                <Camera className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate text-left">{t('builder.photo.title')}</span>
                {draft.identity.photo && <Check className="h-3.5 w-3.5 shrink-0 text-green-700" />}
              </button>
              <button
                type="button"
                onClick={() => togglePanel('summary')}
                aria-pressed={activePanel === 'summary'}
                className={`${SIDEBAR_ITEM_CLASS} ${activePanel === 'summary' ? 'bg-main' : 'bg-white'}`}
              >
                <FileText className="h-4 w-4 shrink-0" />
                <span className="flex-1 truncate text-left">{t('builder.summary')}</span>
                {Boolean(draft.summary?.trim()) && (
                  <Check className="h-3.5 w-3.5 shrink-0 text-green-700" />
                )}
              </button>
              {draft.sections.map((section, si) => (
                <button
                  key={section.section_id}
                  type="button"
                  onClick={() => togglePanel(si)}
                  aria-pressed={activePanel === si}
                  className={`${SIDEBAR_ITEM_CLASS} ${activePanel === si ? 'bg-main' : 'bg-white'} ${
                    section.visible ? '' : 'opacity-50'
                  }`}
                >
                  <span className="flex-1 truncate text-left">{sectionLabel(section)}</span>
                  <Badge variant="neutral">{section.items.length}</Badge>
                  {!section.visible && <EyeOff className="h-3.5 w-3.5 shrink-0 text-gray-500" />}
                </button>
              ))}
              </div>
              )}
            </aside>

            {/* 中：内嵌编辑面板，与预览并排，编辑时预览实时可见 */}
            {activePanel !== null && (
              <section
                className="flex min-h-0 w-full shrink-0 flex-col overflow-hidden rounded-base border-2 border-border bg-background shadow-shadow lg:w-[400px]"
              >
            <div className="flex shrink-0 items-center gap-2 border-b-2 border-border p-3">
              <h2 className="min-w-0 flex-1 truncate font-heading text-lg">
                {activePanel === 'style'
                  ? t('builder.design')
                  : activePanel === 'photo'
                    ? t('builder.photo.title')
                    : activePanel === 'summary'
                      ? t('builder.summary')
                      : activeSection
                        ? sectionLabel(activeSection)
                        : ''}
              </h2>
              {typeof activePanel === 'number' && activeSection && (
                <div className="flex items-center gap-1">
                  <Button
                    variant="neutral"
                    size="icon"
                    title={activeSection.visible ? t('builder.hidden') : t('builder.visible')}
                    onClick={() =>
                      updateSection(activePanel, { visible: !activeSection.visible })
                    }
                  >
                    {activeSection.visible ? (
                      <Eye className="h-4 w-4" />
                    ) : (
                      <EyeOff className="h-4 w-4" />
                    )}
                  </Button>
                  <Button
                    variant="neutral"
                    size="icon"
                    title={t('builder.moveUp')}
                    disabled={activePanel === 0}
                    onClick={() => moveSection(activePanel, -1)}
                  >
                    <ChevronUp className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="neutral"
                    size="icon"
                    title={t('builder.moveDown')}
                    disabled={activePanel === draft.sections.length - 1}
                    onClick={() => moveSection(activePanel, 1)}
                  >
                    <ChevronDown className="h-4 w-4" />
                  </Button>
                </div>
              )}
              <button onClick={() => setActivePanel(null)} aria-label={t('common.close')}>
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="min-h-0 flex-1 overflow-y-auto p-4">
            {/* 样式美化面板：模板 / 密度 / 主题色 / 字体 / 页边距 / 自定义 CSS */}
            {activePanel === 'style' && (
              <div className="space-y-4">
                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.template')}</label>
                  <select
                    className={`${SELECT_CLASS} w-full`}
                    value={draft.template_id}
                    onChange={(e) => changeTemplate(e.target.value as TemplateId)}
                  >
                    {TEMPLATES.map((id) => (
                      <option key={id} value={id}>
                        {t(`builder.template_${id}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.density')}</label>
                  <select
                    className={`${SELECT_CLASS} w-full`}
                    value={draft.design_tokens.density}
                    onChange={(e) => updateTokens({ density: e.target.value as LayoutDensity })}
                  >
                    {DENSITIES.map((id) => (
                      <option key={id} value={id}>
                        {t(`builder.density_${id}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.accentColor')}</label>
                  <div className="flex flex-wrap items-center gap-2">
                    {ACCENT_PRESETS.map((color) => (
                      <button
                        key={color}
                        type="button"
                        aria-label={color}
                        title={color}
                        onClick={() => updateTokens({ accent_color: color })}
                        className={`h-7 w-7 rounded-base border-2 ${
                          draft.design_tokens.accent_color === color
                            ? 'border-black ring-2 ring-black/40'
                            : 'border-border'
                        }`}
                        style={{ backgroundColor: color }}
                      />
                    ))}
                    {/* 自定义取色：拖动时连续触发，走防抖保存 */}
                    <input
                      type="color"
                      value={
                        /^#[0-9a-fA-F]{6}$/.test(draft.design_tokens.accent_color)
                          ? draft.design_tokens.accent_color
                          : '#2563eb'
                      }
                      onChange={(e) => updateTokens({ accent_color: e.target.value }, false)}
                      className="h-7 w-10 cursor-pointer rounded-base border-2 border-border bg-white p-0.5"
                      title={t('builder.accentColor')}
                    />
                  </div>
                </div>

                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.fontFamily')}</label>
                  <select
                    className={`${SELECT_CLASS} w-full`}
                    value={draft.design_tokens.font_family}
                    onChange={(e) => updateTokens({ font_family: e.target.value })}
                  >
                    {!FONT_OPTIONS.some((f) => f.value === draft.design_tokens.font_family) && (
                      <option value={draft.design_tokens.font_family}>
                        {t('builder.customOption')}
                      </option>
                    )}
                    {FONT_OPTIONS.map((f) => (
                      <option key={f.key} value={f.value}>
                        {t(`builder.font_${f.key}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.pageMargin')}</label>
                  <select
                    className={`${SELECT_CLASS} w-full`}
                    value={draft.design_tokens.page_margin}
                    onChange={(e) => updateTokens({ page_margin: e.target.value })}
                  >
                    {!MARGIN_OPTIONS.some((m) => m.value === draft.design_tokens.page_margin) && (
                      <option value={draft.design_tokens.page_margin}>
                        {t('builder.customOption')}
                      </option>
                    )}
                    {MARGIN_OPTIONS.map((m) => (
                      <option key={m.key} value={m.value}>
                        {t(`builder.margin_${m.key}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className={FIELD_LABEL_CLASS}>{t('builder.customCss')}</label>
                  <textarea
                    className="min-h-44 w-full rounded-base border-2 border-border bg-white p-2 font-mono text-xs shadow-shadow focus:outline-none"
                    value={draft.design_tokens.custom_css ?? ''}
                    placeholder={'.name { color: var(--accent); }\n.section-title { border-bottom: 2px solid var(--accent); }'}
                    spellCheck={false}
                    onChange={(e) => updateTokens({ custom_css: e.target.value }, false)}
                  />
                  <p className="mt-1 text-xs text-gray-500">{t('builder.customCssHint')}</p>
                </div>
              </div>
            )}

            {/* 证件照面板：空 / 加载 / 成功（待确认 · 已确认） / 失败 四态 */}
            {activePanel === 'photo' && (
              <div className="space-y-3">
                <label className="flex items-center gap-1 text-sm">
                  {t('builder.photo.bgColor')}
                  <select
                    className={SELECT_CLASS}
                    value={photoBg}
                    disabled={photoUploading}
                    onChange={(e) => changePhotoBg(e.target.value as PhotoBgColor)}
                  >
                    {PHOTO_BGS.map((bg) => (
                      <option key={bg} value={bg}>
                        {t(`builder.photo.bg_${bg}`)}
                      </option>
                    ))}
                  </select>
                </label>

                <input
                  ref={photoInputRef}
                  type="file"
                  accept="image/jpeg,image/png"
                  className="hidden"
                  onChange={onPhotoSelected}
                />

                {photoUploading ? (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    {t('builder.photo.uploading')}
                  </div>
                ) : photoResult ? (
                  <div className="space-y-3">
                    <div className="flex gap-4">
                      <figure className="space-y-1">
                        <img
                          src={photoResult.original_url}
                          alt={t('builder.photo.original')}
                          className="h-32 rounded-base border-2 border-border object-cover"
                        />
                        <figcaption className="text-center text-xs text-gray-500">
                          {t('builder.photo.original')}
                        </figcaption>
                      </figure>
                      <figure className="space-y-1">
                        <img
                          src={photoResult.processed_url}
                          alt={t('builder.photo.processed')}
                          className="h-32 rounded-base border-2 border-border object-cover"
                        />
                        <figcaption className="text-center text-xs text-gray-500">
                          {t('builder.photo.processed')}
                        </figcaption>
                      </figure>
                    </div>
                    {!photoResult.background_replaced && (
                      <p className="text-xs text-amber-700">
                        {t('builder.photo.degraded', {
                          reason: photoResult.degraded_reason ?? '-',
                        })}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2">
                      <Button size="sm" onClick={doConfirmPhoto} disabled={photoConfirming}>
                        {photoConfirming ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Check className="h-3 w-3" />
                        )}
                        {photoConfirming
                          ? t('builder.photo.confirming')
                          : t('builder.photo.confirm')}
                      </Button>
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={() => photoInputRef.current?.click()}
                      >
                        <Camera className="h-3 w-3" />
                        {t('builder.photo.reupload')}
                      </Button>
                    </div>
                  </div>
                ) : draft.identity.photo ? (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-600">{t('builder.photo.confirmed')}</p>
                    <div className="flex flex-wrap gap-2">
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={() => photoInputRef.current?.click()}
                      >
                        <Camera className="h-3 w-3" />
                        {t('builder.photo.reupload')}
                      </Button>
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={doRemovePhoto}
                        disabled={photoRemoving}
                      >
                        {photoRemoving ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Trash2 className="h-3 w-3" />
                        )}
                        {photoRemoving
                          ? t('builder.photo.removing')
                          : t('builder.photo.remove')}
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="space-y-2">
                    <p className="text-sm text-gray-500">{t('builder.photo.empty')}</p>
                    <Button
                      variant="neutral"
                      size="sm"
                      onClick={() => photoInputRef.current?.click()}
                    >
                      <Camera className="h-3 w-3" />
                      {t('builder.photo.choose')}
                    </Button>
                  </div>
                )}

                {photoError && (
                  <Alert variant="destructive">
                    <CircleAlert />
                    <AlertDescription>{photoError}</AlertDescription>
                  </Alert>
                )}
              </div>
            )}

            {/* 个人简介面板 */}
            {activePanel === 'summary' && (
              <textarea
                className="min-h-48 w-full rounded-base border-2 border-border bg-white p-2 text-sm shadow-shadow focus:outline-none"
                value={draft.summary ?? ''}
                placeholder={t('builder.summaryPlaceholder')}
                onChange={(e) => mutate((prev) => ({ ...prev, summary: e.target.value }))}
              />
            )}

            {/* section 条目编辑面板 */}
            {typeof activePanel === 'number' && activeSection && (
              <div className="space-y-3">
                {activeSection.items.map((item, ii) => (
                  <div
                    key={item.item_id}
                    className="space-y-2 rounded-base border-2 border-border bg-white/60 p-3"
                  >
                    <p className="text-xs font-heading text-gray-400">
                      {t('builder.itemN', { n: ii + 1 })}
                    </p>
                    <div>
                      <label className={FIELD_LABEL_CLASS}>{t('builder.heading')}</label>
                      <Input
                        value={item.heading ?? ''}
                        placeholder={t('builder.headingPlaceholder')}
                        onChange={(e) =>
                          updateItem(activePanel, ii, { heading: e.target.value })
                        }
                      />
                    </div>
                    <div className="grid gap-2 sm:grid-cols-2">
                      <div>
                        <label className={FIELD_LABEL_CLASS}>{t('builder.subheading')}</label>
                        <Input
                          value={item.subheading ?? ''}
                          placeholder={t('builder.subheadingPlaceholder')}
                          onChange={(e) =>
                            updateItem(activePanel, ii, { subheading: e.target.value })
                          }
                        />
                      </div>
                      <div>
                        <label className={FIELD_LABEL_CLASS}>{t('builder.dateRange')}</label>
                        <Input
                          value={item.date_range ?? ''}
                          placeholder={t('builder.dateRangePlaceholder')}
                          onChange={(e) =>
                            updateItem(activePanel, ii, { date_range: e.target.value })
                          }
                        />
                      </div>
                    </div>

                    <label className={FIELD_LABEL_CLASS}>{t('builder.bullets')}</label>
                    {item.bullets.map((bullet, bi) => (
                      <div key={bi} className="flex items-start gap-2">
                        <textarea
                          className="min-h-10 flex-1 rounded-base border-2 border-border bg-white p-2 text-sm shadow-shadow focus:outline-none"
                          value={bullet}
                          placeholder={t('builder.bulletPlaceholder')}
                          onChange={(e) => updateBullet(activePanel, ii, bi, e.target.value)}
                        />
                        <Button
                          variant="neutral"
                          size="icon"
                          title={t('builder.removeBullet')}
                          onClick={() => removeBullet(activePanel, ii, bi)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}

                    <div className="flex flex-wrap items-center gap-2">
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={() => addBullet(activePanel, ii)}
                      >
                        <Plus className="h-3 w-3" />
                        {t('builder.addBullet')}
                      </Button>
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={() => openPolish(activePanel, ii)}
                        disabled={polishingKey === `${activePanel}-${ii}`}
                      >
                        {polishingKey === `${activePanel}-${ii}` ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Sparkles className="h-3 w-3" />
                        )}
                        {t('builder.polish')}
                      </Button>
                      <Button
                        variant="neutral"
                        size="sm"
                        className="ml-auto"
                        title={t('builder.removeItem')}
                        onClick={() => removeItem(activePanel, ii)}
                      >
                        <Trash2 className="h-3 w-3" />
                        {t('builder.removeItem')}
                      </Button>
                    </div>
                  </div>
                ))}

                <Button variant="neutral" size="sm" onClick={() => addItem(activePanel)}>
                  <Plus className="h-3 w-3" />
                  {t('builder.addItem')}
                </Button>
              </div>
            )}
            </div>
              </section>
            )}
          </>
        )}

        {/* 右：A4 预览画布，白纸等比缩放 + 右下角缩放控件 */}
        <div
          ref={previewBoxRef}
          className={`relative min-h-[60vh] min-w-0 flex-1 overflow-hidden bg-zinc-300 lg:min-h-0 ${
            isPreviewFullscreen
              ? 'rounded-none border-0 shadow-none'
              : 'rounded-base border-2 border-border shadow-shadow'
          }`}
        >
          <div className="h-full overflow-auto" style={{ padding: PREVIEW_PADDING }}>
            <div
              className="relative mx-auto"
              style={{ width: A4_WIDTH * previewScale, height: previewViewH }}
            >
              {/* iframe 固定 A4 宽度，transform 等比缩放；页面内容在 iframe 内部滚动 */}
              {!exportPreviewOpen && (
                <iframe
                  key={src}
                  src={src}
                  title={t('builder.preview')}
                  className="border-0 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,0.35)]"
                  style={{
                    width: A4_WIDTH,
                    height: previewViewH / previewScale,
                    transform: `scale(${previewScale})`,
                    transformOrigin: 'top left',
                  }}
                  onLoad={() => setPreviewLoading(false)}
                />
              )}
              {/* 预览加载占位：避免 src 切换期间出现空白白纸被误认为卡顿 */}
              {!exportPreviewOpen && previewLoading && (
                <div
                  className="absolute inset-0 flex flex-col bg-white p-8 shadow-[4px_4px_0_0_rgba(0,0,0,0.35)]"
                  aria-busy="true"
                  aria-label={t('builder.previewLoading')}
                >
                  <Skeleton className="h-7 w-1/3" />
                  <Skeleton className="mt-2 h-4 w-1/2" />
                  <div className="mt-6 space-y-2.5">
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-11/12" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-4/5" />
                  </div>
                  <div className="mt-6 space-y-2.5">
                    <Skeleton className="h-4 w-2/3" />
                    <Skeleton className="h-4 w-full" />
                    <Skeleton className="h-4 w-10/12" />
                  </div>
                  <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
                    <Loader2 className="size-4 animate-spin" />
                    {t('builder.previewLoading')}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 缩放控件 */}
          <div className="absolute right-3 bottom-3 z-10 flex items-center gap-1 rounded-base border-2 border-border bg-background px-1.5 py-1 shadow-shadow">
            <Button
              variant="neutral"
              size="icon"
              className="h-7 w-7"
              title={t('builder.zoomOut')}
              onClick={() => setZoom(Math.max(0.2, Math.round((previewScale - 0.1) * 10) / 10))}
            >
              <ZoomOut className="h-3.5 w-3.5" />
            </Button>
            <span className="w-10 text-center text-xs font-heading">
              {Math.round(previewScale * 100)}%
            </span>
            <Button
              variant="neutral"
              size="icon"
              className="h-7 w-7"
              title={t('builder.zoomIn')}
              onClick={() => setZoom(Math.min(2, Math.round((previewScale + 0.1) * 10) / 10))}
            >
              <ZoomIn className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant={zoom === 'fit' ? 'default' : 'neutral'}
              size="icon"
              className="h-7 w-7"
              title={t('builder.zoomFit')}
              onClick={() => setZoom('fit')}
            >
              <Maximize className="h-3.5 w-3.5" />
            </Button>
            <Button
              type="button"
              variant={isPreviewFullscreen ? 'default' : 'neutral'}
              size="icon"
              className="h-7 w-7"
              aria-label={
                isPreviewFullscreen ? t('builder.exitFullscreen') : t('builder.fullscreen')
              }
              title={isPreviewFullscreen ? t('builder.exitFullscreen') : t('builder.fullscreen')}
              onClick={() => void togglePreviewFullscreen()}
            >
              {isPreviewFullscreen ? (
                <Minimize2 className="h-3.5 w-3.5" />
              ) : (
                <Maximize2 className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>
      </div>

      {/* 润色 diff 弹窗 */}
      {polishTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setPolishTarget(null)} />
          <div className="relative z-10 mx-4 max-h-[80vh] w-full max-w-2xl overflow-auto rounded-base border-2 border-border bg-background p-6 shadow-shadow">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-heading text-xl">{t('builder.polishTitle')}</h2>
              <button onClick={() => setPolishTarget(null)} aria-label={t('common.close')}>
                <X className="h-5 w-5" />
              </button>
            </div>
            {polishTarget.result.polished_items.length === 0 ? (
              <p className="text-sm text-gray-500">{t('builder.noChanges')}</p>
            ) : (
              <div className="space-y-4">
                {polishTarget.result.polished_items.map((polished, p) => (
                  <div key={p} className="rounded-base border-2 border-border p-3">
                    <p className="mb-1 text-xs font-heading text-gray-500">
                      {t('builder.original')}
                    </p>
                    <p className="mb-2 text-sm text-gray-600 line-through">
                      {polishTarget.result.original_items[p]}
                    </p>
                    <p className="mb-1 text-xs font-heading text-green-700">
                      {t('builder.polished')}
                    </p>
                    <p className="mb-2 text-sm">{polished}</p>
                    <Button
                      size="sm"
                      variant={polishTarget.accepted[p] ? 'neutral' : 'default'}
                      disabled={polishTarget.accepted[p]}
                      onClick={() => applyPolish(p)}
                    >
                      <Check className="h-3 w-3" />
                      {t('builder.accept')}
                    </Button>
                  </div>
                ))}
                {polishTarget.result.notes && (
                  <p className="text-xs italic text-gray-500">{polishTarget.result.notes}</p>
                )}
                <div className="flex justify-end gap-2">
                  <Button variant="neutral" onClick={() => setPolishTarget(null)}>
                    {t('common.close')}
                  </Button>
                  <Button onClick={() => applyPolish()}>{t('builder.acceptAll')}</Button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI 评分报告抽屉：总分 + 雷达图 + 可折叠的优劣势/建议/风险/面试官视角/维度详情 */}
      {scoreOpen && score && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setScoreOpen(false)} />
          <div className="relative z-10 h-full w-full max-w-md overflow-auto border-l-2 border-border bg-background p-6 shadow-shadow">
            <div className="mb-4 flex items-center justify-between gap-2">
              <h2 className="font-heading text-xl">{t('builder.score')}</h2>
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="neutral"
                  disabled={scoring}
                  onClick={() => {
                    setScoreOpen(false)
                    void runScoring()
                  }}
                >
                  {scoring ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <RefreshCw className="h-4 w-4" />
                  )}
                  {t('builder.rescore')}
                </Button>
                <button onClick={() => setScoreOpen(false)} aria-label={t('common.close')}>
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>
            <div className="mb-2 flex items-center gap-3">
              <span className="text-4xl font-black">{score.overall_score}</span>
              <span className="text-sm text-gray-500">{t('builder.scoreOverall')}</span>
            </div>
            {score.scored_at && (
              <p className="mb-2 text-xs text-gray-500">
                {t('builder.scoredAt', { time: new Date(score.scored_at).toLocaleString() })}
              </p>
            )}
            {isScoreStale && (
              <Alert className="mb-3">
                <CircleAlert />
                <AlertDescription>{t('builder.staleScoreHint')}</AlertDescription>
              </Alert>
            )}
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                  <PolarGrid stroke="#000" strokeWidth={1} />
                  <PolarAngleAxis
                    dataKey="name"
                    tick={{ fontSize: 11, fontWeight: 700, fill: '#000' }}
                  />
                  <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10, fill: '#666' }} />
                  <Radar
                    dataKey="score"
                    stroke="#88aaee"
                    fill="#88aaee"
                    fillOpacity={0.4}
                    strokeWidth={2}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <Accordion type="multiple" defaultValue={['summary']} className="mt-4 space-y-2">
              {score.summary && (
                <AccordionItem value="summary">
                  <AccordionTrigger>{t('builder.scoreSummaryTitle')}</AccordionTrigger>
                  <AccordionContent>
                    <p className="text-sm text-gray-700">{score.summary}</p>
                  </AccordionContent>
                </AccordionItem>
              )}
              <AccordionItem value="strengths">
                <AccordionTrigger>{t('builder.scoreStrengths')}</AccordionTrigger>
                <AccordionContent>
                  {score.strengths && score.strengths.length > 0 ? (
                    <ul className="space-y-2">
                      {score.strengths.map((item, idx) => (
                        <li key={idx} className="text-sm">
                          <p className="font-bold">{item.point}</p>
                          {item.evidence && (
                            <p className="mt-0.5 text-xs text-gray-600">
                              {t('builder.scoreEvidence')}：{item.evidence}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">{t('builder.scoreNoStrengths')}</p>
                  )}
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="improvements">
                <AccordionTrigger>{t('builder.scoreImprovements')}</AccordionTrigger>
                <AccordionContent>
                  {score.improvements && score.improvements.length > 0 ? (
                    <div className="space-y-3">
                      {score.improvements.map((item, idx) => (
                        <div
                          key={idx}
                          className="rounded-base border-2 border-border bg-white p-3 shadow-shadow"
                        >
                          <p className="text-sm font-bold">{item.point}</p>
                          {item.detail && (
                            <p className="mt-1 text-xs text-gray-600">{item.detail}</p>
                          )}
                          <Button
                            size="sm"
                            variant="neutral"
                            className="mt-2"
                            disabled={adoptingIdx !== null}
                            onClick={() => void adoptSuggestion(item, idx)}
                          >
                            {adoptingIdx === idx ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Sparkles className="h-3 w-3" />
                            )}
                            {adoptingIdx === idx
                              ? t('builder.adoptingSuggestion')
                              : t('builder.adoptSuggestion')}
                          </Button>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-gray-500">{t('builder.scoreNoImprovements')}</p>
                  )}
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="risks">
                <AccordionTrigger>{t('builder.scoreRisks')}</AccordionTrigger>
                <AccordionContent>
                  {score.risks && score.risks.length > 0 ? (
                    <ul className="space-y-2">
                      {score.risks.map((item, idx) => (
                        <li key={idx} className="text-sm">
                          <div className="flex items-center gap-2">
                            <p className="font-bold">{item.point}</p>
                            {item.severity && (
                              <Badge
                                variant="neutral"
                                className={
                                  item.severity === 'high'
                                    ? 'bg-red-400 text-red-900 border-red-700'
                                    : undefined
                                }
                              >
                                {t(`builder.risk_${item.severity}`, {
                                  defaultValue: item.severity,
                                })}
                              </Badge>
                            )}
                          </div>
                          {item.evidence && (
                            <p className="mt-0.5 text-xs text-gray-600">
                              {t('builder.scoreEvidence')}：{item.evidence}
                            </p>
                          )}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-500">{t('builder.scoreNoRisks')}</p>
                  )}
                </AccordionContent>
              </AccordionItem>
              {score.interview_suggestions && (
                <AccordionItem value="interview">
                  <AccordionTrigger>{t('builder.scoreInterviewTips')}</AccordionTrigger>
                  <AccordionContent>
                    <div className="space-y-3 text-sm">
                      {(score.interview_suggestions.worth_asking?.length ?? 0) > 0 && (
                        <div>
                          <p className="font-bold">{t('builder.scoreWorthAsking')}</p>
                          <ul className="mt-1 list-disc pl-5 text-gray-700">
                            {score.interview_suggestions.worth_asking?.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(score.interview_suggestions.suspicious?.length ?? 0) > 0 && (
                        <div>
                          <p className="font-bold">{t('builder.scoreSuspicious')}</p>
                          <ul className="mt-1 list-disc pl-5 text-gray-700">
                            {score.interview_suggestions.suspicious?.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(score.interview_suggestions.verify_direction?.length ?? 0) > 0 && (
                        <div>
                          <p className="font-bold">{t('builder.scoreVerifyDirection')}</p>
                          <ul className="mt-1 list-disc pl-5 text-gray-700">
                            {score.interview_suggestions.verify_direction?.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                      {(score.interview_suggestions.skip?.length ?? 0) > 0 && (
                        <div>
                          <p className="font-bold">{t('builder.scoreSkip')}</p>
                          <ul className="mt-1 list-disc pl-5 text-gray-700">
                            {score.interview_suggestions.skip?.map((item, idx) => (
                              <li key={idx}>{item}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  </AccordionContent>
                </AccordionItem>
              )}
              <AccordionItem value="dimensions">
                <AccordionTrigger>{t('builder.scoreDimensionDetail')}</AccordionTrigger>
                <AccordionContent>
                  <div className="space-y-3">
                    {score.dimension_scores.map((d) => (
                      <div key={d.name} className="text-sm">
                        <div className="flex items-center justify-between">
                          <span className="font-bold">{d.name}</span>
                          <Badge variant="neutral">{d.score}</Badge>
                        </div>
                        {d.reason && <p className="mt-1 text-xs text-gray-600">{d.reason}</p>}
                        {d.evidence && (
                          <p className="mt-0.5 text-xs text-gray-500">
                            {t('builder.scoreEvidence')}：{d.evidence}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </div>
        </div>
      )}

      {/* 评分进度弹窗：运行中不可关闭，完成后短暂展示再打开报告 */}
      <Dialog
        open={scoreProgress !== 'closed'}
        onOpenChange={(next) => {
          if (!next && scoreProgress === 'done') setScoreProgress('closed')
        }}
      >
        <DialogContent
          className="max-w-sm"
          onInteractOutside={(e) => {
            if (scoreProgress === 'running') e.preventDefault()
          }}
          onEscapeKeyDown={(e) => {
            if (scoreProgress === 'running') e.preventDefault()
          }}
        >
          <DialogHeader>
            <DialogTitle>{t('builder.scoreProgressTitle')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-3 py-2">
            {scoreProgress === 'done' ? (
              <div className="flex items-center gap-2 text-sm font-bold text-green-700">
                <CircleCheck className="h-4 w-4 shrink-0" />
                {t('builder.scoreStepDone')}
              </div>
            ) : (
              SCORE_STEP_KEYS.map((key, idx) => (
                <div
                  key={key}
                  className={`flex items-center gap-2 text-sm ${
                    idx <= scoreStepIdx ? '' : 'opacity-40'
                  }`}
                >
                  {idx < scoreStepIdx ? (
                    <CircleCheck className="h-4 w-4 shrink-0 text-green-700" />
                  ) : idx === scoreStepIdx ? (
                    <Loader2 className="h-4 w-4 shrink-0 animate-spin" />
                  ) : (
                    <span className="h-4 w-4 shrink-0 rounded-full border-2 border-border" />
                  )}
                  {t(`builder.${key}`)}
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* 简历已更新时的重新评分确认 */}
      <Dialog open={rescoreDialogOpen} onOpenChange={setRescoreDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('builder.rescoreConfirmTitle')}</DialogTitle>
            <DialogDescription>{t('builder.rescoreConfirmDesc')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="neutral"
              onClick={() => {
                setRescoreDialogOpen(false)
                if (savedScore) {
                  setScore(savedScore)
                  setScoreOpen(true)
                }
              }}
            >
              {t('builder.viewLastScore')}
            </Button>
            <Button
              onClick={() => {
                setRescoreDialogOpen(false)
                void runScoring()
              }}
            >
              <RefreshCw className="h-4 w-4" />
              {t('builder.rescore')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* LLM 配置门禁弹窗：进入页面未就绪时自动弹出，AI 动作触发时也会拦截唤起 */}
      <LLMGateDialog
        open={gateOpen}
        onOpenChange={setGateOpen}
        description={t('llmGate.builderDescription')}
        successMessage={t('llmGate.readyToBuild')}
      />
      {exportPreviewOpen && (
        <ExportPreviewDialog
          open
          src={previewSrc}
          title={draft.title}
          exporting={exporting}
          onOpenChange={setExportPreviewOpen}
          onConfirm={doExport}
          placeholders={draft.privacy_placeholders}
          replacements={exportReplacements}
          onReplacementChange={(token, value) => {
            setExportReplacements((current) => ({ ...current, [token]: value }))
          }}
          onPrint={printPreview}
          onRetry={() => setPreviewRequestKey((key) => key + 1)}
        />
      )}
    </div>
  )
}
