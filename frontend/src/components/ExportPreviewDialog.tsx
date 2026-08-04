import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { CircleAlert, Download, Loader2 } from 'lucide-react'

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'

const A4_WIDTH = 794
const A4_HEIGHT = 1123

type PreviewState = 'loading' | 'ready' | 'error'

interface ExportPreviewDialogProps {
  open: boolean
  src: string
  title: string
  exporting: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}

export function ExportPreviewDialog({
  open,
  src,
  title,
  exporting,
  onOpenChange,
  onConfirm,
}: ExportPreviewDialogProps) {
  const { t } = useTranslation()
  const [previewState, setPreviewState] = useState<PreviewState>('loading')
  const [retryKey, setRetryKey] = useState(0)

  useEffect(() => {
    if (!open) return
    setPreviewState('loading')
  }, [open, src])

  const retryPreview = () => {
    setPreviewState('loading')
    setRetryKey((key) => key + 1)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="grid h-[min(90vh,1100px)] max-h-[90vh] max-w-[min(96vw,920px)] grid-rows-[auto_minmax(0,1fr)_auto] gap-3 overflow-hidden p-4 sm:p-6">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Download className="h-5 w-5" />
            {t('builder.exportPreviewTitle')}
          </DialogTitle>
          <DialogDescription>
            {t('builder.exportPreviewDescription', { title })}
          </DialogDescription>
        </DialogHeader>

        <div className="relative min-h-0 overflow-auto rounded-base border-2 border-border bg-zinc-300 p-3">
          <div className="mx-auto w-fit min-w-0">
            <iframe
              key={`${src}-${retryKey}`}
              src={src}
              title={`${t('builder.preview')} - ${title}`}
              className={`block border-0 bg-white shadow-[4px_4px_0_0_rgba(0,0,0,0.35)] ${
                previewState === 'error' ? 'invisible' : ''
              }`}
              style={{ width: A4_WIDTH, height: A4_HEIGHT }}
              onLoad={() => setPreviewState('ready')}
              onError={() => setPreviewState('error')}
            />
          </div>

          {previewState === 'loading' && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-zinc-300/90 p-4">
              <div className="flex items-center gap-2 rounded-base border-2 border-border bg-background px-4 py-3 text-sm shadow-shadow">
                <Loader2 className="h-4 w-4 animate-spin" />
                {t('builder.exportPreviewLoading')}
              </div>
            </div>
          )}

          {previewState === 'error' && (
            <div className="absolute inset-0 z-10 flex items-center justify-center p-4">
              <div className="flex max-w-sm flex-col items-center gap-3 rounded-base border-2 border-border bg-background p-5 text-center shadow-shadow">
                <CircleAlert className="h-6 w-6" />
                <p className="text-sm">{t('builder.exportPreviewFailed')}</p>
                <Button type="button" variant="neutral" onClick={retryPreview}>
                  {t('common.retry')}
                </Button>
              </div>
            </div>
          )}
        </div>

        <DialogFooter className="flex-col gap-2 sm:flex-row sm:justify-end">
          <Button
            type="button"
            variant="neutral"
            onClick={() => onOpenChange(false)}
            disabled={exporting}
          >
            {t('common.cancel')}
          </Button>
          <Button type="button" onClick={onConfirm} disabled={previewState !== 'ready' || exporting}>
            {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
            {exporting ? t('builder.exporting') : t('builder.confirmExport')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
