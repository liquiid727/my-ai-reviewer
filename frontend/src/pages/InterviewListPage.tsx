import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { formatDateTime } from '@/i18n'
import { listInterviews } from '@/api/interview'
import type { InterviewListItem } from '@/types/interview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowRight, Calendar, Hash, CircleAlert } from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-300 text-gray-800 border-gray-500',
  generating: 'bg-blue-300 text-blue-900 border-blue-600',
  in_progress: 'bg-yellow-300 text-yellow-900 border-yellow-600',
  report_generating: 'bg-purple-300 text-purple-900 border-purple-600',
  completed: 'bg-green-400 text-green-900 border-green-700',
  failed: 'bg-red-400 text-red-900 border-red-700',
}

export function InterviewListPage() {
  const { t } = useTranslation()
  const [interviews, setInterviews] = useState<InterviewListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    listInterviews()
      .then((res) => {
        if (res.code !== 0) {
          setError(res.message || t('interviewList.loadFailed'))
          return
        }
        setInterviews(res.data || [])
      })
      .catch((err: Error) => {
        setError(err.message || t('interviewList.loadFailed'))
      })
      .finally(() => {
        setLoading(false)
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4 space-y-4">
        <Skeleton className="h-10 w-48" />
        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Alert variant="destructive">
          <CircleAlert />
          <AlertDescription>
            {t('interviewList.error', { msg: error })}
          </AlertDescription>
        </Alert>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-3xl font-black">{t('interviewList.title')}</h1>

      {interviews.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <p className="text-lg text-muted-foreground">{t('interviewList.noRecords')}</p>
            <Button asChild>
              <Link to="/upload">{t('interviewList.uploadToStart')}</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {interviews.map((iv) => {
            const statusColor = STATUS_COLORS[iv.status] || 'bg-gray-300'
            const linkTo =
              iv.status === 'completed'
                ? `/interview/${iv.interview_id}/report`
                : `/interview/${iv.interview_id}`

            return (
              <Card key={iv.interview_id} className="hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      {t('interviewList.interviewId', { id: iv.interview_id.slice(0, 8) })}
                      <Badge className={statusColor}>{t(`interviewList.status.${iv.status}`) || iv.status}</Badge>
                    </CardTitle>
                    {iv.overall_score != null && (
                      <span className="text-2xl font-black">
                        {iv.overall_score.toFixed(0)}{t('interview.points')}
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Hash className="size-3" />
                        {t('interviewList.questions', { count: iv.question_count })}
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3" />
                        {formatDateTime(iv.created_at)}
                      </span>
                      {iv.recommendation && (
                        <Badge variant="neutral">
                          {t(`interviewList.recommendation.${iv.recommendation}`) || iv.recommendation}
                        </Badge>
                      )}
                    </div>
                    <Button asChild size="sm">
                      <Link to={linkTo}>
                        {iv.status === 'completed' ? t('interviewList.viewReport') : t('interviewList.continue')}
                        <ArrowRight className="size-4" />
                      </Link>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
