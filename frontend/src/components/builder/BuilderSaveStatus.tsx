import { CircleAlert } from 'lucide-react'
import { useTranslation } from 'react-i18next'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  builderSaveStatusLabelKey,
  type BuilderSaveStatus as SaveStatus,
} from '@/lib/builder-save'

export type BuilderSaveStatusProps = {
  status: SaveStatus
  conflictMessage?: string | null
  onReload?: () => void
}

/**
 * Toolbar save label + optional revision-conflict banner for the builder.
 */
export function BuilderSaveStatus({
  status,
  conflictMessage,
  onReload,
}: BuilderSaveStatusProps) {
  const { t } = useTranslation()
  const labelKey = builderSaveStatusLabelKey(status)
  const showConflict = status === 'conflict' || Boolean(conflictMessage)

  return (
    <div data-testid="builder-save-status" className="contents">
      <span className="text-xs text-gray-500" data-testid="builder-save-label">
        {labelKey ? t(labelKey) : ''}
      </span>
      {showConflict && (
        <Alert data-testid="builder-save-conflict" className="basis-full">
          <CircleAlert />
          <AlertTitle>{t('builder.conflictTitle')}</AlertTitle>
          <AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3">
            <span>{conflictMessage || t('builder.revisionConflict')}</span>
            {onReload && (
              <Button size="sm" variant="neutral" onClick={onReload}>
                {t('builder.reload')}
              </Button>
            )}
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
