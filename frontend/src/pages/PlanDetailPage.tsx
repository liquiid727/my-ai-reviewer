import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { CircleAlert, ClipboardPlus, Loader2, RefreshCw, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  createPlanTask,
  deletePlan,
  deletePlanTask,
  getPlan,
  patchPlanTask,
  regeneratePlan,
  reorderPlanTasks,
  retryPlan,
} from '@/api/plans'
import { PlanStatusBadge } from '@/components/plans/PlanStatusBadge'
import { PlanTaskEditor } from '@/components/plans/PlanTaskEditor'
import { RegeneratePlanDialog } from '@/components/plans/RegeneratePlanDialog'
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
import type { PlanDetail, PlanMutationData, PlanTask, PlanTaskCategory, PlanTaskPriority, PlanTaskStatus } from '@/types/plans'

type TaskPatch = {
  title?: string
  category?: PlanTaskCategory
  description?: string
  priority?: PlanTaskPriority
  status?: PlanTaskStatus
  due_date?: string | null
}

const categories: PlanTaskCategory[] = ['gap_priority', 'resume', 'skill', 'evidence_project', 'interview', 'application_review']

function DetailSkeleton() {
  return <div className="space-y-5"><Skeleton className="h-10 w-2/5" /><Skeleton className="h-36 w-full" /><Skeleton className="h-72 w-full" /></div>
}

function progressStatus(progress: { done: number; total: number }) {
  return progress.total > 0 && progress.done === progress.total ? 'completed' : 'active'
}

export function PlanDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [plan, setPlan] = useState<PlanDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [conflict, setConflict] = useState(false)
  const [reconciliationVersion, setReconciliationVersion] = useState(0)
  const [regenerateOpen, setRegenerateOpen] = useState(false)
  const [transitionPending, setTransitionPending] = useState(false)
  const [manualTitle, setManualTitle] = useState('')
  const [manualCategory, setManualCategory] = useState<PlanTaskCategory>('gap_priority')
  const [manualPriority, setManualPriority] = useState<PlanTaskPriority>('medium')
  const [manualDueDate, setManualDueDate] = useState('')
  const [manualDescription, setManualDescription] = useState('')
  const revisionRef = useRef(0)
  const queueRef = useRef<Promise<unknown>>(Promise.resolve())
  const epochRef = useRef(0)
  const pollingStartedAt = useRef<number | null>(null)

  const load = useCallback(async (showLoading = true, clearConflict = true) => {
    if (showLoading) setLoading(true)
    try {
      const response = await getPlan(id)
      if (response.code !== 0) throw new Error(response.message || t('plans.loadFailed'))
      revisionRef.current = response.data.revision
      setPlan(response.data)
      setError(null)
      if (clearConflict) setConflict(false)
    } catch (reason) {
      setError((reason as Error).message || t('plans.loadFailed'))
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [id, t])

  useEffect(() => { void load() }, [load])

  const reconcile = useCallback(async () => {
    await load(false, false)
    setReconciliationVersion((value) => value + 1)
  }, [load])

  const isGenerating = plan?.status === 'generating' || plan?.status === 'regenerating'
  useEffect(() => {
    if (!isGenerating) {
      pollingStartedAt.current = null
      return undefined
    }
    pollingStartedAt.current ??= Date.now()
    let stopped = false
    let timer: number | undefined
    const schedule = () => {
      if (stopped || document.visibilityState !== 'visible') return
      const elapsed = Date.now() - (pollingStartedAt.current ?? Date.now())
      timer = window.setTimeout(async () => {
        await load(false, false)
        schedule()
      }, elapsed >= 60_000 ? 5_000 : 2_000)
    }
    const onVisibility = () => {
      if (timer) window.clearTimeout(timer)
      if (document.visibilityState === 'visible') schedule()
    }
    document.addEventListener('visibilitychange', onVisibility)
    schedule()
    return () => {
      stopped = true
      if (timer) window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', onVisibility)
    }
  }, [isGenerating, load])

  const enqueue = useCallback(async (
    request: (revision: number) => Promise<{ code: number; message: string; data: PlanMutationData }>,
    apply: (current: PlanDetail, data: PlanMutationData) => PlanDetail,
  ) => {
    const requestEpoch = epochRef.current
    const run = async () => {
      if (requestEpoch !== epochRef.current) throw new Error(t('plans.writeStopped'))
      const response = await request(revisionRef.current)
      if (response.code === 1007) {
        epochRef.current += 1
        setConflict(true)
        await reconcile()
        throw new Error(t('plans.revisionConflict'))
      }
      if (response.code !== 0) throw new Error(response.message || t('plans.saveFailed'))
      revisionRef.current = response.data.revision
      setPlan((current) => current ? apply(current, response.data) : current)
      return true
    }
    const queued = queueRef.current.then(run, run)
    queueRef.current = queued.catch(() => undefined)
    try {
      return await queued
    } catch (reason) {
      toast.error((reason as Error).message || t('plans.saveFailed'))
      return false
    }
  }, [reconcile, t])

  const patchTask = useCallback((taskId: string, patch: TaskPatch) => enqueue(
    (revision) => patchPlanTask(id, taskId, { expected_revision: revision, ...patch }),
    (current, data) => {
      const task = data.task
      if (!task) return current
      return {
        ...current,
        revision: data.revision,
        progress: data.progress,
        status: progressStatus(data.progress),
        tasks: current.tasks.map((entry) => entry.id === task.id ? task : entry),
      }
    },
  ), [enqueue, id])

  const createTask = async () => {
    if (!manualTitle.trim()) return
    const saved = await enqueue(
      (revision) => createPlanTask(id, {
        expected_revision: revision,
        title: manualTitle.trim(),
        category: manualCategory,
        description: manualDescription,
        priority: manualPriority,
        due_date: manualDueDate || null,
      }),
      (current, data) => data.task ? {
        ...current,
        revision: data.revision,
        progress: data.progress,
        status: progressStatus(data.progress),
        tasks: [...current.tasks, data.task].sort((a, b) => a.sort_order - b.sort_order),
      } : current,
    )
    if (saved) {
      setManualTitle('')
      setManualDescription('')
      setManualDueDate('')
    }
  }

  const removeTask = (taskId: string) => enqueue(
    (revision) => deletePlanTask(id, taskId, revision),
    (current, data) => ({
      ...current,
      revision: data.revision,
      progress: data.progress,
      status: progressStatus(data.progress),
      tasks: current.tasks.filter((task) => task.id !== taskId),
    }),
  )

  const moveTask = (taskId: string, direction: -1 | 1) => {
    if (!plan) return Promise.resolve(false)
    const ordered = [...plan.tasks].sort((a, b) => a.sort_order - b.sort_order)
    const currentIndex = ordered.findIndex((task) => task.id === taskId)
    const nextIndex = currentIndex + direction
    if (currentIndex < 0 || nextIndex < 0 || nextIndex >= ordered.length) return Promise.resolve(false)
    const next = [...ordered]
    const [moving] = next.splice(currentIndex, 1)
    next.splice(nextIndex, 0, moving)
    const ids = next.map((task) => task.id)
    return enqueue(
      (revision) => reorderPlanTasks(id, revision, ids),
      (current, data) => ({
        ...current,
        revision: data.revision,
        progress: data.progress,
        tasks: ids.map((taskId, index) => ({ ...current.tasks.find((task) => task.id === taskId) as PlanTask, sort_order: index })),
      }),
    )
  }

  const transition = async (kind: 'retry' | 'regenerate') => {
    if (!plan || transitionPending) return
    setTransitionPending(true)
    epochRef.current += 1
    try {
      await queueRef.current
      const response = kind === 'retry'
        ? await retryPlan(plan.id, revisionRef.current)
        : await regeneratePlan(plan.id, revisionRef.current)
      if (response.code === 1007) {
        setConflict(true)
        await reconcile()
        toast.error(t('plans.revisionConflict'))
        return
      }
      if (response.code === 5004) {
        revisionRef.current = response.data.revision
        setPlan((current) => current ? {
          ...current,
          status: response.data.status,
          revision: response.data.revision,
          generation_error: response.data.generation_error || response.message,
        } : current)
        setRegenerateOpen(false)
        toast.error(response.message || t('plans.actionFailed'))
        return
      }
      if (response.code !== 0) throw new Error(response.message || t('plans.actionFailed'))
      revisionRef.current = response.data.revision
      setPlan((current) => current ? { ...current, status: response.data.status, revision: response.data.revision, generation_error: response.data.generation_error || null } : current)
      setRegenerateOpen(false)
      toast.success(kind === 'retry' ? t('plans.generationStarted') : t('plans.regenerationStarted'))
    } catch (reason) {
      toast.error((reason as Error).message || t('plans.actionFailed'))
    } finally {
      setTransitionPending(false)
    }
  }

  const removePlan = async () => {
    if (!plan || !window.confirm(t('plans.deleteConfirm'))) return
    epochRef.current += 1
    setTransitionPending(true)
    try {
      await queueRef.current
      const response = await deletePlan(plan.id, revisionRef.current)
      if (response.code === 1007) {
        setConflict(true)
        await reconcile()
        toast.error(t('plans.revisionConflict'))
        return
      }
      if (response.code !== 0) throw new Error(response.message || t('plans.deleteFailed'))
      toast.success(t('plans.deleted'))
      navigate('/plans')
    } catch (reason) {
      toast.error((reason as Error).message || t('plans.deleteFailed'))
    } finally {
      setTransitionPending(false)
    }
  }

  const tasksByCategory = useMemo(() => {
    const bucket = new Map<PlanTaskCategory, PlanTask[]>()
    categories.forEach((category) => bucket.set(category, []))
    ;(plan?.tasks || []).slice().sort((a, b) => a.sort_order - b.sort_order).forEach((task) => bucket.get(task.category)?.push(task))
    return bucket
  }, [plan?.tasks])

  if (loading) return <DetailSkeleton />
  if (error || !plan) return <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('plans.loadFailed')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{error}</span><Button size="sm" variant="neutral" onClick={() => void load()}>{t('common.retry')}</Button></AlertDescription></Alert>

  const mutationDisabled = plan.status === 'generating' || plan.status === 'regenerating' || plan.status === 'failed'
  const orderedTasks = [...plan.tasks].sort((a, b) => a.sort_order - b.sort_order)
  return (
    <div className="space-y-6 py-4 sm:py-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between"><div className="min-w-0"><Button asChild size="sm" variant="neutral"><Link to="/plans">{t('common.back')}</Link></Button><div className="mt-4 flex flex-wrap items-center gap-2"><h1 className="break-words text-3xl font-black">{plan.title}</h1><PlanStatusBadge status={plan.status} /></div><p className="mt-2 break-words text-sm text-muted-foreground">{[plan.jd.title, plan.jd.company, plan.resume.display_name].filter(Boolean).join(' · ')}</p></div><div className="flex flex-wrap gap-2">{plan.status === 'failed' && <Button onClick={() => void transition('retry')} disabled={transitionPending}><RefreshCw className="size-4" />{t('common.retry')}</Button>}{(plan.status === 'active' || plan.status === 'completed') && <Button variant="neutral" onClick={() => setRegenerateOpen(true)} disabled={transitionPending}><RefreshCw className="size-4" />{t('plans.regenerate')}</Button>}<Button variant="neutral" onClick={() => void removePlan()} disabled={transitionPending || plan.status === 'generating' || plan.status === 'regenerating'}><Trash2 className="size-4" />{t('common.delete')}</Button></div></div>
      {conflict && <Alert><CircleAlert /><AlertTitle>{t('plans.conflictTitle')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{t('plans.conflictDescription')}</span><Button size="sm" variant="neutral" onClick={() => void reconcile()}>{t('plans.reload')}</Button></AlertDescription></Alert>}
      {plan.is_generation_stale && <Alert><CircleAlert /><AlertTitle>{t('plans.staleTitle')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{t('plans.staleDescription')}</span><Button size="sm" variant="neutral" onClick={() => setRegenerateOpen(true)} disabled={mutationDisabled}>{t('plans.regenerate')}</Button></AlertDescription></Alert>}
      {(plan.status === 'generating' || plan.status === 'regenerating') && <Alert><Loader2 className="animate-spin" /><AlertTitle>{plan.status === 'generating' ? t('plans.generating') : t('plans.regenerating')}</AlertTitle><AlertDescription>{t('plans.generationWait')}</AlertDescription></Alert>}
      {plan.generation_error && !isGenerating && <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('plans.generationFailed')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{plan.generation_error || t('plans.unknownFailure')}</span><Button size="sm" variant="neutral" onClick={() => plan.status === 'failed' ? void transition('retry') : setRegenerateOpen(true)} disabled={transitionPending}><RefreshCw className="size-4" />{plan.status === 'failed' ? t('common.retry') : t('plans.regenerate')}</Button></AlertDescription></Alert>}
      <Card><CardHeader><CardTitle>{t('plans.summary')}</CardTitle></CardHeader><CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4"><div><p className="text-xs font-heading uppercase">{t('plans.progress')}</p><p className="text-2xl font-black">{plan.progress.percent}%</p><p className="text-sm text-muted-foreground">{t('plans.progressValue', { done: plan.progress.done, total: plan.progress.total, percent: plan.progress.percent })}</p></div><div><p className="text-xs font-heading uppercase">{t('plans.targetDate')}</p><p>{plan.target_date || '—'}</p></div><div><p className="text-xs font-heading uppercase">{t('plans.weeklyHours')}</p><p>{plan.weekly_hours ? t('plans.hoursValue', { count: plan.weekly_hours }) : '—'}</p></div><div><p className="text-xs font-heading uppercase">{t('plans.revision')}</p><p>{plan.revision}</p></div></CardContent></Card>
      <Card><CardHeader><CardTitle>{t('plans.addTask')}</CardTitle></CardHeader><CardContent className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_10rem_8rem_9rem_auto]"><Input value={manualTitle} maxLength={300} disabled={mutationDisabled} placeholder={t('plans.taskTitle')} onChange={(event) => setManualTitle(event.target.value)} /><Select value={manualCategory} disabled={mutationDisabled} onValueChange={(value) => setManualCategory(value as PlanTaskCategory)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{categories.map((value) => <SelectItem key={value} value={value}>{t(`plans.category.${value}`)}</SelectItem>)}</SelectContent></Select><Select value={manualPriority} disabled={mutationDisabled} onValueChange={(value) => setManualPriority(value as PlanTaskPriority)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(['high', 'medium', 'low'] as PlanTaskPriority[]).map((value) => <SelectItem key={value} value={value}>{t(`plans.priority.${value}`)}</SelectItem>)}</SelectContent></Select><Input type="date" disabled={mutationDisabled} value={manualDueDate} onChange={(event) => setManualDueDate(event.target.value)} /><Button disabled={mutationDisabled || !manualTitle.trim()} onClick={() => void createTask()}><ClipboardPlus className="size-4" />{t('plans.add')}</Button><textarea className="min-h-20 rounded-base border-2 border-black bg-secondary-background p-3 text-sm lg:col-span-5" disabled={mutationDisabled} value={manualDescription} maxLength={3000} placeholder={t('plans.taskDescription')} onChange={(event) => setManualDescription(event.target.value)} /></CardContent></Card>
      <div className="space-y-6">{categories.map((category) => {
        const tasks = tasksByCategory.get(category) || []
        if (!tasks.length) return null
        return <section key={category} className="space-y-3"><div className="flex items-center justify-between"><h2 className="text-lg font-black">{t(`plans.category.${category}`)}</h2><span className="text-sm text-muted-foreground">{tasks.length}</span></div><div className="space-y-3">{tasks.map((task) => { const index = orderedTasks.findIndex((entry) => entry.id === task.id); return <PlanTaskEditor key={task.id} task={task} disabled={mutationDisabled} reconciliationVersion={reconciliationVersion} canMoveUp={index > 0} canMoveDown={index < orderedTasks.length - 1} onPatch={(patch) => patchTask(task.id, patch)} onDelete={() => removeTask(task.id)} onMove={(direction) => moveTask(task.id, direction)} /> })}</div></section>
      })}</div>
      <RegeneratePlanDialog open={regenerateOpen} pending={transitionPending} onOpenChange={setRegenerateOpen} onConfirm={() => void transition('regenerate')} />
    </div>
  )
}
