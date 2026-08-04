import { useTranslation } from 'react-i18next'
import { Loader2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

export function RegeneratePlanDialog({ open, pending, onOpenChange, onConfirm }: {
  open: boolean
  pending: boolean
  onOpenChange: (open: boolean) => void
  onConfirm: () => void
}) {
  const { t } = useTranslation()
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader><DialogTitle>{t('plans.regenerateTitle')}</DialogTitle><DialogDescription>{t('plans.regenerateDescription')}</DialogDescription></DialogHeader>
        <DialogFooter><Button type="button" variant="neutral" disabled={pending} onClick={() => onOpenChange(false)}>{t('common.cancel')}</Button><Button type="button" disabled={pending} onClick={onConfirm}>{pending ? <Loader2 className="size-4 animate-spin" /> : <RefreshCw className="size-4" />}{t('plans.regenerate')}</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
