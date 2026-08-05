import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { ArrowLeft, CheckCircle2, Loader2, RefreshCw, TriangleAlert } from 'lucide-react'
import { toast } from 'sonner'
import { createMatchAssessment, getMatchAssessment, retryMatchAssessment } from '@/api/match-assessments'
import { getJobTarget, listJdVersions, listResumeVersions } from '@/api/job-targets'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { JobTargetDetail, JdVersionSummary, ResumeVersionSummary } from '@/types/job-targets'
import type { MatchAssessment } from '@/types/match-assessments'

function readableDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

export default function MatchCreatePage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [target, setTarget] = useState<JobTargetDetail | null>(null)
  const [jdVersions, setJdVersions] = useState<JdVersionSummary[]>([])
  const [resumeVersions, setResumeVersions] = useState<ResumeVersionSummary[]>([])
  const [jdVersionId, setJdVersionId] = useState('')
  const [resumeVersionId, setResumeVersionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [conflictError, setConflictError] = useState<string | null>(null)

  const [assessment, setAssessment] = useState<MatchAssessment | null>(null)
  const [polling, setPolling] = useState(false)
  const pollTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    getJobTarget(id)
      .then((resp) => {
        const data = resp.data
        setTarget(data)
        setJdVersionId(data.default_jd_version_id ?? '')
        setResumeVersionId(data.default_resume_version_id ?? '')
        if (data.job_description_id) {
          return listJdVersions(data.job_description_id).then((r) => {
            setJdVersions(r.data.versions)
            return listResumeVersions().then((rv) => setResumeVersions(rv.data.versions))
          })
        }
        return undefined
      })
      .catch(() => setError(t('common.loading')))
      .finally(() => setLoading(false))
  }, [id, t])

  useEffect(() => {
    return () => {
      if (pollTimer.current) clearTimeout(pollTimer.current)
    }
  }, [])

  async function pollUntilTerminal(assessmentId: string) {
    setPolling(true)
    const tick = async () => {
      try {
        const resp = await getMatchAssessment(assessmentId)
        setAssessment(resp.data)
        if (resp.data.status === 'completed') {
          setPolling(false)
          toast.success(t('match.assessmentCompleted'))
          navigate(`/targets/${id}/match/${resp.data.id}`, { replace: true })
          return
        }
        if (resp.data.status === 'failed') {
          setPolling(false)
          return
        }
        pollTimer.current = setTimeout(tick, 2000)
      } catch {
        setPolling(false)
        toast.error(t('match.pollFailed'))
      }
    }
    void tick()
  }

  async function doSubmit() {
    if (!target || !jdVersionId || !resumeVersionId || submitting) return
    setSubmitting(true)
    setConflictError(null)
    try {
      const resp = await createMatchAssessment({
        job_target_id: target.id,
        jd_version_id: jdVersionId,
        resume_version_id: resumeVersionId,
      })
      const data = resp.data
      if (data.reused && data.status === 'completed') {
        toast.success(t('match.reusedCompleted'))
        navigate(`/targets/${target.id}/match/${data.id}`)
        return
      }
      setAssessment({ ...data, result: null, created_at: null, updated_at: null, completed_at: null })
      await pollUntilTerminal(data.id)
    } catch (e: unknown) {
      const err = e as { code?: number; message?: string; status?: number }
      if (err.code === 409 || err.status === 409) {
        setConflictError(t('match.activeExists'))
      } else if (err.code === 422 || err.status === 422) {
        setConflictError(t('match.versionsInvalid'))
      } else {
        toast.error(err.message || t('match.createFailed'))
      }
      setSubmitting(false)
    }
  }

  async function doRetry() {
    if (!assessment || submitting) return
    setSubmitting(true)
    setConflictError(null)
    try {
      const resp = await retryMatchAssessment(assessment.id)
      setAssessment({ ...resp.data, result: null, created_at: null, updated_at: null, completed_at: null })
      await pollUntilTerminal(resp.data.id)
    } catch (e: unknown) {
      toast.error((e as { message?: string }).message || t('match.retryFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error || !target) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-muted-foreground">{error || t('match.targetMissing')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <Button asChild size="sm" variant="neutral">
          <Link to={`/targets/${target.id}`}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('match.backToTarget')}
          </Link>
        </Button>
        <h1 className="mt-4 text-2xl font-semibold">{t('match.createTitle')}</h1>
        <p className="text-sm text-muted-foreground">{t('match.createSubtitle')}</p>
      </div>

      {conflictError && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 pt-4">
            <TriangleAlert className="h-4 w-4 text-destructive" />
            <span className="text-sm">{conflictError}</span>
          </CardContent>
        </Card>
      )}

      {!assessment && (
        <Card>
          <CardHeader>
            <CardTitle>{t('match.pinnedVersions')}</CardTitle>
            <CardDescription>{t('match.pinnedVersionsDesc')}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('match.jdVersion')}</label>
              <Select value={jdVersionId || undefined} onValueChange={setJdVersionId} disabled={submitting}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t('match.selectJdVersion')} />
                </SelectTrigger>
                <SelectContent>
                  {jdVersions.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      v{v.version_no} · {readableDate(v.published_at)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {jdVersions.length === 0 && <p className="text-sm text-muted-foreground">{t('match.noJdVersions')}</p>}
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">{t('match.resumeVersion')}</label>
              <Select value={resumeVersionId || undefined} onValueChange={setResumeVersionId} disabled={submitting}>
                <SelectTrigger className="w-full">
                  <SelectValue placeholder={t('match.selectResumeVersion')} />
                </SelectTrigger>
                <SelectContent>
                  {resumeVersions.map((v) => (
                    <SelectItem key={v.id} value={v.id}>
                      {v.source_type} · {readableDate(v.published_at)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {resumeVersions.length === 0 && <p className="text-sm text-muted-foreground">{t('match.noResumeVersions')}</p>}
            </div>
            <div className="flex justify-end">
              <Button onClick={() => void doSubmit()} disabled={!jdVersionId || !resumeVersionId || submitting}>
                {submitting && <Loader2 className="mr-1 h-4 w-4 animate-spin" />}
                {t('match.startAssessment')}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {assessment && (
        <Card>
          <CardHeader>
            <CardTitle>{t('match.assessmentStatus')}</CardTitle>
            <CardDescription>
              v{assessment.attempt} · {readableDate(assessment.created_at)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {assessment.status === 'queued' && (
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">{t('match.statusQueued')}</span>
              </div>
            )}
            {assessment.status === 'evaluating' && (
              <div className="flex items-center gap-3">
                <Loader2 className="h-5 w-5 animate-spin" />
                <span className="text-sm">{t('match.statusEvaluating')}</span>
              </div>
            )}
            {assessment.status === 'completed' && (
              <div className="flex items-center gap-3 text-green-600">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-sm">{t('match.statusCompleted')}</span>
              </div>
            )}
            {assessment.status === 'failed' && (
              <div className="space-y-3">
                <div className="flex items-center gap-3">
                  <TriangleAlert className="h-5 w-5 text-destructive" />
                  <span className="text-sm">{t('match.statusFailed')}</span>
                </div>
                {assessment.error_details && (
                  <p className="text-sm text-muted-foreground">{assessment.error_details}</p>
                )}
                {assessment.retryable && (
                  <Button variant="neutral" onClick={() => void doRetry()} disabled={submitting}>
                    <RefreshCw className="mr-1 h-4 w-4" />
                    {t('match.retry')}
                  </Button>
                )}
              </div>
            )}
            {polling && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
