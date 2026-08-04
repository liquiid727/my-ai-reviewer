import { Badge } from '@/components/ui/badge'
import type { JDStatus } from '@/types/jd'

const labels: Record<JDStatus, string> = {
  processing: 'Processing',
  duplicate_pending: 'Duplicate review',
  ready: 'Ready',
  failed: 'Failed',
}

const styles: Record<JDStatus, string> = {
  processing: 'bg-yellow-300 text-yellow-950 border-yellow-700',
  duplicate_pending: 'bg-orange-300 text-orange-950 border-orange-700',
  ready: 'bg-green-400 text-green-950 border-green-700',
  failed: 'bg-red-400 text-red-950 border-red-700',
}

export function JDStatusBadge({ status }: { status: JDStatus }) {
  return <Badge className={styles[status]}>{labels[status]}</Badge>
}
