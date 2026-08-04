import { Badge } from '@/components/ui/badge'
import type { PlanStatus } from '@/types/plans'

const labels: Record<PlanStatus, string> = {
  generating: 'Generating',
  regenerating: 'Regenerating',
  active: 'Active',
  completed: 'Completed',
  failed: 'Failed',
}

const styles: Record<PlanStatus, string> = {
  generating: 'bg-yellow-300 text-yellow-950 border-yellow-700',
  regenerating: 'bg-orange-300 text-orange-950 border-orange-700',
  active: 'bg-green-400 text-green-950 border-green-700',
  completed: 'bg-blue-300 text-blue-950 border-blue-700',
  failed: 'bg-red-400 text-red-950 border-red-700',
}

export function PlanStatusBadge({ status }: { status: PlanStatus }) {
  return <Badge className={styles[status]}>{labels[status]}</Badge>
}
