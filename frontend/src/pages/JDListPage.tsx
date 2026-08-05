import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { CircleAlert, FilePlus2, Loader2, MessageSquare, Search } from 'lucide-react'
import { toast } from 'sonner'
import {
  cancelJDDuplicate,
  confirmJDDuplicate,
  listJobDescriptions,
} from '@/api/jd'
import { JDImportDialog } from '@/components/jd/JDImportDialog'
import { JDStatusBadge } from '@/components/jd/JDStatusBadge'
import { StartInterviewDialog } from '@/components/interview/StartInterviewDialog'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
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
import type { JDDetail, JDListData, JDListItem, JDSourceType, JDStatus } from '@/types/jd'

const sourceValues: Array<JDSourceType | 'all'> = ['all', 'text', 'file', 'url']
const statusValues: Array<JDStatus | 'all'> = ['all', 'processing', 'duplicate_pending', 'ready', 'failed']

function readableDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

function JDRow({ item, onConfirmDuplicate, onCancelDuplicate, onStartInterview }: {
  item: JDListItem
  onConfirmDuplicate: (item: JDListItem) => void
  onCancelDuplicate: (item: JDListItem) => void
  onStartInterview: (item: JDListItem) => void
}) {
  const { t } = useTranslation()
  return (
    <Card className="gap-4 py-4">
      <CardHeader className="px-4 sm:px-6">
        <div className="flex min-w-0 flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1">
            <CardTitle className="truncate text-base">{item.title || t('jd.untitled')}</CardTitle>
            <p className="truncate text-sm text-muted-foreground">
              {[item.company, item.location, item.seniority].filter(Boolean).join(' · ') || t('jd.noMetadata')}
            </p>
          </div>
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Badge variant="neutral">{t(`jd.source.${item.source_type}`)}</Badge>
            <JDStatusBadge status={item.status} />
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex flex-col gap-3 px-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex min-w-0 flex-1 items-center gap-2 text-sm text-muted-foreground">
          {item.status === 'processing' && <Loader2 className="size-4 shrink-0 animate-spin" />}
          <span className="truncate">{item.processing_error || t(`jd.step.${item.processing_step}`, { defaultValue: item.processing_step })}</span>
          <span className="shrink-0">{readableDate(item.updated_at)}</span>
        </div>
        {item.status === 'duplicate_pending' ? (
          <div className="flex shrink-0 flex-wrap gap-2">
            <Button size="sm" onClick={() => onConfirmDuplicate(item)}>{t('jd.keepDuplicate')}</Button>
            <Button size="sm" variant="neutral" onClick={() => onCancelDuplicate(item)}>{t('jd.cancelDuplicate')}</Button>
          </div>
        ) : (
          <div className="flex shrink-0 flex-wrap gap-2">
            {item.status === 'ready' && (
              <Button size="sm" onClick={() => onStartInterview(item)}>
                <MessageSquare className="size-4" />
                {t('jd.startInterview')}
              </Button>
            )}
            <Button asChild size="sm" variant="neutral">
              <Link to={`/jobs/${item.id}`}>{t('jd.open')}</Link>
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function ListSkeleton() {
  return (
    <div className="space-y-4">
      {[0, 1, 2].map((value) => (
        <Card key={value} className="gap-4 py-4">
          <CardHeader className="px-4 sm:px-6"><Skeleton className="h-6 w-2/5" /></CardHeader>
          <CardContent className="px-4 sm:px-6"><Skeleton className="h-4 w-3/4" /></CardContent>
        </Card>
      ))}
    </div>
  )
}

export function JDListPage() {
  const { t } = useTranslation()
  const [data, setData] = useState<JDListData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [query, setQuery] = useState('')
  const [sourceType, setSourceType] = useState<JDSourceType | 'all'>('all')
  const [status, setStatus] = useState<JDStatus | 'all'>('all')
  const [importOpen, setImportOpen] = useState(false)
  const [llmGateOpen, setLlmGateOpen] = useState(false)
  // 发起面试选中的 JD（null 表示对话框关闭）
  const [interviewJdId, setInterviewJdId] = useState<string | null>(null)
  const pollingStartedAt = useRef<number | null>(null)

  const load = useCallback(async (showLoading = true) => {
    if (showLoading) setLoading(true)
    try {
      const response = await listJobDescriptions({
        page,
        q: query,
        sourceType: sourceType === 'all' ? '' : sourceType,
        status: status === 'all' ? '' : status,
      })
      if (response.code !== 0) throw new Error(response.message || t('jd.loadFailed'))
      setData(response.data)
      setError(null)
    } catch (reason) {
      setError((reason as Error).message || t('jd.loadFailed'))
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [page, query, sourceType, status, t])

  useEffect(() => {
    void load()
  }, [load])

  const hasProcessing = useMemo(
    () => data?.items.some((item) => item.status === 'processing') ?? false,
    [data],
  )

  useEffect(() => {
    if (!hasProcessing) {
      pollingStartedAt.current = null
      return undefined
    }
    pollingStartedAt.current ??= Date.now()
    let timer: number | undefined
    let stopped = false
    const schedule = () => {
      if (stopped || document.visibilityState !== 'visible') return
      const elapsed = Date.now() - (pollingStartedAt.current ?? Date.now())
      timer = window.setTimeout(async () => {
        await load(false)
        schedule()
      }, elapsed >= 60_000 ? 5_000 : 2_000)
    }
    const onVisibilityChange = () => {
      if (timer) window.clearTimeout(timer)
      if (document.visibilityState === 'visible') schedule()
    }
    document.addEventListener('visibilitychange', onVisibilityChange)
    schedule()
    return () => {
      stopped = true
      if (timer) window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibilityChange)
    }
  }, [hasProcessing, load])

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    setPage(1)
    setQuery(search.trim())
  }

  const confirmDuplicate = async (item: JDListItem) => {
    try {
      const response = await confirmJDDuplicate(item.id)
      if (response.code === 428) {
        setLlmGateOpen(true)
        return
      }
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      toast.success(t('jd.importStarted'))
      await load(false)
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.actionFailed'))
    }
  }

  const cancelDuplicate = async (item: JDListItem) => {
    try {
      const response = await cancelJDDuplicate(item.id)
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      setData((current) => current ? { ...current, items: current.items.filter((entry) => entry.id !== item.id), total: Math.max(0, current.total - 1) } : current)
      toast.success(t('jd.duplicateCancelled'))
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.actionFailed'))
    }
  }

  const created = (jd: JDDetail) => {
    setData((current) => current && page === 1
      ? { ...current, total: current.total + 1, items: [jd, ...current.items].slice(0, current.page_size) }
      : current)
    void load(false)
  }

  return (
    <div className="space-y-6 py-4 sm:py-8">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-3xl font-black">{t('jd.title')}</h1>
          <p className="mt-1 text-sm text-muted-foreground">{t('jd.subtitle')}</p>
        </div>
        <Button onClick={() => setImportOpen(true)}>
          <FilePlus2 className="size-4" />
          {t('jd.import')}
        </Button>
      </div>

      <form className="grid gap-3 md:grid-cols-[minmax(0,1fr)_11rem_11rem_auto]" onSubmit={submitSearch}>
        <Input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t('jd.search')} />
        <Select value={sourceType} onValueChange={(value) => { setPage(1); setSourceType(value as JDSourceType | 'all') }}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{sourceValues.map((value) => <SelectItem key={value} value={value}>{t(`jd.filterSource.${value}`)}</SelectItem>)}</SelectContent>
        </Select>
        <Select value={status} onValueChange={(value) => { setPage(1); setStatus(value as JDStatus | 'all') }}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>{statusValues.map((value) => <SelectItem key={value} value={value}>{t(`jd.filterStatus.${value}`)}</SelectItem>)}</SelectContent>
        </Select>
        <Button type="submit" variant="neutral"><Search className="size-4" />{t('jd.searchButton')}</Button>
      </form>

      {error && (
        <Alert variant="destructive">
          <CircleAlert />
          <AlertTitle>{t('jd.loadFailed')}</AlertTitle>
          <AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3">
            <span>{error}</span>
            <Button size="sm" variant="neutral" onClick={() => void load()}>{t('common.retry')}</Button>
          </AlertDescription>
        </Alert>
      )}

      {loading ? <ListSkeleton /> : data?.items.length ? (
        <div className="space-y-4">
          {data.items.map((item) => <JDRow key={item.id} item={item} onConfirmDuplicate={confirmDuplicate} onCancelDuplicate={cancelDuplicate} onStartInterview={(entry) => setInterviewJdId(entry.id)} />)}
        </div>
      ) : !error && (
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-14 text-center">
            <FilePlus2 className="size-8" />
            <p className="font-heading">{t('jd.emptyTitle')}</p>
            <p className="text-sm text-muted-foreground">{t('jd.emptyDescription')}</p>
            <Button onClick={() => setImportOpen(true)}>{t('jd.import')}</Button>
          </CardContent>
        </Card>
      )}

      {data && data.total > data.page_size && (
        <div className="flex items-center justify-between gap-3">
          <p className="text-sm text-muted-foreground">{t('jd.page', { page, total: Math.max(1, Math.ceil(data.total / data.page_size)) })}</p>
          <div className="flex gap-2">
            <Button size="sm" variant="neutral" disabled={page <= 1} onClick={() => setPage((value) => value - 1)}>{t('jd.previous')}</Button>
            <Button size="sm" variant="neutral" disabled={page * data.page_size >= data.total} onClick={() => setPage((value) => value + 1)}>{t('jd.next')}</Button>
          </div>
        </div>
      )}

      <JDImportDialog open={importOpen} onOpenChange={setImportOpen} onCreated={created} onLLMGate={() => setLlmGateOpen(true)} />
      <StartInterviewDialog
        open={interviewJdId !== null}
        onOpenChange={(open) => !open && setInterviewJdId(null)}
        jdId={interviewJdId ?? undefined}
      />
      <LLMGateDialog open={llmGateOpen} onOpenChange={setLlmGateOpen} description={t('jd.llmGateDescription')} successMessage={t('jd.llmReady')} />
    </div>
  )
}
