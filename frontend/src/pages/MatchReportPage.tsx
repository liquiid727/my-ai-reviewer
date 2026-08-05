import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import {
  ArrowLeft,
  BookOpen,
  CheckCircle2,
  FileText,
  Loader2,
  MessageSquareText,
  RefreshCw,
  Target,
  TriangleAlert,
} from 'lucide-react'
import { toast } from 'sonner'
import { createInterview } from '@/api/interview'
import { createMatchAssessment, getMatchAssessment } from '@/api/match-assessments'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import type { MatchAction, MatchAssessment, MatchReport } from '@/types/match-assessments'

function readableDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

function recommendationColor(recommendation: string | null): string {
  if (recommendation === 'strong_hire') return 'bg-green-100 text-green-800'
  if (recommendation === 'hire') return 'bg-green-100 text-green-800'
  if (recommendation === 'conditional') return 'bg-yellow-100 text-yellow-800'
  return 'bg-red-100 text-red-800'
}

export default function MatchReportPage() {
  const { id, assessmentId } = useParams<{ id: string; assessmentId: string }>()
  const navigate = useNavigate()
  const { t } = useTranslation()

  const [assessment, setAssessment] = useState<MatchAssessment | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [recreating, setRecreating] = useState(false)
  const [startingInterview, setStartingInterview] = useState(false)

  useEffect(() => {
    if (!assessmentId) return
    setLoading(true)
    setError(null)
    getMatchAssessment(assessmentId)
      .then((resp) => setAssessment(resp.data))
      .catch(() => setError(t('match.reportLoadFailed')))
      .finally(() => setLoading(false))
  }, [assessmentId, t])

  async function doRerun() {
    if (!assessment) return
    setRecreating(true)
    try {
      const resp = await createMatchAssessment({
        job_target_id: assessment.job_target_id,
        jd_version_id: assessment.jd_version_id,
        resume_version_id: assessment.resume_version_id,
        force: true,
      })
      const data = resp.data
      if (data.status === 'completed' && data.reused) {
        toast.success(t('match.reusedCompleted'))
      }
      navigate(`/targets/${id}/match/${data.id}`)
    } catch (e: unknown) {
      toast.error((e as { message?: string }).message || t('match.rerunFailed'))
    } finally {
      setRecreating(false)
    }
  }

  async function runAction(action: MatchAction) {
    if (!action.eligible) return
    if (action.id === 'resume_optimization') {
      const draftId = action.destination?.draft_id
      if (draftId) navigate(`/builder/${draftId}`)
      return
    }
    if (action.id === 'plan') {
      const resumeId = action.destination?.resume_id
      const query = resumeId ? `?resume_id=${resumeId}` : ''
      navigate(`/plans/new${query}`)
      return
    }
    if (action.id === 'interview') {
      const resumeId = action.destination?.resume_id
      if (!resumeId) return
      setStartingInterview(true)
      try {
        const resp = await createInterview({ resumeId })
        toast.success(t('match.interviewStarted'))
        navigate(`/interview/${resp.data.interview_id}`)
      } catch (e: unknown) {
        toast.error((e as { message?: string }).message || t('match.interviewFailed'))
      } finally {
        setStartingInterview(false)
      }
    }
  }

  if (loading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 p-6">
        <Skeleton className="h-8 w-1/3" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  if (error || !assessment) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-muted-foreground">{error || t('match.reportNotFound')}</p>
      </div>
    )
  }

  const report: MatchReport | undefined = assessment.report

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div>
        <Button asChild size="sm" variant="neutral">
          <Link to={`/targets/${id}`}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            {t('match.backToTarget')}
          </Link>
        </Button>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">{t('match.reportTitle')}</h1>
            <p className="text-sm text-muted-foreground">
              {report ? `v${report.version_facts.jd_version_no ?? '—'} · ${readableDate(report.completed_at)}` : readableDate(assessment.completed_at)}
            </p>
          </div>
          <Button variant="neutral" onClick={() => void doRerun()} disabled={recreating}>
            <RefreshCw className={`mr-1 h-4 w-4 ${recreating ? 'animate-spin' : ''}`} />
            {t('match.rerun')}
          </Button>
        </div>
      </div>

      {assessment.status === 'failed' && (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>{t('match.assessmentFailed')}</AlertTitle>
          <AlertDescription>{assessment.error_details || t('match.unknownFailure')}</AlertDescription>
        </Alert>
      )}

      {assessment.status !== 'completed' && assessment.status !== 'failed' && (
        <Card>
          <CardContent className="flex items-center gap-3 pt-4">
            <Loader2 className="h-5 w-5 animate-spin" />
            <span className="text-sm">{t('match.statusRunning')}</span>
          </CardContent>
        </Card>
      )}

      {assessment.status === 'completed' && report && (
        <>
          {report.stale.is_stale && (
            <Alert>
              <TriangleAlert />
              <AlertTitle>{t('match.staleTitle')}</AlertTitle>
              <AlertDescription>
                {report.stale.jd.includes('jd_has_newer_published_version') && <span>{t('match.staleJdNewer')}</span>}
                {report.stale.jd.includes('target_default_jd_version_moved') && <span>{t('match.staleJdDefaultMoved')}</span>}
                {report.stale.resume.includes('target_default_resume_version_moved') && <span>{t('match.staleResumeDefaultMoved')}</span>}
              </AlertDescription>
            </Alert>
          )}

          <Card>
            <CardHeader>
              <CardTitle>{t('match.overallScore')}</CardTitle>
              <CardDescription>{t('match.overallScoreDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="flex flex-col items-center gap-4 sm:flex-row sm:justify-center sm:gap-10">
              <ScoreGauge score={(report.scores.total_score ?? 0) / 10} size={170} />
              <div className="space-y-2 text-sm">
                <div className="flex items-center gap-2">
                  <Badge className={recommendationColor(report.scores.recommendation)}>
                    {t(`match.recommendation.${report.scores.recommendation ?? 'conditional'}`)}
                  </Badge>
                </div>
                <p>
                  {t('match.confidence')}: {((report.scores.overall_confidence ?? 0) * 100).toFixed(0)}%
                </p>
                <p>
                  {t('match.beforeCaps')}: {report.scores.score_before_caps?.toFixed(1) ?? '—'}
                </p>
                {report.scores.caps_applied.length > 0 && (
                  <p>
                    {t('match.capsApplied')}: {report.scores.caps_applied.join(', ')}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('match.dimensions')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {report.dimensions.map((dim) => (
                <div key={dim.key} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{t(`match.dimension.${dim.key}`)}</span>
                    <span className="text-muted-foreground">{dim.raw_score?.toFixed(1)} / 100</span>
                  </div>
                  <div className="h-2 w-full overflow-hidden rounded-full bg-secondary">
                    <div
                      className="h-full rounded-full bg-primary"
                      style={{ width: `${Math.min(Math.max(dim.raw_score ?? 0, 0), 100)}%` }}
                    />
                  </div>
                  {dim.explanation && <p className="text-xs text-muted-foreground">{dim.explanation}</p>}
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('match.gaps')}</CardTitle>
              <CardDescription>{t('match.gapsDesc')}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              {Object.entries(report.gap_classes.counts_by_class).map(([key, count]) => (
                <div key={key} className="flex items-center justify-between">
                  <span>{t(`match.gapClass.${key}`)}</span>
                  <span className="font-medium">{count}</span>
                </div>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('match.evidence')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                {t('match.evidenceJd')}: {report.evidence_sufficiency.jd_evidence} ·{' '}
                {t('match.evidenceResume')}: {report.evidence_sufficiency.resume_evidence}
              </p>
              {report.evidence_sufficiency.unknown_citations.length > 0 && (
                <Alert variant="default">
                  <TriangleAlert />
                  <AlertTitle>{t('match.unknownEvidenceTitle')}</AlertTitle>
                  <AlertDescription className="break-all">
                    {report.evidence_sufficiency.unknown_citations.map((item) => (
                      <span key={item} className="block text-xs">
                        {item}
                      </span>
                    ))}
                  </AlertDescription>
                </Alert>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>{t('match.nextSteps')}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-3">
              {report.actions.map((action) => {
                const Icon = action.id === 'resume_optimization' ? Target : action.id === 'plan' ? FileText : MessageSquareText
                return (
                  <Button
                    key={action.id}
                    variant={action.id === 'interview' ? 'default' : 'neutral'}
                    onClick={() => void runAction(action)}
                    disabled={!action.eligible || startingInterview}
                  >
                    {startingInterview && action.id === 'interview' ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Icon className="mr-1 h-4 w-4" />}
                    {action.id === 'resume_optimization' ? t('match.actionOptimize') : action.id === 'plan' ? t('match.actionPlan') : t('match.actionInterview')}
                  </Button>
                )
              })}
              {report.actions.length === 0 && <p className="text-sm text-muted-foreground">{t('match.noActions')}</p>}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <BookOpen className="h-4 w-4" />
                {t('match.versionFacts')}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1 text-xs text-muted-foreground">
              <p>JD v{report.version_facts.jd_version_no ?? '—'} · {report.version_facts.jd_version_id}</p>
              <p>{report.version_facts.resume_version_source_type} · {report.version_facts.resume_version_id}</p>
              {report.model.name && (
                <p>
                  {report.model.name} {report.model.version ?? ''} · {report.model.prompt_version ?? ''}
                </p>
              )}
            </CardContent>
          </Card>
        </>
      )}

      {assessment.status === 'completed' && !report && (
        <Card>
          <CardContent className="flex items-center gap-3 pt-4">
            <CheckCircle2 className="h-5 w-5 text-green-600" />
            <span className="text-sm">{t('match.statusCompleted')}</span>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
