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
} from 'lucide-react'

import {
  getDraft,
  updateDraft,
  polishSection,
  scoreDraft,
  exportDraftPdf,
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
  LayoutDensity,
  TemplateId,
  PolishResult,
  ScoreResult,
  UpdateDraftPayload,
  PhotoBgColor,
  PhotoUploadResult,
} from '@/types/builder'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Badge } from '@/components/ui/badge'

const TEMPLATES: TemplateId[] = ['classic', 'modern', 'compact']
const DENSITIES: LayoutDensity[] = ['loose', 'normal', 'tight', 'compact']
const PHOTO_BGS: PhotoBgColor[] = ['white', 'blue', 'red']
const PHOTO_ACCEPT_TYPES = ['image/jpeg', 'image/png']
const PHOTO_MAX_SIZE = 10 * 1024 * 1024

const SELECT_CLASS =
  'rounded-base border-2 border-border bg-white px-3 py-1.5 text-sm font-base shadow-shadow focus:outline-none'

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
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [previewNonce, setPreviewNonce] = useState(0)

  const [polishTarget, setPolishTarget] = useState<PolishTarget | null>(null)
  const [polishingKey, setPolishingKey] = useState<string | null>(null)
  const [polishingAll, setPolishingAll] = useState(false)
  const [scoring, setScoring] = useState(false)
  const [score, setScore] = useState<ScoreResult | null>(null)
  const [scoreOpen, setScoreOpen] = useState(false)
  const [exporting, setExporting] = useState(false)

  const [photoBg, setPhotoBg] = useState<PhotoBgColor>('white')
  const [photoUploading, setPhotoUploading] = useState(false)
  const [photoResult, setPhotoResult] = useState<PhotoUploadResult | null>(null)
  const [photoConfirming, setPhotoConfirming] = useState(false)
  const [photoRemoving, setPhotoRemoving] = useState(false)
  const [photoError, setPhotoError] = useState<string | null>(null)
  const photoInputRef = useRef<HTMLInputElement | null>(null)
  const photoFileRef = useRef<File | null>(null)

  const dirtyRef = useRef(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

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

  // ─────────────────────────── 保存 ───────────────────────────
  const buildPatch = useCallback((d: ResumeDraftData): UpdateDraftPayload => {
    return {
      title: d.title,
      identity: d.identity,
      summary: d.summary,
      sections: d.sections,
      template_id: d.template_id,
      design_tokens: d.design_tokens,
      auto_one_page: d.auto_one_page,
    }
  }, [])

  const persist = useCallback(
    async (d: ResumeDraftData) => {
      if (!draftId) return
      setSaveStatus('saving')
      try {
        const res = await updateDraft(draftId, buildPatch(d))
        if (res.code !== 0) {
          setSaveStatus('error')
          toast.error(res.message || t('builder.saveFailed'))
          return
        }
        setSaveStatus('saved')
        setPreviewNonce((n) => n + 1)
      } catch (err) {
        setSaveStatus('error')
        toast.error((err as Error).message || t('builder.saveFailed'))
      }
    },
    [draftId, buildPatch, t],
  )

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
            void persist(next)
          },
          immediate ? 0 : 700,
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
    },
    [mutate],
  )

  const addItem = useCallback(
    (sectionIdx: number) => {
      const empty: DraftItem = { heading: '', subheading: '', date_range: '', bullets: [''] }
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

  // ─────────────────────────── 顶栏设置 ───────────────────────────
  const changeTemplate = useCallback(
    (id: TemplateId) => mutate((prev) => ({ ...prev, template_id: id }), true),
    [mutate],
  )
  const changeDensity = useCallback(
    (density: LayoutDensity) =>
      mutate((prev) => ({ ...prev, design_tokens: { ...prev.design_tokens, density } }), true),
    [mutate],
  )
  const toggleAutoOnePage = useCallback(
    () => mutate((prev) => ({ ...prev, auto_one_page: !prev.auto_one_page }), true),
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
        toast.error(res.message || t('builder.polishFailed'))
        return null
      }
      return res.data
    },
    [draftId, draft, t],
  )

  const openPolish = useCallback(
    async (sectionIdx: number, itemIdx: number) => {
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
    [runPolish, t],
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
  }, [draft, runPolish, mutate, t])

  // ─────────────────────────── AI 打分 ───────────────────────────
  const doScore = useCallback(async () => {
    if (!draftId) return
    setScoring(true)
    try {
      const res = await scoreDraft(draftId)
      if (res.code !== 0) {
        toast.error(res.message || t('builder.scoreFailed'))
        return
      }
      setScore(res.data)
      setScoreOpen(true)
    } catch (err) {
      toast.error((err as Error).message || t('builder.scoreFailed'))
    } finally {
      setScoring(false)
    }
  }, [draftId, t])

  // ─────────────────────────── 导出 PDF ───────────────────────────
  const doExport = useCallback(async () => {
    if (!draftId || !draft) return
    setExporting(true)
    try {
      const { blob, overflow } = await exportDraftPdf(draftId, {
        auto_one_page: draft.auto_one_page,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${draft.title || 'resume'}.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      if (overflow) toast.warning(t('builder.exportOverflow'))
    } catch (err) {
      toast.error((err as Error).message || t('builder.exportFailed'))
    } finally {
      setExporting(false)
    }
  }, [draftId, draft, t])

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
      const data = await confirmPhoto(draftId, photoResult.processed_object)
      // 只合并服务端受控的 photo 字段，避免整体覆盖回滚未保存的本地编辑
      setDraft((prev) =>
        prev
          ? { ...prev, identity: { ...prev.identity, photo: data.identity.photo ?? null } }
          : data,
      )
      setPhotoResult(null)
      photoFileRef.current = null
      setPreviewNonce((n) => n + 1)
      toast.success(t('builder.photo.confirmed'))
    } catch (err) {
      void err
      toast.error(t('builder.photo.confirmFailed'))
    } finally {
      setPhotoConfirming(false)
    }
  }, [draftId, photoResult, t])

  const doRemovePhoto = useCallback(async () => {
    if (!draftId) return
    setPhotoRemoving(true)
    try {
      const data = await deletePhoto(draftId)
      // 同 confirm：仅同步 photo 字段，保留本地未保存的编辑
      setDraft((prev) =>
        prev
          ? { ...prev, identity: { ...prev.identity, photo: data.identity.photo ?? null } }
          : data,
      )
      setPreviewNonce((n) => n + 1)
    } catch (err) {
      void err
      toast.error(t('builder.photo.removeFailed'))
    } finally {
      setPhotoRemoving(false)
    }
  }, [draftId, t])

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

  const src = draftId ? `${previewUrl(draftId)}?v=${previewNonce}` : ''

  if (loading) {
    return (
      <div className="mx-auto max-w-6xl space-y-4">
        <Skeleton className="h-12 w-full" />
        <div className="grid gap-4 lg:grid-cols-2">
          <Skeleton className="h-96 w-full" />
          <Skeleton className="h-96 w-full" />
        </div>
      </div>
    )
  }

  if (error || !draft) {
    return (
      <div className="mx-auto max-w-4xl space-y-4">
        <h1 className="text-3xl font-black">{t('builder.title')}</h1>
        <p className="text-red-600">{error ?? t('builder.loadFailed')}</p>
        <Button variant="neutral" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-7xl space-y-4">
      {/* 顶栏 */}
      <div className="sticky top-0 z-20 flex flex-wrap items-center gap-2 rounded-base border-2 border-border bg-bg p-3 shadow-shadow">
        <Button variant="neutral" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <Input
          value={draft.title}
          onChange={(e) => mutate((prev) => ({ ...prev, title: e.target.value }))}
          className="w-48"
        />
        <span className="text-xs text-gray-500">
          {saveStatus === 'saving'
            ? t('builder.saving')
            : saveStatus === 'saved'
              ? t('builder.saved')
              : saveStatus === 'error'
                ? t('builder.saveFailed')
                : ''}
        </span>

        <div className="ml-auto flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1 text-sm">
            {t('builder.template')}
            <select
              className={SELECT_CLASS}
              value={draft.template_id}
              onChange={(e) => changeTemplate(e.target.value as TemplateId)}
            >
              {TEMPLATES.map((id) => (
                <option key={id} value={id}>
                  {t(`builder.template_${id}`)}
                </option>
              ))}
            </select>
          </label>

          <label className="flex items-center gap-1 text-sm">
            {t('builder.density')}
            <select
              className={SELECT_CLASS}
              value={draft.design_tokens.density}
              onChange={(e) => changeDensity(e.target.value as LayoutDensity)}
            >
              {DENSITIES.map((id) => (
                <option key={id} value={id}>
                  {t(`builder.density_${id}`)}
                </option>
              ))}
            </select>
          </label>

          <Button
            variant={draft.auto_one_page ? 'default' : 'neutral'}
            onClick={toggleAutoOnePage}
          >
            {t('builder.autoOnePage')}: {draft.auto_one_page ? t('common.active') : '—'}
          </Button>

          <Button variant="neutral" onClick={polishAll} disabled={polishingAll}>
            {polishingAll ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Sparkles className="h-4 w-4" />
            )}
            {t('builder.polishAll')}
          </Button>

          <Button variant="neutral" onClick={doScore} disabled={scoring}>
            {scoring ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <BarChart3 className="h-4 w-4" />
            )}
            {t('builder.score')}
          </Button>

          <Button onClick={doExport} disabled={exporting}>
            {exporting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Download className="h-4 w-4" />
            )}
            {t('builder.export')}
          </Button>
        </div>
      </div>

      {/* 三区：左编辑 / 右预览 */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* 左：结构化编辑器 */}
        <div className="space-y-4">
          {/* 证件照：空 / 加载 / 成功（待确认 · 已确认） / 失败 四态 */}
          <Card>
            <CardContent className="space-y-3 py-4">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="font-heading text-sm">{t('builder.photo.title')}</h3>
                <label className="ml-auto flex items-center gap-1 text-sm">
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
              </div>

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

              {photoError && <p className="text-sm text-red-600">{photoError}</p>}
            </CardContent>
          </Card>

          {/* 个人简介 */}
          <Card>
            <CardContent className="space-y-2 py-4">
              <h3 className="font-heading text-sm">{t('builder.summary')}</h3>
              <textarea
                className="min-h-20 w-full rounded-base border-2 border-border bg-white p-2 text-sm shadow-shadow focus:outline-none"
                value={draft.summary ?? ''}
                placeholder={t('builder.summaryPlaceholder')}
                onChange={(e) => mutate((prev) => ({ ...prev, summary: e.target.value }))}
              />
            </CardContent>
          </Card>

          {draft.sections.map((section, si) => (
            <Card key={`${section.section_type}-${si}`}>
              <CardContent className="space-y-3 py-4">
                <div className="flex items-center gap-2">
                  <h3 className="font-heading text-base">{sectionLabel(section)}</h3>
                  <div className="ml-auto flex items-center gap-1">
                    <Button
                      variant="neutral"
                      size="icon"
                      title={section.visible ? t('builder.hidden') : t('builder.visible')}
                      onClick={() => updateSection(si, { visible: !section.visible })}
                    >
                      {section.visible ? (
                        <Eye className="h-4 w-4" />
                      ) : (
                        <EyeOff className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="neutral"
                      size="icon"
                      title={t('builder.moveUp')}
                      disabled={si === 0}
                      onClick={() => moveSection(si, -1)}
                    >
                      <ChevronUp className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="neutral"
                      size="icon"
                      title={t('builder.moveDown')}
                      disabled={si === draft.sections.length - 1}
                      onClick={() => moveSection(si, 1)}
                    >
                      <ChevronDown className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {section.items.map((item, ii) => (
                  <div
                    key={ii}
                    className="space-y-2 rounded-base border-2 border-border bg-white/60 p-3"
                  >
                    <div className="grid gap-2 sm:grid-cols-3">
                      <Input
                        value={item.heading ?? ''}
                        placeholder={t('builder.heading')}
                        onChange={(e) => updateItem(si, ii, { heading: e.target.value })}
                      />
                      <Input
                        value={item.subheading ?? ''}
                        placeholder={t('builder.subheading')}
                        onChange={(e) => updateItem(si, ii, { subheading: e.target.value })}
                      />
                      <Input
                        value={item.date_range ?? ''}
                        placeholder={t('builder.dateRange')}
                        onChange={(e) => updateItem(si, ii, { date_range: e.target.value })}
                      />
                    </div>

                    {item.bullets.map((bullet, bi) => (
                      <div key={bi} className="flex items-start gap-2">
                        <textarea
                          className="min-h-10 flex-1 rounded-base border-2 border-border bg-white p-2 text-sm shadow-shadow focus:outline-none"
                          value={bullet}
                          placeholder={t('builder.bulletPlaceholder')}
                          onChange={(e) => updateBullet(si, ii, bi, e.target.value)}
                        />
                        <Button
                          variant="neutral"
                          size="icon"
                          title={t('builder.removeBullet')}
                          onClick={() => removeBullet(si, ii, bi)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    ))}

                    <div className="flex flex-wrap items-center gap-2">
                      <Button variant="neutral" size="sm" onClick={() => addBullet(si, ii)}>
                        <Plus className="h-3 w-3" />
                        {t('builder.addBullet')}
                      </Button>
                      <Button
                        variant="neutral"
                        size="sm"
                        onClick={() => openPolish(si, ii)}
                        disabled={polishingKey === `${si}-${ii}`}
                      >
                        {polishingKey === `${si}-${ii}` ? (
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
                        onClick={() => removeItem(si, ii)}
                      >
                        <Trash2 className="h-3 w-3" />
                        {t('builder.removeItem')}
                      </Button>
                    </div>
                  </div>
                ))}

                <Button variant="neutral" size="sm" onClick={() => addItem(si)}>
                  <Plus className="h-3 w-3" />
                  {t('builder.addItem')}
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* 右：实时预览 */}
        <div className="lg:sticky lg:top-24 lg:h-[calc(100vh-8rem)]">
          <Card className="h-full overflow-hidden">
            <CardContent className="h-full p-2">
              <iframe
                key={src}
                src={src}
                title={t('builder.preview')}
                className="h-[80vh] w-full rounded-base border-2 border-border bg-white lg:h-full"
              />
            </CardContent>
          </Card>
        </div>
      </div>

      {/* 润色 diff 弹窗 */}
      {polishTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div className="absolute inset-0 bg-black/40" onClick={() => setPolishTarget(null)} />
          <div className="relative z-10 mx-4 max-h-[80vh] w-full max-w-2xl overflow-auto rounded-base border-2 border-border bg-bg p-6 shadow-shadow">
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

      {/* AI 打分抽屉 */}
      {scoreOpen && score && (
        <div className="fixed inset-0 z-50 flex justify-end">
          <div className="absolute inset-0 bg-black/40" onClick={() => setScoreOpen(false)} />
          <div className="relative z-10 h-full w-full max-w-md overflow-auto border-l-2 border-border bg-bg p-6 shadow-shadow">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="font-heading text-xl">{t('builder.score')}</h2>
              <button onClick={() => setScoreOpen(false)} aria-label={t('common.close')}>
                <X className="h-5 w-5" />
              </button>
            </div>
            <div className="mb-4 flex items-center gap-3">
              <span className="text-4xl font-black">{score.overall_score}</span>
              <span className="text-sm text-gray-500">{t('builder.scoreOverall')}</span>
            </div>
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
            <div className="mt-4 space-y-2">
              {score.dimension_scores.map((d) => (
                <div key={d.name} className="flex items-center justify-between text-sm">
                  <span>{d.name}</span>
                  <Badge variant="neutral">{d.score}</Badge>
                </div>
              ))}
            </div>
            {score.summary && <p className="mt-4 text-sm text-gray-600">{score.summary}</p>}
          </div>
        </div>
      )}
    </div>
  )
}
