import type { RefObject } from 'react'
import { CircleAlert, CircleCheck, Copy, Loader2, ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { PrivacyReviewData, ResumeFailureDiagnostic, ResumeStatus } from '@/types/resume'

/** 与后端 PIPELINE_STEPS 保持一致的处理阶段顺序（backend/application/resume_service/queries.py） */
const PIPELINE_STEPS = ['text_extract', 'privacy_scan', 'llm_parse', 'classify', 'evaluate'] as const

type StepState = 'completed' | 'active' | 'pending'

function getStepState(
  step: string,
  currentStep: string | null,
  completedSteps: string[],
): StepState {
  if (completedSteps.includes(step)) return 'completed'
  if (currentStep === step) return 'active'
  return 'pending'
}

export type UploadWorkflowPanelProps = {
  resumeId: string | null
  status: ResumeStatus | null
  currentStep: string | null
  completedSteps: string[]
  error: string | null
  runId?: string | null
  diagnostic?: ResumeFailureDiagnostic | null
  privacyReview: PrivacyReviewData | null
  privacyBusy?: boolean
  privacyEntityType?: string
  privacyTextRef?: RefObject<HTMLTextAreaElement | null>
  onPrivacyEntityTypeChange?: (value: string) => void
  onMaskSelection?: () => void
  onApprovePrivacy?: () => void
  onRetry?: () => void
  pollTimedOut?: boolean
  pollError?: string | null
  onRecheck?: () => void
  onReset?: () => void
}

/**
 * Presentational branches for upload processing / privacy review / failure.
 * Kept free of fetch/polling so component tests stay deterministic.
 */
export function UploadWorkflowPanel({
  resumeId,
  status,
  currentStep,
  completedSteps,
  error,
  runId = null,
  diagnostic = null,
  privacyReview,
  privacyBusy = false,
  privacyEntityType = 'person',
  privacyTextRef,
  onPrivacyEntityTypeChange,
  onMaskSelection,
  onApprovePrivacy,
  onRetry,
  pollTimedOut = false,
  pollError = null,
  onRecheck,
  onReset,
}: UploadWorkflowPanelProps) {
  const { t } = useTranslation()

  if (!resumeId || !status) return null

  if (status === 'privacy_review_required' && privacyReview) {
    return (
      <div
        data-testid="upload-privacy-review"
        className="space-y-4 rounded-lg border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_#000]"
      >
        <div className="flex items-center gap-3">
          <ShieldCheck className="size-6" />
          <div>
            <h2 className="text-xl font-black">{t('upload.privacyTitle')}</h2>
            <p className="text-sm text-gray-600">{t('upload.privacyDescription')}</p>
          </div>
        </div>
        <textarea
          ref={privacyTextRef}
          value={privacyReview.masked_text || ''}
          readOnly
          aria-label={t('upload.privacyMaskedText')}
          data-testid="upload-privacy-masked-text"
          className="min-h-64 w-full resize-y rounded-base border-2 border-border bg-secondary-background p-3 font-mono text-sm"
        />
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={privacyEntityType}
            onChange={(event) => onPrivacyEntityTypeChange?.(event.target.value)}
            className="rounded-base border-2 border-border bg-white px-3 py-2 text-sm"
            aria-label={t('upload.privacyEntityType')}
          >
            {['person', 'phone', 'email', 'organization', 'school', 'address', 'project', 'url'].map(
              (type) => (
                <option key={type} value={type}>
                  {type}
                </option>
              ),
            )}
          </select>
          <Button variant="neutral" onClick={() => onMaskSelection?.()} disabled={privacyBusy}>
            {t('upload.privacyMaskSelection')}
          </Button>
          <Button onClick={() => onApprovePrivacy?.()} disabled={privacyBusy}>
            <ShieldCheck className="size-4" />
            {t('upload.privacyApprove')}
          </Button>
        </div>
      </div>
    )
  }

  if (status === 'evaluated') return null

  const progress = Math.min(
    100,
    Math.round((completedSteps.length / PIPELINE_STEPS.length) * 100),
  )
  const activeStep =
    currentStep && PIPELINE_STEPS.includes(currentStep as (typeof PIPELINE_STEPS)[number])
      ? currentStep
      : null

  return (
    <div
      data-testid="upload-processing"
      className="rounded-lg border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_#000]"
    >
      <div className="mb-1 flex items-center gap-3">
        <h2 className="text-xl font-black">{t('upload.processing')}</h2>
        <Badge
          variant={status === 'failed' ? 'neutral' : 'default'}
          className={status === 'failed' ? 'bg-red-500 text-white' : ''}
          data-testid="upload-status-badge"
        >
          {t(`upload.status.${status}`, status)}
        </Badge>
      </div>
      <p className="mb-4 text-sm text-gray-600">{t('upload.processingHint')}</p>

      {status !== 'failed' && !pollTimedOut && !pollError && (
        <>
          {/* 整体进度：进度条 + 百分比，按后端流水线阶段数折算 */}
          <div className="mb-4">
            <div className="mb-1 flex items-center justify-between text-sm">
              <span className="font-bold">{t('upload.overallProgress')}</span>
              <span className="font-bold">{progress}%</span>
            </div>
            <Progress value={progress} data-testid="upload-progress" />
          </div>

          {/* 当前阶段：旋转动画 + 具体进展描述 */}
          <div className="mb-4 flex items-center gap-3 rounded-base border-2 border-border bg-secondary-background p-3">
            <Loader2
              className="size-5 shrink-0 animate-spin"
              data-testid="upload-current-step-spinner"
            />
            <p className="text-sm font-bold" data-testid="upload-current-step">
              {t(`upload.stepDesc.${activeStep ?? 'starting'}`)}
            </p>
          </div>

          {/* 分阶段清单：已完成（绿色对勾）/ 进行中（旋转圈）/ 待处理（序号） */}
          <ol className="space-y-2">
            {PIPELINE_STEPS.map((step, index) => {
              const state = getStepState(step, currentStep, completedSteps)
              return (
                <li
                  key={step}
                  data-testid={`upload-step-${step}`}
                  aria-current={state === 'active' ? 'step' : undefined}
                  className="flex items-start gap-3"
                >
                  {state === 'completed' && (
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-border bg-success">
                      <CircleCheck className="size-4" />
                    </span>
                  )}
                  {state === 'active' && (
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-border bg-main">
                      <Loader2 className="size-4 animate-spin" />
                    </span>
                  )}
                  {state === 'pending' && (
                    <span className="flex size-6 shrink-0 items-center justify-center rounded-full border-2 border-border bg-secondary-background text-xs font-bold text-foreground/50">
                      {index + 1}
                    </span>
                  )}
                  <div className="min-w-0">
                    <p
                      className={`text-sm ${
                        state === 'active'
                          ? 'font-black'
                          : state === 'completed'
                            ? 'font-medium'
                            : 'font-medium text-foreground/50'
                      }`}
                    >
                      {t(`upload.step.${step}`)}
                    </p>
                    {state === 'active' && (
                      <p className="text-xs text-gray-600">{t(`upload.stepDesc.${step}`)}</p>
                    )}
                  </div>
                </li>
              )
            })}
          </ol>
        </>
      )}

      {status === 'failed' && (
        <div className="space-y-3" data-testid="upload-failed">
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>{t('upload.processingFailed')}</AlertTitle>
            <AlertDescription>
              <p>
                {diagnostic
                  ? t(`upload.failure.${diagnostic.error_code}`, {
                      defaultValue: error || t('upload.failure.RESUME_PROCESSING_FAILED'),
                    })
                  : error?.toLowerCase().includes('softtimelimitexceeded')
                    ? t('upload.failure.RESUME_PROCESSING_TIMEOUT')
                    : error || t('upload.failure.RESUME_PROCESSING_FAILED')}
              </p>
              {diagnostic?.step && (
                <p className="mt-1 text-xs font-bold">
                  {t('upload.failureStage', {
                    step: t(`upload.step.${diagnostic.step}`, { defaultValue: diagnostic.step }),
                  })}
                </p>
              )}
              {runId && <RunIdBlock runId={runId} />}
            </AlertDescription>
          </Alert>
          <div className="flex gap-2">
            <Button onClick={() => onRetry?.()}>{t('upload.retry')}</Button>
            <Button variant="neutral" onClick={() => onReset?.()}>
              {t('upload.uploadAnother')}
            </Button>
          </div>
        </div>
      )}

      {pollTimedOut && status !== 'failed' && (
        <div className="space-y-3" data-testid="upload-timeout">
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>{t('upload.processingTimedOut')}</AlertTitle>
            <AlertDescription>{t('upload.processingTimedOutDescription')}</AlertDescription>
          </Alert>
          <div className="flex flex-wrap gap-2">
            <Button variant="neutral" onClick={() => onRecheck?.()}>
              {t('upload.recheck')}
            </Button>
            <Button onClick={() => onRetry?.()}>{t('upload.retryTask')}</Button>
          </div>
        </div>
      )}

      {pollError && status !== 'failed' && !pollTimedOut && (
        <div className="space-y-3" data-testid="upload-poll-error">
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>{t('upload.statusQueryFailed')}</AlertTitle>
            <AlertDescription>{pollError}</AlertDescription>
          </Alert>
          <Button variant="neutral" onClick={() => onRecheck?.()}>
            {t('upload.recheck')}
          </Button>
        </div>
      )}
    </div>
  )
}

function RunIdBlock({ runId }: { runId: string }) {
  const { t } = useTranslation()

  const copyRunId = async () => {
    try {
      await navigator.clipboard?.writeText(runId)
    } catch {
      // Copy is a convenience; the identifier remains selectable in the UI.
    }
  }

  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 rounded-base border-2 border-border bg-white p-2">
      <span className="text-xs font-bold">{t('upload.runId')}</span>
      <code className="break-all text-xs" data-testid="upload-run-id">
        {runId}
      </code>
      <Button
        type="button"
        variant="neutral"
        size="sm"
        aria-label={t('upload.copyRunId')}
        onClick={() => void copyRunId()}
      >
        <Copy className="size-3.5" />
        {t('upload.copyRunId')}
      </Button>
    </div>
  )
}
