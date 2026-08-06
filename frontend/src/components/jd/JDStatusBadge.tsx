import { useTranslation } from 'react-i18next'
import { CircleAlert, CircleCheck, Loader2, TriangleAlert } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { JDStatus } from '@/types/jd'

const styles: Record<JDStatus, string> = {
  processing: 'bg-yellow-300 text-yellow-950 border-yellow-700',
  duplicate_pending: 'bg-orange-300 text-orange-950 border-orange-700',
  needs_review: 'bg-violet-300 text-violet-950 border-violet-700',
  ready: 'bg-green-400 text-green-950 border-green-700',
  failed: 'bg-red-400 text-red-950 border-red-700',
  archived: 'bg-zinc-300 text-zinc-800 border-zinc-500',
}

function StatusIcon({ status }: { status: JDStatus }) {
  if (status === 'processing') return <Loader2 className="animate-spin" />
  if (status === 'ready') return <CircleCheck />
  if (status === 'failed') return <CircleAlert />
  return <TriangleAlert />
}

export function JDStatusBadge({ status }: { status: JDStatus }) {
  const { t } = useTranslation()
  return (
    <Badge className={styles[status]}>
      <StatusIcon status={status} />
      {t(`jd.status.${status}`)}
    </Badge>
  )
}
