import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { CircleAlert, FileText, Loader2, Pencil, RefreshCw, Target, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import {
  deleteJobDescription,
  createJDMatch,
  getJDMatch,
  getJobDescription,
  listJDMatches,
  patchJobDescription,
  reextractJobDescription,
  recomputeJDMatch,
  retryJobDescription,
} from '@/api/jd'
import { listEligibleResumes } from '@/api/plans'
import { JDEditor } from '@/components/jd/JDEditor'
import { JDStatusBadge } from '@/components/jd/JDStatusBadge'
import { MatchResultPanel } from '@/components/jd/MatchResultPanel'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { JDDetail, JDMatchResult, JDPatchInput } from '@/types/jd'
import type { EligibleResume } from '@/types/plans'

function DetailSkeleton() {
  return <div className="space-y-5"><Skeleton className="h-10 w-2/5" /><Skeleton className="h-48 w-full" /><Skeleton className="h-64 w-full" /></div>
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-2"><dt className="text-xs font-heading uppercase">{label}</dt><dd>{children}</dd></div>
}

export function JDDetailPage() {
  const { id = '' } = useParams()
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [jd, setJD] = useState<JDDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [editing, setEditing] = useState(false)
  const [conflict, setConflict] = useState(false)
  const [llmGateOpen, setLlmGateOpen] = useState(false)
  const [eligibleResumes, setEligibleResumes] = useState<EligibleResume[]>([])
  const [resumeId, setResumeId] = useState('')
  const [matching, setMatching] = useState(false)
  const [matchResult, setMatchResult] = useState<JDMatchResult | null>(null)
  const [matchLoading, setMatchLoading] = useState(false)
  const [recomputing, setRecomputing] = useState(false)
  const matchPollingStartedAt = useRef<number | null>(null)
  const pollingStartedAt = useRef<number | null>(null)

  const load = useCallback(async (showLoading = true, clearConflict = true) => {
    if (showLoading) setLoading(true)
    try {
      const response = await getJobDescription(id)
      if (response.code !== 0) throw new Error(response.message || t('jd.loadFailed'))
      setJD(response.data)
      setError(null)
      if (clearConflict) setConflict(false)
    } catch (reason) {
      setError((reason as Error).message || t('jd.loadFailed'))
    } finally {
      if (showLoading) setLoading(false)
    }
  }, [id, t])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (jd?.status !== 'processing') {
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
  }, [jd?.status, load])

  useEffect(() => {
    if (jd?.status !== 'ready') return
    listEligibleResumes().then((response) => {
      if (response.code === 0) setEligibleResumes(response.data.items)
    }).catch(() => undefined)
  }, [jd?.status])

  const loadMatch = useCallback(async (targetResumeId = resumeId, showLoading = true) => {
    if (!jd || jd.status !== 'ready' || !targetResumeId) {
      setMatchResult(null)
      return
    }
    if (showLoading) setMatchLoading(true)
    try {
      const existing = await listJDMatches({ jdId: jd.id, resumeId: targetResumeId, mode: 'hybrid_v2', pageSize: 1 })
      if (existing.code === 0 && existing.data.items.length > 0) {
        const detail = await getJDMatch(existing.data.items[0].id)
        if (detail.code === 0) setMatchResult(detail.data)
      } else {
        setMatchResult(null)
      }
    } catch {
      setMatchResult(null)
    } finally {
      if (showLoading) setMatchLoading(false)
    }
  }, [jd, resumeId])

  useEffect(() => { void loadMatch(resumeId) }, [loadMatch, resumeId])

  useEffect(() => {
    if (!matchResult || !['queued', 'running'].includes(matchResult.status)) {
      matchPollingStartedAt.current = null
      return undefined
    }
    matchPollingStartedAt.current ??= Date.now()
    let stopped = false
    let timer: number | undefined
    const schedule = () => {
      if (stopped || document.visibilityState !== 'visible') return
      const elapsed = Date.now() - (matchPollingStartedAt.current ?? Date.now())
      if (elapsed > 120_000) return
      timer = window.setTimeout(async () => {
        const response = await getJDMatch(matchResult.id)
        if (!stopped && response.code === 0) setMatchResult(response.data)
        schedule()
      }, 2_000)
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
  }, [matchResult])

  const save = async (input: JDPatchInput) => {
    if (!jd) return false
    try {
      const response = await patchJobDescription(jd.id, input)
      if (response.code === 1003) {
        setConflict(true)
        toast.error(t('jd.conflict'))
        return false
      }
      if (response.code !== 0) throw new Error(response.message || t('jd.saveFailed'))
      setJD(response.data)
      toast.success(t('jd.saved'))
      return true
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.saveFailed'))
      return false
    }
  }

  const runCommand = async (kind: 'retry' | 'reextract') => {
    if (!jd) return
    if (kind === 'reextract' && !window.confirm(t('jd.reextractConfirm'))) return
    try {
      const response = kind === 'retry'
        ? await retryJobDescription(jd.id)
        : await reextractJobDescription(jd.id)
      if (response.code === 428) { setLlmGateOpen(true); return }
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      setJD(response.data)
      toast.success(t('jd.importStarted'))
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.actionFailed'))
    }
  }

  const deleteJD = async () => {
    if (!jd || !window.confirm(t('jd.deleteConfirm'))) return
    try {
      const response = await deleteJobDescription(jd.id)
      if (response.code !== 0) throw new Error(response.message || t('jd.deleteFailed'))
      toast.success(t('jd.deleted'))
      navigate('/jobs')
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.deleteFailed'))
    }
  }

  const match = async () => {
    if (!jd || !resumeId || matching) return
    setMatching(true)
    try {
      const response = await createJDMatch({ jdId: jd.id, resumeId })
      if (response.code !== 0) throw new Error(response.message || t('jd.matchFailed'))
      const detail = await getJDMatch(response.data.id)
      if (detail.code === 0) setMatchResult(detail.data)
      await loadMatch(resumeId, false)
      toast.success(t('jd.matchCreated'))
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.matchFailed'))
    } finally {
      setMatching(false)
    }
  }

  const recomputeMatch = async () => {
    if (!matchResult || recomputing) return
    setRecomputing(true)
    try {
      const response = await recomputeJDMatch(matchResult.id)
      if (response.code !== 0) throw new Error(response.message || t('jd.matchFailed'))
      const detail = await getJDMatch(response.data.id)
      if (detail.code === 0) setMatchResult(detail.data)
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.matchFailed'))
    } finally {
      setRecomputing(false)
    }
  }

  if (loading) return <DetailSkeleton />
  if (error || !jd) return <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('jd.loadFailed')}</AlertTitle><AlertDescription className="flex flex-row items-center justify-between gap-3"><span>{error}</span><Button size="sm" variant="neutral" onClick={() => void load()}>{t('common.retry')}</Button></AlertDescription></Alert>

  const isProcessing = jd.status === 'processing'
  return (
    <div className="space-y-6 py-4 sm:py-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <Button asChild variant="neutral" size="sm"><Link to="/jobs">{t('common.back')}</Link></Button>
          <div className="mt-4 flex min-w-0 flex-wrap items-center gap-2"><h1 className="break-words text-3xl font-black">{jd.title || t('jd.untitled')}</h1><JDStatusBadge status={jd.status} /></div>
          <p className="mt-2 break-words text-muted-foreground">{[jd.company, jd.location, jd.seniority ? t(`jd.seniority.${jd.seniority}`, { defaultValue: jd.seniority }) : null].filter(Boolean).join(' · ') || t('jd.noMetadata')}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          {jd.status === 'ready' && <Button variant="neutral" onClick={() => setEditing((value) => !value)}><Pencil className="size-4" />{editing ? t('common.cancel') : t('common.edit')}</Button>}
          {jd.status === 'ready' && <Button variant="neutral" onClick={() => void runCommand('reextract')}><RefreshCw className="size-4" />{t('jd.reextract')}</Button>}
          {jd.status === 'failed' && <Button onClick={() => void runCommand('retry')}><RefreshCw className="size-4" />{t('common.retry')}</Button>}
          <Button variant="neutral" onClick={() => void deleteJD()} disabled={isProcessing}><Trash2 className="size-4" />{t('common.delete')}</Button>
        </div>
      </div>

      {conflict && <Alert><CircleAlert /><AlertTitle>{t('jd.conflictTitle')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{t('jd.conflictDescription')}</span><Button size="sm" variant="neutral" onClick={() => void load()}>{t('jd.reload')}</Button></AlertDescription></Alert>}
      {jd.status === 'failed' && <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('jd.processingFailed')}</AlertTitle><AlertDescription>{jd.processing_error || t('jd.unknownFailure')}</AlertDescription></Alert>}
      {isProcessing && <Alert><Loader2 className="animate-spin" /><AlertTitle>{t('jd.processing')}</AlertTitle><AlertDescription>{t(`jd.step.${jd.processing_step}`, { defaultValue: jd.processing_step })}</AlertDescription></Alert>}
      {jd.status === 'duplicate_pending' && <Alert><CircleAlert /><AlertTitle>{t('jd.duplicateTitle')}</AlertTitle><AlertDescription>{t('jd.duplicateDetail')}</AlertDescription></Alert>}

      {editing ? (
        <Card><CardHeader><CardTitle>{t('jd.editStructured')}</CardTitle></CardHeader><CardContent><JDEditor key={`${jd.id}-${jd.updated_at}`} jd={jd} onSave={save} onCancel={() => setEditing(false)} /></CardContent></Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,.8fr)]">
          <Card className="min-w-0"><CardHeader><CardTitle>{t('jd.structured')}</CardTitle></CardHeader><CardContent><dl className="grid gap-5 sm:grid-cols-2"><FieldGroup label={t('jd.field.title')}>{jd.title || '—'}</FieldGroup><FieldGroup label={t('jd.field.company')}>{jd.company || '—'}</FieldGroup><FieldGroup label={t('jd.field.location')}>{jd.location || '—'}</FieldGroup><FieldGroup label={t('jd.field.seniority')}>{jd.seniority ? t(`jd.seniority.${jd.seniority}`) : '—'}</FieldGroup><FieldGroup label={t('jd.field.requiredSkills')}><div className="flex flex-wrap gap-2">{jd.required_skills.length ? jd.required_skills.map((skill) => <Badge key={skill.name}>{skill.name}{skill.critical ? ` · ${t('jd.critical')}` : ''}</Badge>) : '—'}</div></FieldGroup><FieldGroup label={t('jd.field.preferredSkills')}><div className="flex flex-wrap gap-2">{jd.preferred_skills.length ? jd.preferred_skills.map((skill) => <Badge key={skill.name} variant="neutral">{skill.name}</Badge>) : '—'}</div></FieldGroup><FieldGroup label={t('jd.field.responsibilities')}><ul className="list-disc space-y-1 pl-5 text-sm">{jd.responsibilities.length ? jd.responsibilities.map((value, index) => <li key={`${value}-${index}`}>{value}</li>) : <li>—</li>}</ul></FieldGroup><FieldGroup label={t('jd.provenance')}><div className="space-y-1 text-sm">{Object.entries(jd.field_sources || {}).length ? Object.entries(jd.field_sources).map(([field, source]) => <p key={field}>{t(`jd.field.${field}`, { defaultValue: field })}: <span className="font-heading">{source}</span></p>) : '—'}</div></FieldGroup></dl></CardContent></Card>
          <Card className="min-w-0"><CardHeader><CardTitle>{t('jd.original')}</CardTitle></CardHeader><CardContent><pre className="max-h-[34rem] overflow-auto whitespace-pre-wrap break-words rounded-base border-2 border-black bg-secondary-background p-4 text-sm">{jd.raw_text || '—'}</pre>{jd.source_url && <a className="mt-3 block break-all text-sm font-heading underline" href={jd.source_url} target="_blank" rel="noreferrer">{jd.source_url}</a>}</CardContent></Card>
        </div>
      )}

      {jd.status === 'ready' && <Card><CardHeader><CardTitle className="flex items-center gap-2"><Target className="size-5" />{t('jd.downstream')}</CardTitle></CardHeader><CardContent className="space-y-4"><div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"><Select value={resumeId} onValueChange={setResumeId}><SelectTrigger><SelectValue placeholder={t('jd.selectResume')} /></SelectTrigger><SelectContent>{eligibleResumes.map((resume) => <SelectItem key={resume.id} value={resume.id}>{resume.display_name}</SelectItem>)}</SelectContent></Select><Button onClick={() => void match()} disabled={!resumeId || matching}>{matching && <Loader2 className="size-4 animate-spin" />}{t('jd.match')}</Button></div><MatchResultPanel match={matchResult} loading={matchLoading} recomputing={recomputing} onRecompute={matchResult?.stale ? () => void recomputeMatch() : undefined} /><div className="flex flex-wrap gap-2"><Button asChild variant="neutral"><Link to={`/plans/new?jd_id=${jd.id}`}><FileText className="size-4" />{t('plans.create')}</Link></Button></div></CardContent></Card>}
      <LLMGateDialog open={llmGateOpen} onOpenChange={setLlmGateOpen} description={t('jd.llmGateDescription')} successMessage={t('jd.llmReady')} />
    </div>
  )
}
