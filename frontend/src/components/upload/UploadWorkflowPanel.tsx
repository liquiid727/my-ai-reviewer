import type { RefObject } from 'react'
import { ShieldCheck } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import type { PrivacyReviewData } from '@/types/resume'

export type UploadWorkflowPanelProps = {
  resumeId: string | null
  status: string | null
  currentStep: string | null
  completedSteps: string[]
  error: string | null
  privacyReview: PrivacyReviewData | null
  privacyBusy?: boolean
  privacyEntityType?: string
  privacyTextRef?: RefObject<HTMLTextAreaElement | null>
  onPrivacyEntityTypeChange?: (value: string) => void
  onMaskSelection?: () => void
  onApprovePrivacy?: () => void
  onRetry?: () => void
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
  privacyReview,
  privacyBusy = false,
  privacyEntityType = 'person',
  privacyTextRef,
  onPrivacyEntityTypeChange,
  onMaskSelection,
  onApprovePrivacy,
  onRetry,
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

  const progress = completedSteps.length * 25

  return (
    <div
      data-testid="upload-processing"
      className="rounded-lg border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_#000]"
    >
      <div className="mb-4 flex items-center gap-3">
        <h2 className="text-xl font-black">{t('upload.processing')}</h2>
        <Badge
          variant={status === 'failed' ? 'neutral' : 'default'}
          className={status === 'failed' ? 'bg-red-500 text-white' : ''}
          data-testid="upload-status-badge"
        >
          {status}
        </Badge>
      </div>

      {status !== 'failed' && (
        <>
          <Progress value={progress} className="mb-3" data-testid="upload-progress" />
          <p className="text-sm font-medium" data-testid="upload-current-step">
            {t(`upload.step.${currentStep || 'starting'}`)}
          </p>
          <div className="mt-2 flex flex-wrap gap-1">
            {completedSteps.map((step) => (
              <Badge key={step} variant="default">
                {step}
              </Badge>
            ))}
          </div>
        </>
      )}

      {status === 'failed' && (
        <div className="space-y-3" data-testid="upload-failed">
          <Alert variant="destructive">
            <AlertTitle>{t('upload.processingFailed')}</AlertTitle>
            <AlertDescription>{error || t('common.loading')}</AlertDescription>
          </Alert>
          <div className="flex gap-2">
            <Button onClick={() => onRetry?.()}>{t('upload.retry')}</Button>
            <Button variant="neutral" onClick={() => onReset?.()}>
              {t('upload.uploadAnother')}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
