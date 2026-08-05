import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { Loader2, MessageSquare } from 'lucide-react'

import { createInterview } from '@/api/interview'
import { getJobDescription, listJobDescriptions } from '@/api/jd'
import { listResumeOptions, type ResumeOption } from '@/api/resume'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { JDListItem } from '@/types/jd'

/** JD 来源模式：从 JD 库选择 / 手动粘贴 / 不使用 JD */
type JdMode = 'library' | 'custom' | 'none'

const QUESTION_COUNTS = [3, 5, 8, 10]
const SELECT_CLASS =
  'rounded-base border-2 border-border bg-white px-3 py-1.5 text-sm font-base shadow-shadow focus:outline-none'

interface StartInterviewDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** 从简历发起：固定简历，让用户选择 JD */
  resumeId?: string
  /** 从简历草稿发起：以草稿当前内容为出题依据，让用户选择 JD */
  draftId?: string
  /** 从 JD 发起：固定 JD，让用户选择目标简历 */
  jdId?: string
}

/**
 * 发起模拟面试的共享对话框。
 * - resumeId / draftId 模式：选择 JD（JD 库 / 手动粘贴 / 不用 JD）后创建面试；
 * - jdId 模式：选择目标简历后创建面试。
 */
export function StartInterviewDialog({ open, onOpenChange, resumeId, draftId, jdId }: StartInterviewDialogProps) {
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [jdOptions, setJdOptions] = useState<JDListItem[]>([])
  const [jdOptionsLoading, setJdOptionsLoading] = useState(false)
  const [jdMode, setJdMode] = useState<JdMode>('none')
  const [selectedJdId, setSelectedJdId] = useState('')
  const [jdText, setJdText] = useState('')
  const [jdLoading, setJdLoading] = useState(false)

  const [resumeOptions, setResumeOptions] = useState<ResumeOption[]>([])
  const [resumeOptionsLoading, setResumeOptionsLoading] = useState(false)
  const [resumeOptionsError, setResumeOptionsError] = useState<string | null>(null)
  const [selectedResumeId, setSelectedResumeId] = useState('')

  const [questionCount, setQuestionCount] = useState(5)
  const [starting, setStarting] = useState(false)

  // 打开时按发起方向加载可选项；关闭时重置选择状态
  useEffect(() => {
    if (!open) return
    setJdMode('none')
    setSelectedJdId('')
    setJdText('')
    setSelectedResumeId('')
    setResumeOptionsError(null)
    setQuestionCount(5)

    if (resumeId || draftId) {
      setJdOptionsLoading(true)
      listJobDescriptions({ status: 'ready', pageSize: 50 })
        .then((res) => {
          const items = res.code === 0 ? res.data?.items ?? [] : []
          setJdOptions(items)
        })
        .catch(() => setJdOptions([]))
        .finally(() => setJdOptionsLoading(false))
    }

    if (jdId) {
      setResumeOptionsLoading(true)
      listResumeOptions()
        .then((res) => {
          if (res.code !== 0) {
            setResumeOptionsError(res.message || t('interviewStart.resumesLoadFailed'))
            return
          }
          const items = res.data?.items ?? []
          setResumeOptions(items)
          if (items.length > 0) setSelectedResumeId(items[0].id)
        })
        .catch((err: Error) => setResumeOptionsError(err.message || t('interviewStart.resumesLoadFailed')))
        .finally(() => setResumeOptionsLoading(false))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, resumeId, draftId, jdId])

  // JD 库选中变化时拉取完整 JD 文本（createInterview 需要 jd_text）
  useEffect(() => {
    if (!open || jdMode !== 'library' || !selectedJdId) {
      setJdLoading(false)
      return
    }
    setJdLoading(true)
    getJobDescription(selectedJdId)
      .then((res) => {
        if (res.code === 0 && res.data) setJdText(res.data.raw_text || '')
      })
      .catch(() => {
        // 拉取失败时保留空文本，允许用户切换为手动粘贴
      })
      .finally(() => setJdLoading(false))
  }, [open, jdMode, selectedJdId])

  const canConfirm = starting
    ? false
    : jdId
      ? selectedResumeId !== ''
      : jdMode !== 'library' || (selectedJdId !== '' && !jdLoading)

  const handleConfirm = useCallback(async () => {
    const targetResumeId = resumeId ?? selectedResumeId
    if (!draftId && !targetResumeId) return
    setStarting(true)
    try {
      const finalJdText = jdMode === 'none' ? '' : jdText.trim()
      const res = await createInterview({
        draftId: draftId || undefined,
        resumeId: draftId ? undefined : targetResumeId,
        jdText: finalJdText || undefined,
        questionCount,
      })
      if (res.code !== 0) {
        toast.error(res.message || t('interviewStart.failed'))
        return
      }
      toast.success(t('interviewStart.success'))
      onOpenChange(false)
      navigate(`/interview/${res.data.interview_id}`)
    } catch (err) {
      toast.error((err as Error).message || t('interviewStart.failed'))
    } finally {
      setStarting(false)
    }
  }, [draftId, resumeId, selectedResumeId, jdMode, jdText, questionCount, navigate, onOpenChange, t])

  const isFromJd = Boolean(jdId)

  const titleKey = draftId
    ? 'interviewStart.titleFromDraft'
    : isFromJd
      ? 'interviewStart.titleFromJd'
      : 'interviewStart.titleFromResume'
  const descriptionKey = draftId
    ? 'interviewStart.descriptionFromDraft'
    : isFromJd
      ? 'interviewStart.descriptionFromJd'
      : 'interviewStart.descriptionFromResume'

  return (
    <Dialog open={open} onOpenChange={(next) => !starting && onOpenChange(next)}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{t(titleKey)}</DialogTitle>
          <DialogDescription>{t(descriptionKey)}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* 从 JD 发起：选择目标简历 */}
          {isFromJd && (
            <div className="space-y-2">
              <label className="text-sm font-heading">{t('interviewStart.resumeLabel')}</label>
              {resumeOptionsLoading ? (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="size-4 animate-spin" />
                  {t('common.loading')}
                </div>
              ) : resumeOptionsError ? (
                <p className="text-sm text-red-700">{resumeOptionsError}</p>
              ) : resumeOptions.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('interviewStart.resumeEmpty')}</p>
              ) : (
                <select
                  className={`${SELECT_CLASS} w-full`}
                  value={selectedResumeId}
                  onChange={(e) => setSelectedResumeId(e.target.value)}
                >
                  {resumeOptions.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.display_name}
                    </option>
                  ))}
                </select>
              )}
            </div>
          )}

          {/* 从简历发起：选择 JD 来源 */}
          {!isFromJd && (
            <>
              <div className="space-y-2">
                <label className="text-sm font-heading">{t('interviewStart.jdMode')}</label>
                <Select value={jdMode} onValueChange={(value) => setJdMode(value as JdMode)}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">{t('interviewStart.jdNone')}</SelectItem>
                    <SelectItem value="library" disabled={jdOptionsLoading || jdOptions.length === 0}>
                      {t('interviewStart.jdLibrary')}
                    </SelectItem>
                    <SelectItem value="custom">{t('interviewStart.jdCustom')}</SelectItem>
                  </SelectContent>
                </Select>
                {jdMode === 'library' && !jdOptionsLoading && jdOptions.length === 0 && (
                  <p className="text-xs text-muted-foreground">{t('interviewStart.jdLibraryEmpty')}</p>
                )}
              </div>

              {jdMode === 'library' && (
                <div className="space-y-2">
                  {jdOptionsLoading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="size-4 animate-spin" />
                      {t('common.loading')}
                    </div>
                  ) : (
                    <select
                      className={`${SELECT_CLASS} w-full`}
                      value={selectedJdId}
                      onChange={(e) => setSelectedJdId(e.target.value)}
                    >
                      <option value="">—</option>
                      {jdOptions.map((item) => (
                        <option key={item.id} value={item.id}>
                          {(item.title || t('jd.untitled')) + (item.company ? ` · ${item.company}` : '')}
                        </option>
                      ))}
                    </select>
                  )}
                  {jdLoading && (
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <Loader2 className="size-3 animate-spin" />
                      {t('interviewStart.jdLoading')}
                    </div>
                  )}
                </div>
              )}

              {jdMode === 'custom' && (
                <div className="space-y-2">
                  <textarea
                    value={jdText}
                    onChange={(e) => setJdText(e.target.value)}
                    placeholder={t('interviewStart.jdPlaceholder')}
                    rows={5}
                    className="w-full resize-none rounded-base border-2 border-border bg-white px-3 py-2 text-sm shadow-shadow focus:outline-none focus:ring-2 focus:ring-main"
                  />
                </div>
              )}
            </>
          )}

          <div className="flex items-center justify-between gap-2">
            <label className="text-sm font-heading">{t('interviewStart.questionCount')}</label>
            <Select value={String(questionCount)} onValueChange={(value) => setQuestionCount(Number(value))}>
              <SelectTrigger className="w-28">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {QUESTION_COUNTS.map((count) => (
                  <SelectItem key={count} value={String(count)}>
                    {t('resume.questionUnit', { count })}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <DialogFooter>
          <Button variant="neutral" disabled={starting} onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button disabled={!canConfirm} onClick={() => void handleConfirm()}>
            {starting ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <MessageSquare className="size-4" />
            )}
            {starting ? t('interviewStart.starting') : t('interviewStart.confirm')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
