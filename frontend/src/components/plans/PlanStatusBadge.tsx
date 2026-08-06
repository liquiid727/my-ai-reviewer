import { useTranslation } from 'react-i18next'
import { CircleAlert, CircleCheck, Loader2, Play } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import type { PlanStatus } from '@/types/plans'

const styles: Record<PlanStatus, string> = {
  generating: 'bg-yellow-300 text-yellow-950 border-yellow-700',
  regenerating: 'bg-orange-300 text-orange-950 border-orange-700',
  active: 'bg-green-400 text-green-950 border-green-700',
  completed: 'bg-blue-300 text-blue-950 border-blue-700',
  failed: 'bg-red-400 text-red-950 border-red-700',
}

function StatusIcon({ status }: { status: PlanStatus }) {
  if (status === 'generating' || status === 'regenerating') {
    return <Loader2 className="animate-spin" />
  }
  if (status === 'active') return <Play />
  if (status === 'completed') return <CircleCheck />
  return <CircleAlert />
}

export function PlanStatusBadge({ status }: { status: PlanStatus }) {
  const { t } = useTranslation()
  return (
    <Badge className={styles[status]}>
      <StatusIcon status={status} />
      {t(`plans.status.${status}`)}
    </Badge>
  )
}
