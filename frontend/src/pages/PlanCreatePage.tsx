import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { CircleAlert, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { listJobDescriptions } from '@/api/jd'
import { createPlan, listEligibleResumes } from '@/api/plans'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { JDListItem } from '@/types/jd'
import type { EligibleResume } from '@/types/plans'

type PagedOptions<T> = {
  code: number
  message: string
  data: { items: T[]; total: number }
}

async function collectAllOptions<T>(loadPage: (page: number) => Promise<PagedOptions<T>>): Promise<T[]> {
  const items: T[] = []
  let page = 1
  let total = 0
  do {
    const response = await loadPage(page)
    if (response.code !== 0) throw new Error(response.message)
    items.push(...response.data.items)
    total = response.data.total
    page += 1
    if (response.data.items.length === 0) break
  } while (items.length < total)
  return items
}

function localDate() {
  const current = new Date()
  return `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}-${String(current.getDate()).padStart(2, '0')}`
}

function maxDate() {
  const current = new Date()
  current.setDate(current.getDate() + 365)
  return `${current.getFullYear()}-${String(current.getMonth() + 1).padStart(2, '0')}-${String(current.getDate()).padStart(2, '0')}`
}

export function PlanCreatePage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [jds, setJDs] = useState<JDListItem[]>([])
  const [resumes, setResumes] = useState<EligibleResume[]>([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [selectionError, setSelectionError] = useState<string | null>(null)
  const [jdId, setJDId] = useState('')
  const [resumeId, setResumeId] = useState('')
  const [jobTargetId, setJobTargetId] = useState('')
  const [jdVersionId, setJdVersionId] = useState('')
  const [resumeVersionId, setResumeVersionId] = useState('')
  const [matchAssessmentId, setMatchAssessmentId] = useState('')
  const [title, setTitle] = useState('')
  const [targetDate, setTargetDate] = useState('')
  const [weeklyHours, setWeeklyHours] = useState('')
  const [background, setBackground] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [llmGateOpen, setLlmGateOpen] = useState(false)

  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const [readyJDs, eligibleResumes] = await Promise.all([
          collectAllOptions((page) => listJobDescriptions({ status: 'ready', page, pageSize: 100 })),
          collectAllOptions((page) => listEligibleResumes({ page, pageSize: 100 })),
        ])
        if (!active) return
        setJDs(readyJDs)
        setResumes(eligibleResumes)
        const requestedJD = params.get('jd_id')
        const requestedResume = params.get('resume_id')
        setJobTargetId(params.get('job_target_id') ?? '')
        setJdVersionId(params.get('jd_version_id') ?? '')
        setResumeVersionId(params.get('resume_version_id') ?? '')
        setMatchAssessmentId(params.get('match_assessment_id') ?? '')
        const invalid = (requestedJD && !readyJDs.some((item) => item.id === requestedJD)) || (requestedResume && !eligibleResumes.some((item) => item.id === requestedResume))
        setSelectionError(invalid ? t('plans.invalidPreselection') : null)
        if (requestedJD && readyJDs.some((item) => item.id === requestedJD)) setJDId(requestedJD)
        if (requestedResume && eligibleResumes.some((item) => item.id === requestedResume)) setResumeId(requestedResume)
        setLoadError(null)
      } catch (reason) {
        if (active) setLoadError((reason as Error).message || t('plans.optionsLoadFailed'))
      } finally {
        if (active) setLoading(false)
      }
    })()
    return () => { active = false }
  }, [params, t])

  const validationError = useMemo(() => {
    if (targetDate && (targetDate < localDate() || targetDate > maxDate())) return t('plans.targetDateRange')
    const hours = weeklyHours ? Number(weeklyHours) : undefined
    if (hours !== undefined && (!Number.isInteger(hours) || hours < 1 || hours > 80)) return t('plans.weeklyHoursRange')
    if (background.length > 10_000) return t('plans.backgroundTooLong')
    return null
  }, [background.length, targetDate, t, weeklyHours])

  const valid = Boolean(jdId && resumeId && !validationError && !loading && !loadError)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!valid || submitting) return
    setSubmitting(true)
    try {
      const response = await createPlan({
        jd_id: jdId,
        resume_id: resumeId,
        title: title.trim() || undefined,
        target_date: targetDate || undefined,
        weekly_hours: weeklyHours ? Number(weeklyHours) : undefined,
        supplemental_background: background.trim() || undefined,
        job_target_id: jobTargetId || undefined,
        jd_version_id: jdVersionId || undefined,
        resume_version_id: resumeVersionId || undefined,
        match_assessment_id: matchAssessmentId || undefined,
      })
      if (response.code === 428) { setLlmGateOpen(true); return }
      if (response.code === 5004 && response.data?.id) {
        toast.error(response.message || t('plans.createFailed'))
        navigate(`/plans/${response.data.id}`)
        return
      }
      if (response.code === 1006) {
        const existingId = (response.data as { plan_id?: string; id?: string } | undefined)?.plan_id || (response.data as { id?: string } | undefined)?.id
        if (existingId) {
          toast.error(t('plans.duplicatePlan'))
          navigate(`/plans/${existingId}`)
          return
        }
      }
      if (response.code !== 0) throw new Error(response.message || t('plans.createFailed'))
      toast.success(t('plans.generationStarted'))
      navigate(`/plans/${response.data.id}`)
    } catch (reason) {
      toast.error((reason as Error).message || t('plans.createFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 py-4 sm:py-8">
      <div><Button asChild size="sm" variant="neutral"><Link to="/plans">{t('common.back')}</Link></Button><h1 className="mt-4 text-3xl font-black">{t('plans.createTitle')}</h1><p className="mt-1 text-sm text-muted-foreground">{t('plans.createSubtitle')}</p></div>
      {(loadError || selectionError || validationError) && <Alert variant={loadError ? 'destructive' : 'default'}><CircleAlert /><AlertTitle>{loadError ? t('plans.optionsLoadFailed') : t('plans.checkInput')}</AlertTitle><AlertDescription>{loadError || selectionError || validationError}</AlertDescription></Alert>}
      <Card><CardHeader><CardTitle>{t('plans.createTitle')}</CardTitle></CardHeader><CardContent><form className="space-y-5" onSubmit={submit}>
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="space-y-2"><Label>{t('plans.selectJD')}</Label><Select value={jdId} onValueChange={setJDId} disabled={loading}><SelectTrigger><SelectValue placeholder={loading ? t('common.loading') : t('plans.selectJD')} /></SelectTrigger><SelectContent>{jds.map((jd) => <SelectItem key={jd.id} value={jd.id}>{[jd.title || t('jd.untitled'), jd.company].filter(Boolean).join(' · ')}</SelectItem>)}</SelectContent></Select></div>
          <div className="space-y-2"><Label>{t('plans.selectResume')}</Label><Select value={resumeId} onValueChange={setResumeId} disabled={loading}><SelectTrigger><SelectValue placeholder={loading ? t('common.loading') : t('plans.selectResume')} /></SelectTrigger><SelectContent>{resumes.map((resume) => <SelectItem key={resume.id} value={resume.id}>{resume.display_name}</SelectItem>)}</SelectContent></Select></div>
        </div>
        <div className="space-y-2"><Label htmlFor="plan-title">{t('plans.planTitleOptional')}</Label><Input id="plan-title" maxLength={200} value={title} onChange={(event) => setTitle(event.target.value)} /></div>
        <div className="grid gap-5 sm:grid-cols-2"><div className="space-y-2"><Label htmlFor="plan-target-date">{t('plans.targetDate')}</Label><Input id="plan-target-date" type="date" min={localDate()} max={maxDate()} value={targetDate} onChange={(event) => setTargetDate(event.target.value)} /></div><div className="space-y-2"><Label htmlFor="plan-hours">{t('plans.weeklyHours')}</Label><Input id="plan-hours" type="number" min="1" max="80" step="1" value={weeklyHours} onChange={(event) => setWeeklyHours(event.target.value)} /></div></div>
        <div className="space-y-2"><Label htmlFor="plan-background">{t('plans.background')}</Label><textarea id="plan-background" className="min-h-28 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" maxLength={10_000} value={background} onChange={(event) => setBackground(event.target.value)} /><p className="text-xs text-muted-foreground">{background.length.toLocaleString()} / 10,000</p></div>
        <div className="flex justify-end"><Button type="submit" disabled={!valid || submitting}>{submitting && <Loader2 className="size-4 animate-spin" />}{submitting ? t('plans.generating') : t('plans.generate')}</Button></div>
      </form></CardContent></Card>
      <LLMGateDialog open={llmGateOpen} onOpenChange={setLlmGateOpen} description={t('plans.llmGateDescription')} successMessage={t('plans.llmReady')} />
    </div>
  )
}
