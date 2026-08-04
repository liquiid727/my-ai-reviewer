import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { CircleAlert, ClipboardPlus, Search } from 'lucide-react'
import { listPlans } from '@/api/plans'
import { PlanStatusBadge } from '@/components/plans/PlanStatusBadge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { PlanListData, PlanStatus, PlanSummary } from '@/types/plans'

const statuses: Array<PlanStatus | 'all'> = ['all', 'generating', 'regenerating', 'active', 'completed', 'failed']

function readableDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

function PlanRow({ plan }: { plan: PlanSummary }) {
  const { t } = useTranslation()
  return (
    <Card className="gap-4 py-4">
      <CardHeader className="px-4 sm:px-6">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0"><CardTitle className="truncate text-base">{plan.title}</CardTitle><p className="mt-1 truncate text-sm text-muted-foreground">{[plan.jd.title, plan.jd.company].filter(Boolean).join(' · ') || t('plans.unknownJD')}</p></div>
          <PlanStatusBadge status={plan.status} />
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 px-4 sm:flex-row sm:items-end sm:justify-between sm:px-6">
        <div className="grid min-w-0 flex-1 gap-1 text-sm text-muted-foreground sm:grid-cols-3">
          <span className="truncate">{plan.resume.display_name}</span>
          <span>{t('plans.progressValue', { done: plan.progress.done, total: plan.progress.total, percent: plan.progress.percent })}</span>
          <span className="truncate">{plan.next_due_task || t('plans.noNextDue')}</span>
        </div>
        <div className="flex shrink-0 items-center gap-3"><span className="text-xs text-muted-foreground">{readableDate(plan.updated_at)}</span><Button asChild size="sm" variant="neutral"><Link to={`/plans/${plan.id}`}>{t('plans.open')}</Link></Button></div>
      </CardContent>
    </Card>
  )
}

export function PlanListPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<PlanListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [query, setQuery] = useState('')
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<PlanStatus | 'all'>('all')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await listPlans({ page, q: query, status: status === 'all' ? '' : status })
      if (response.code !== 0) throw new Error(response.message || t('plans.loadFailed'))
      setData(response.data)
      setError(null)
    } catch (reason) {
      setError((reason as Error).message || t('plans.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [page, query, status, t])

  useEffect(() => { void load() }, [load])

  return (
    <div className="space-y-6 py-4 sm:py-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between"><div><h1 className="text-3xl font-black">{t('plans.title')}</h1><p className="mt-1 text-sm text-muted-foreground">{t('plans.subtitle')}</p></div><Button asChild><Link to="/plans/new"><ClipboardPlus className="size-4" />{t('plans.create')}</Link></Button></div>
      <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_12rem_auto]" onSubmit={(event) => { event.preventDefault(); setPage(1); setQuery(search.trim()) }}>
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('plans.search')} />
        <Select value={status} onValueChange={(value) => { setPage(1); setStatus(value as PlanStatus | 'all') }}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{statuses.map((value) => <SelectItem key={value} value={value}>{t(`plans.filterStatus.${value}`)}</SelectItem>)}</SelectContent></Select>
        <Button type="submit" variant="neutral"><Search className="size-4" />{t('plans.searchButton')}</Button>
      </form>
      {error && <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('plans.loadFailed')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{error}</span><Button size="sm" variant="neutral" onClick={() => void load()}>{t('common.retry')}</Button></AlertDescription></Alert>}
      {loading ? <div className="space-y-4">{[0, 1, 2].map((value) => <Card key={value}><CardHeader><Skeleton className="h-6 w-2/5" /></CardHeader><CardContent><Skeleton className="h-4 w-3/4" /></CardContent></Card>)}</div> : data?.items.length ? <div className="space-y-4">{data.items.map((plan) => <PlanRow key={plan.id} plan={plan} />)}</div> : !error && <Card><CardContent className="flex flex-col items-center gap-3 py-14 text-center"><ClipboardPlus className="size-8" /><p className="font-heading">{t('plans.emptyTitle')}</p><p className="text-sm text-muted-foreground">{t('plans.emptyDescription')}</p><Button asChild><Link to="/plans/new">{t('plans.create')}</Link></Button></CardContent></Card>}
      {data && data.total > data.page_size && <div className="flex items-center justify-between gap-3"><span className="text-sm text-muted-foreground">{t('plans.page', { page, total: Math.max(1, Math.ceil(data.total / data.page_size)) })}</span><div className="flex gap-2"><Button size="sm" variant="neutral" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>{t('plans.previous')}</Button><Button size="sm" variant="neutral" disabled={page * data.page_size >= data.total} onClick={() => setPage((value) => value + 1)}>{t('plans.next')}</Button></div></div>}
    </div>
  )
}
