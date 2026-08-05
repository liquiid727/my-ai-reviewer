import { useEffect, useState } from 'react'
import { useParams } from 'react-router'
import { useTranslation } from 'react-i18next'
import { Archive, Loader2, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import {
  archiveJobTarget,
  getJobTarget,
  listJdVersions,
  listResumeVersions,
  updateJobTargetDefaults,
} from '@/api/job-targets'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import type { JobTargetDetail, JdVersionSummary, ResumeVersionSummary } from '@/types/job-targets'

function readableDate(value: string | null) {
  return value ? new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) : '—'
}

export default function JobTargetPage() {
  const { id } = useParams<{ id: string }>()
  const { t } = useTranslation()

  const [target, setTarget] = useState<JobTargetDetail | null>(null)
  const [jdVersions, setJdVersions] = useState<JdVersionSummary[]>([])
  const [resumeVersions, setResumeVersions] = useState<ResumeVersionSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [conflict, setConflict] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    getJobTarget(id)
      .then((resp) => {
        const data = resp.data
        setTarget(data)
        setConflict(null)
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

  async function changeDefaultResume(versionId: string) {
    if (!target) return
    setSaving(true)
    setConflict(null)
    try {
      const resp = await updateJobTargetDefaults(target.id, {
        expected_revision: target.revision,
        default_resume_version_id: versionId,
      })
      setTarget(resp.data)
      toast.success(t('jobTargets.defaultUpdated'))
    } catch (e: unknown) {
      const err = e as { code?: number; message?: string }
      if (err.code === 409) {
        setConflict(t('jobTargets.revisionConflict'))
        // Reload to reconcile.
        const fresh = await getJobTarget(target.id)
        setTarget(fresh.data)
      } else {
        toast.error(err.message || t('common.retry'))
      }
    } finally {
      setSaving(false)
    }
  }

  async function doArchive() {
    if (!target) return
    setSaving(true)
    try {
      const resp = await archiveJobTarget(target.id, target.revision)
      setTarget(resp.data)
      toast.success(t('jobTargets.archived'))
    } catch {
      toast.error(t('common.retry'))
    } finally {
      setSaving(false)
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

  if (error || !target) {
    return (
      <div className="mx-auto max-w-3xl p-6">
        <p className="text-muted-foreground">{error || t('jobTargets.notFound')}</p>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">
            {target.job?.title || t('jobTargets.untitled')}
          </h1>
          <p className="text-sm text-muted-foreground">
            {target.job?.company || '—'} · {t('jobTargets.revision')} {target.revision}
          </p>
        </div>
        {target.archived_at ? (
          <span className="text-sm text-muted-foreground">{t('jobTargets.archived')}</span>
        ) : (
          <Button variant="neutral" size="sm" onClick={doArchive} disabled={saving}>
            <Archive className="mr-1 h-4 w-4" />
            {t('jobTargets.archive')}
          </Button>
        )}
      </div>

      {conflict && (
        <Card className="border-destructive">
          <CardContent className="flex items-center gap-3 pt-4">
            <RefreshCw className="h-4 w-4 text-destructive" />
            <span className="text-sm">{conflict}</span>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t('jobTargets.currentVersion')}</CardTitle>
          <CardDescription>
            {target.current_jd_version
              ? `v${target.current_jd_version.version_no} · ${readableDate(target.current_jd_version.published_at)}`
              : t('jobTargets.noVersion')}
          </CardDescription>
        </CardHeader>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('jobTargets.defaultResume')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Select
            value={target.default_resume_version_id ?? undefined}
            onValueChange={changeDefaultResume}
            disabled={saving || !!target.archived_at}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder={t('jobTargets.selectResume')} />
            </SelectTrigger>
            <SelectContent>
              {resumeVersions.map((v) => (
                <SelectItem key={v.id} value={v.id}>
                  {v.source_type} · {readableDate(v.published_at)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {saving && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{t('jobTargets.jdHistory')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {jdVersions.length === 0 && (
            <p className="text-sm text-muted-foreground">{t('jobTargets.noVersions')}</p>
          )}
          {jdVersions.map((v) => (
            <div key={v.id} className="flex items-center justify-between text-sm">
              <span>v{v.version_no}</span>
              <span className="text-muted-foreground">{readableDate(v.published_at)}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
