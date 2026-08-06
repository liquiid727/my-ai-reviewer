import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  Archive,
  CircleAlert,
  FileText,
  History,
  Loader2,
  Pencil,
  RefreshCw,
  Send,
  Target,
  Trash2,
  X,
} from 'lucide-react'
import { toast } from 'sonner'
import {
  abandonJDDraft,
  archiveJobDescription,
  deleteJobDescription,
  createJDMatch,
  getJDMatch,
  getJobDescription,
  getJDVersion,
  listJDMatches,
  listJDVersions,
  patchJobDescription,
  publishJDVersion,
  recomputeJDMatch,
  reextractJobDescription,
  reparseJobDescription,
  retryJobDescription,
  saveJDReviewDraft,
} from '@/api/jd'
import { listEligibleResumes } from '@/api/plans'
import { JDEditor } from '@/components/jd/JDEditor'
import { JDReviewEditor } from '@/components/jd/JDReviewEditor'
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
import type { JDDetail, JDMatchResult, JDPatchInput, JDReviewDraft, JDVersionDetail, JDVersionSummary } from '@/types/jd'
import type { EligibleResume } from '@/types/plans'

function DetailSkeleton() {
  return <div className="space-y-5"><Skeleton className="h-10 w-2/5" /><Skeleton className="h-48 w-full" /><Skeleton className="h-64 w-full" /></div>
}

function FieldGroup({ label, children }: { label: string; children: React.ReactNode }) {
  return <div className="space-y-2"><dt className="text-xs font-heading uppercase">{label}</dt><dd>{children}</dd></div>
}

function DraftItemRow({ item }: { item: { value: string; evidence?: string | null; confidence?: number; provenance?: string } }) {
  const { t } = useTranslation()
  const manual = item.provenance === 'manual'
  return (
    <li className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <span>{item.value}</span>
        {manual && <Badge variant="neutral" className="text-[10px]">{t('jd.manualEdits')}</Badge>}
        {typeof item.confidence === 'number' && item.confidence < 0.7 && (
          <Badge className="bg-amber-300 text-amber-950 border-amber-700 text-[10px]">{t('jd.confidence')}: {Math.round(item.confidence * 100)}%</Badge>
        )}
      </div>
      {item.evidence && <p className="text-xs text-muted-foreground">“{item.evidence}”</p>}
    </li>
  )
}

function DraftView({ draft }: { draft: JDReviewDraft }) {
  const { t } = useTranslation()
  const meta = [draft.company, draft.department, draft.location, draft.employment_type && t(`jd.employmentType.${draft.employment_type}`), draft.seniority && t(`jd.seniority.${draft.seniority}`)].filter(Boolean)
  const compensation = draft.compensation?.currency
    ? `${draft.compensation.currency}${draft.compensation.min_amount ?? ''}${draft.compensation.max_amount ? ` - ${draft.compensation.max_amount}` : ''}${draft.compensation.period ? `/${draft.compensation.period}` : ''}`
    : null
  const scalars: Array<[string, string | null]> = [
    [t('jd.field.minimumYears'), draft.minimum_years != null ? String(draft.minimum_years) : null],
    [t('jd.field.preferredYears'), draft.preferred_years != null ? String(draft.preferred_years) : null],
    [t('jd.field.education'), draft.education || null],
    [t('jd.field.locationConstraint'), draft.location_constraint || null],
    [t('jd.field.domainContext'), draft.domain_context || null],
    [t('jd.field.industryContext'), draft.industry_context || null],
  ]
  return (
    <div className="space-y-4">
      {meta.length > 0 && <p className="text-sm text-muted-foreground">{meta.join(' · ')}</p>}
      <dl className="grid gap-4 sm:grid-cols-2">
        {scalars.filter(([, value]) => value).map(([label, value]) => <FieldGroup key={label} label={label}>{value}</FieldGroup>)}
        {compensation && <FieldGroup label={t('jd.field.compensation')}>{compensation}</FieldGroup>}
        {draft.languages?.length ? <FieldGroup label={t('jd.field.languages')}><div className="flex flex-wrap gap-2">{draft.languages.map((lang) => <Badge key={lang} variant="neutral">{lang}</Badge>)}</div></FieldGroup> : null}
        {draft.certificates?.length ? <FieldGroup label={t('jd.field.certificates')}><div className="flex flex-wrap gap-2">{draft.certificates.map((cert) => <Badge key={cert} variant="neutral">{cert}</Badge>)}</div></FieldGroup> : null}
        {draft.interview_clues?.length ? <FieldGroup label={t('jd.field.interviewClues')}><ul className="list-disc space-y-1 pl-5 text-sm">{draft.interview_clues.map((clue) => <li key={clue}>{clue}</li>)}</ul></FieldGroup> : null}
      </dl>
      {draft.hard_conditions?.length ? (
        <FieldGroup label={t('jd.field.hardConditions')}><ul className="space-y-2">{draft.hard_conditions.map((item) => <DraftItemRow key={item.key} item={item} />)}</ul></FieldGroup>
      ) : null}
      <FieldGroup label={t('jd.field.responsibilities')}><ul className="space-y-2">{draft.responsibilities?.length ? draft.responsibilities.map((item) => <DraftItemRow key={item.key} item={item} />) : <li>—</li>}</ul></FieldGroup>
      <FieldGroup label={t('jd.field.requiredSkills')}><ul className="space-y-2">{draft.required_skills?.length ? draft.required_skills.map((item) => <DraftItemRow key={item.key} item={item} />) : <li>—</li>}</ul></FieldGroup>
      <FieldGroup label={t('jd.field.preferredSkills')}><ul className="space-y-2">{draft.preferred_skills?.length ? draft.preferred_skills.map((item) => <DraftItemRow key={item.key} item={item} />) : <li>—</li>}</ul></FieldGroup>
      {draft.notes ? <p className="text-sm italic text-muted-foreground">{draft.notes}</p> : null}
    </div>
  )
}

function VersionDetail({ detail }: { detail: JDVersionDetail | null }) {
  const { t } = useTranslation()
  const structured = (detail?.structured ?? {}) as Partial<JDReviewDraft>
  const hasStructured = Object.keys(structured).length > 0
  return (
    <div className="space-y-4">
      {detail && <p className="text-xs text-muted-foreground">{t('jd.readOnlyVersion')} · {t('jd.publishedOn', { date: detail.published_at || '—' })}</p>}
      {hasStructured ? <DraftView draft={structured as JDReviewDraft} /> : <p className="text-sm text-muted-foreground">—</p>}
      {detail?.normalized_text && <Card className="min-w-0"><CardHeader><CardTitle>{t('jd.original')}</CardTitle></CardHeader><CardContent><pre className="max-h-72 overflow-auto whitespace-pre-wrap break-words rounded-base border-2 border-black bg-secondary-background p-4 text-sm">{detail.normalized_text}</pre></CardContent></Card>}
    </div>
  )
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
  const [versions, setVersions] = useState<JDVersionSummary[] | null>(null)
  const [versionsError, setVersionsError] = useState<string | null>(null)
  const [versionDetail, setVersionDetail] = useState<JDVersionDetail | null>(null)
  const [publishing, setPublishing] = useState(false)
  const [reparsing, setReparsing] = useState(false)
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

  const loadVersions = useCallback(async (showDetail = true) => {
    try {
      const response = await listJDVersions(id)
      if (response.code !== 0) throw new Error(response.message || t('jd.versionLoadFailed'))
      setVersions(response.data.versions)
      setVersionsError(null)
      if (showDetail && response.data.versions.length > 0 && jd?.current_version_id) {
        const current = response.data.versions.find((version) => version.id === jd.current_version_id)
        if (current) {
          const detailResponse = await getJDVersion(id, current.id)
          if (detailResponse.code === 0) setVersionDetail(detailResponse.data)
        }
      }
    } catch (reason) {
      setVersionsError((reason as Error).message || t('jd.versionLoadFailed'))
    }
  }, [id, jd?.current_version_id, t])

  useEffect(() => { void loadVersions() }, [loadVersions])

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

  const saveReview = async (draft: JDReviewDraft) => {
    if (!jd) return false
    try {
      const response = await saveJDReviewDraft(jd.id, {
        expected_review_revision: jd.review_revision,
        draft,
      })
      if (response.code === 409) {
        setConflict(true)
        toast.error(t('jd.conflict'))
        return false
      }
      if (response.code !== 0) throw new Error(response.message || t('jd.saveFailed'))
      setJD(response.data)
      setConflict(false)
      toast.success(t('jd.saved'))
      return true
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.saveFailed'))
      return false
    }
  }

  const publish = async () => {
    if (!jd || publishing) return
    setPublishing(true)
    try {
      const response = await publishJDVersion(jd.id, { expected_review_revision: jd.review_revision })
      if (response.code === 409) {
        setConflict(true)
        toast.error(t('jd.publishConflict'))
        return
      }
      if (response.code !== 0) throw new Error(response.message || t('jd.publishFailed'))
      toast.success(t('jd.published', { version: response.data.version_no }))
      await load()
      await loadVersions(false)
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.publishFailed'))
    } finally {
      setPublishing(false)
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

  const reparse = async () => {
    if (!jd || reparsing) return
    if (!window.confirm(t('jd.reparseConfirm'))) return
    setReparsing(true)
    try {
      const response = await reparseJobDescription(jd.id)
      if (response.code === 428) { setLlmGateOpen(true); return }
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      toast.success(t('jd.reparseStarted'))
      await load()
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.actionFailed'))
    } finally {
      setReparsing(false)
    }
  }

  const abandon = async () => {
    if (!jd) return
    if (!window.confirm(t('jd.abandonDraftConfirm'))) return
    try {
      const response = await abandonJDDraft(jd.id)
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      toast.success(t('jd.draftAbandoned'))
      await load()
    } catch (reason) {
      toast.error((reason as Error).message || t('jd.actionFailed'))
    }
  }

  const archive = async () => {
    if (!jd) return
    if (!window.confirm(t('jd.archiveConfirm'))) return
    try {
      const response = await archiveJobDescription(jd.id)
      if (response.code !== 0) throw new Error(response.message || t('jd.actionFailed'))
      toast.success(t('jd.archivedJd'))
      await load()
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
  const draft = jd.review_draft
  const hasVersion = jd.current_version_id !== null
  return (
    <div className="space-y-6 py-4 sm:py-8">
      <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="min-w-0">
          <Button asChild variant="neutral" size="sm"><Link to="/jobs">{t('common.back')}</Link></Button>
          <div className="mt-4 flex min-w-0 flex-wrap items-center gap-2"><h1 className="break-words text-3xl font-black">{jd.title || t('jd.untitled')}</h1><JDStatusBadge status={jd.status} /></div>
          <p className="mt-2 break-words text-muted-foreground">{[jd.company, jd.location, jd.seniority ? t(`jd.seniority.${jd.seniority}`, { defaultValue: jd.seniority }) : null].filter(Boolean).join(' · ') || t('jd.noMetadata')}</p>
          {hasVersion && <p className="mt-2 text-sm font-heading text-muted-foreground">{t('jd.currentVersion')} · v{versions?.find((version) => version.id === jd.current_version_id)?.version_no ?? '?'}</p>}
        </div>
        <div className="flex flex-wrap gap-2">
          {jd.status === 'ready' && !isProcessing && <Button variant="neutral" onClick={() => setEditing((value) => !value)}><Pencil className="size-4" />{editing ? t('common.cancel') : t('common.edit')}</Button>}
          {jd.status === 'ready' && !isProcessing && <Button variant="neutral" onClick={() => void reparse()} disabled={reparsing}><RefreshCw className="size-4" />{t('jd.reparse')}</Button>}
          {jd.status === 'failed' && <Button onClick={() => void runCommand('retry')}><RefreshCw className="size-4" />{t('common.retry')}</Button>}
          {jd.status === 'needs_review' && <Button variant="neutral" onClick={() => void abandon()}><X className="size-4" />{t('jd.abandonDraft')}</Button>}
          {!['archived', 'processing'].includes(jd.status) && <Button variant="neutral" onClick={() => void archive()}><Archive className="size-4" />{t('jd.archive')}</Button>}
          <Button variant="neutral" onClick={() => void deleteJD()} disabled={isProcessing}><Trash2 className="size-4" />{t('common.delete')}</Button>
        </div>
      </div>

      {conflict && <Alert><CircleAlert /><AlertTitle>{t('jd.conflictTitle')}</AlertTitle><AlertDescription className="flex flex-row flex-wrap items-center justify-between gap-3"><span>{t('jd.conflictDescription')}</span><Button size="sm" variant="neutral" onClick={() => void load()}>{t('jd.reload')}</Button></AlertDescription></Alert>}
      {jd.status === 'failed' && <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('jd.processingFailed')}</AlertTitle><AlertDescription>{jd.review_error || jd.processing_error || t('jd.unknownFailure')}</AlertDescription></Alert>}
      {isProcessing && <Alert><Loader2 className="animate-spin" /><AlertTitle>{t('jd.reprocessing')}</AlertTitle><AlertDescription>{hasVersion ? t('jd.reprocessingDetail') : t('jd.processing')} · {t(`jd.step.${jd.processing_step}`, { defaultValue: jd.processing_step })}</AlertDescription></Alert>}
      {jd.status === 'duplicate_pending' && <Alert><CircleAlert /><AlertTitle>{t('jd.duplicateTitle')}</AlertTitle><AlertDescription>{t('jd.duplicateDetail')}</AlertDescription></Alert>}
      {jd.status === 'archived' && <Alert><Archive /><AlertTitle>{t('jd.archivedJd')}</AlertTitle><AlertDescription>{t('jd.status.archived')}</AlertDescription></Alert>}
      {jd.status === 'needs_review' && !draft && <Alert><CircleAlert /><AlertTitle>{t('jd.reviewRequired')}</AlertTitle><AlertDescription>{t('jd.reviewRequiredDetail')}</AlertDescription></Alert>}

      {jd.status === 'needs_review' && draft ? (
        <Card className="min-w-0"><CardHeader><CardTitle className="flex items-center gap-2"><Send className="size-5" />{t('jd.reviewTitle')}</CardTitle></CardHeader><CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{t('jd.reviewIntro')}</p>
          <JDReviewEditor jd={jd} onSave={saveReview} />
          <div className="flex flex-wrap justify-end gap-2">
            <Button variant="neutral" onClick={() => void abandon()}><X className="size-4" />{t('jd.abandonDraft')}</Button>
            <Button onClick={() => void publish()} disabled={publishing}>{publishing && <Loader2 className="size-4 animate-spin" />}{t('jd.publish')}</Button>
          </div>
        </CardContent></Card>
      ) : editing ? (
        <Card><CardHeader><CardTitle>{t('jd.editStructured')}</CardTitle></CardHeader><CardContent><JDEditor key={`${jd.id}-${jd.updated_at}`} jd={jd} onSave={save} onCancel={() => setEditing(false)} /></CardContent></Card>
      ) : (
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(20rem,.8fr)]">
          <Card className="min-w-0"><CardHeader><CardTitle>{draft ? t('jd.reviewDraft') : t('jd.structured')}</CardTitle></CardHeader><CardContent>{draft ? <DraftView draft={draft} /> : <dl className="grid gap-5 sm:grid-cols-2"><FieldGroup label={t('jd.field.title')}>{jd.title || '—'}</FieldGroup><FieldGroup label={t('jd.field.company')}>{jd.company || '—'}</FieldGroup><FieldGroup label={t('jd.field.location')}>{jd.location || '—'}</FieldGroup><FieldGroup label={t('jd.field.seniority')}>{jd.seniority ? t(`jd.seniority.${jd.seniority}`) : '—'}</FieldGroup><FieldGroup label={t('jd.field.requiredSkills')}><div className="flex flex-wrap gap-2">{jd.required_skills.length ? jd.required_skills.map((skill) => <Badge key={skill.name}>{skill.name}{skill.critical ? ` · ${t('jd.critical')}` : ''}</Badge>) : '—'}</div></FieldGroup><FieldGroup label={t('jd.field.preferredSkills')}><div className="flex flex-wrap gap-2">{jd.preferred_skills.length ? jd.preferred_skills.map((skill) => <Badge key={skill.name} variant="neutral">{skill.name}</Badge>) : '—'}</div></FieldGroup><FieldGroup label={t('jd.field.responsibilities')}><ul className="list-disc space-y-1 pl-5 text-sm">{jd.responsibilities.length ? jd.responsibilities.map((value, index) => <li key={`${value}-${index}`}>{value}</li>) : <li>—</li>}</ul></FieldGroup><FieldGroup label={t('jd.provenance')}><div className="space-y-1 text-sm">{Object.entries(jd.field_sources || {}).length ? Object.entries(jd.field_sources).map(([field, source]) => <p key={field}>{t(`jd.field.${field}`, { defaultValue: field })}: <span className="font-heading">{source}</span></p>) : '—'}</div></FieldGroup></dl>}</CardContent></Card>
          <Card className="min-w-0"><CardHeader><CardTitle>{t('jd.original')}</CardTitle></CardHeader><CardContent><pre className="max-h-[34rem] overflow-auto whitespace-pre-wrap break-words rounded-base border-2 border-black bg-secondary-background p-4 text-sm">{jd.raw_text || '—'}</pre>{jd.source_url && <a className="mt-3 block break-all text-sm font-heading underline" href={jd.source_url} target="_blank" rel="noreferrer">{jd.source_url}</a>}</CardContent></Card>
        </div>
      )}

      <Card className="min-w-0"><CardHeader><CardTitle className="flex items-center gap-2"><History className="size-5" />{t('jd.versionHistory')}</CardTitle></CardHeader><CardContent className="space-y-4">
        {versionsError && <Alert variant="destructive"><CircleAlert /><AlertTitle>{t('jd.versionLoadFailed')}</AlertTitle></Alert>}
        {!versionsError && versions !== null && versions.length === 0 && <p className="text-sm text-muted-foreground">{t('jd.noVersions')}</p>}
        {!versionsError && versions !== null && versions.length > 0 && (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2">
              {versions.map((version) => (
                <Button
                  key={version.id}
                  size="sm"
                  variant={jd.current_version_id === version.id ? undefined : 'neutral'}
                  onClick={() => { void getJDVersion(id, version.id).then((response) => { if (response.code === 0) setVersionDetail(response.data) }) }}
                  disabled={!jd.current_version_id}
                >
                  {t('jd.versionNo', { no: version.version_no })}
                  {jd.current_version_id === version.id && <Badge className="ml-1 bg-green-400 text-green-950 border-green-700">{t('jd.currentVersion')}</Badge>}
                </Button>
              ))}
            </div>
            <VersionDetail detail={versionDetail} />
          </div>
        )}
      </CardContent></Card>

      {jd.status === 'ready' && <Card><CardHeader><CardTitle className="flex items-center gap-2"><Target className="size-5" />{t('jd.downstream')}</CardTitle></CardHeader><CardContent className="space-y-4"><div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_auto]"><Select value={resumeId} onValueChange={setResumeId}><SelectTrigger><SelectValue placeholder={t('jd.selectResume')} /></SelectTrigger><SelectContent>{eligibleResumes.map((resume) => <SelectItem key={resume.id} value={resume.id}>{resume.display_name}</SelectItem>)}</SelectContent></Select><Button onClick={() => void match()} disabled={!resumeId || matching}>{matching && <Loader2 className="size-4 animate-spin" />}{t('jd.match')}</Button></div><MatchResultPanel match={matchResult} loading={matchLoading} recomputing={recomputing} onRecompute={matchResult?.stale ? () => void recomputeMatch() : undefined} /><div className="flex flex-wrap gap-2"><Button asChild variant="neutral"><Link to={`/plans/new?jd_id=${jd.id}`}><FileText className="size-4" />{t('plans.create')}</Link></Button></div></CardContent></Card>}
      <LLMGateDialog open={llmGateOpen} onOpenChange={setLlmGateOpen} description={t('jd.llmGateDescription')} successMessage={t('jd.llmReady')} />
    </div>
  )
}
