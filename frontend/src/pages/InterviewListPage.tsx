import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { formatDateTime } from '@/i18n'
import { listInterviews } from '@/api/interview'
import type { InterviewListItem } from '@/types/interview'
import { Card, CardContent, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ArrowRight,
  Calendar,
  CircleAlert,
  CircleCheck,
  Clock,
  FileText,
  Hash,
  Loader2,
  Medal,
  MessageSquare,
  Minus,
  ThumbsDown,
  ThumbsUp,
  Video,
} from 'lucide-react'

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-300 text-gray-800 border-gray-500',
  generating: 'bg-blue-300 text-blue-900 border-blue-600',
  in_progress: 'bg-yellow-300 text-yellow-900 border-yellow-600',
  report_generating: 'bg-purple-300 text-purple-900 border-purple-600',
  completed: 'bg-green-400 text-green-900 border-green-700',
  failed: 'bg-red-400 text-red-900 border-red-700',
}

/** 状态徽章图标：生成类状态使用旋转动画，终态使用语义图标 */
function InterviewStatusIcon({ status }: { status: string }) {
  if (status === 'generating' || status === 'report_generating') {
    return <Loader2 className="animate-spin" />
  }
  if (status === 'completed') return <CircleCheck />
  if (status === 'failed') return <CircleAlert />
  if (status === 'in_progress') return <MessageSquare />
  return <Clock />
}

/** 推荐结论图标：正向/负向/待定 */
function RecommendationIcon({ recommendation }: { recommendation: string }) {
  if (recommendation === 'strong_yes' || recommendation === 'yes') return <ThumbsUp />
  if (recommendation === 'no' || recommendation === 'strong_no') return <ThumbsDown />
  return <Minus />
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
      <div>
        <h1 className="text-3xl font-black">{t('interviewList.title')}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{t('interviewList.subtitle')}</p>
      </div>

      {interviews.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <Video className="size-8" />
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
            const iconBg =
              iv.status === 'completed'
                ? 'bg-success'
                : iv.status === 'failed'
                  ? 'bg-destructive'
                  : 'bg-main'

            return (
              <Card key={iv.interview_id} className="transition-all hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none">
                <CardContent className="flex flex-col gap-4 py-4 sm:flex-row sm:items-center">
                  {/* 面试图标块：底色随状态传达语义 */}
                  <div className={`flex size-12 shrink-0 items-center justify-center rounded-base border-2 border-border shadow-shadow ${iconBg}`}>
                    <Video className="size-6" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-1.5">
                    {/* 标题行：面试编号 + 草稿标记 + 状态徽章 */}
                    <div className="flex flex-wrap items-center gap-2">
                      <CardTitle className="text-base">
                        {t('interviewList.interviewId', { id: iv.interview_id.slice(0, 8) })}
                      </CardTitle>
                      {iv.is_draft_interview && (
                        <Badge variant="neutral">{t('interviewList.draftInterview')}</Badge>
                      )}
                      <Badge className={statusColor}>
                        <InterviewStatusIcon status={iv.status} />
                        {t(`interviewList.status.${iv.status}`) || iv.status}
                      </Badge>
                    </div>
                    {/* 元信息行：题目数 / 创建时间 / 推荐结论 */}
                    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Hash className="size-3.5 shrink-0" />
                        {t('interviewList.questions', { count: iv.question_count })}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Calendar className="size-3.5 shrink-0" />
                        {formatDateTime(iv.created_at)}
                      </span>
                      {iv.recommendation && (
                        <Badge variant="neutral">
                          <RecommendationIcon recommendation={iv.recommendation} />
                          {t(`interviewList.recommendation.${iv.recommendation}`) || iv.recommendation}
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex shrink-0 items-center gap-4">
                    {/* 综合评分：仅已完成且有分数时展示 */}
                    {iv.overall_score != null && (
                      <span className="flex items-center gap-1.5 text-2xl font-black">
                        <Medal className="size-5" />
                        {iv.overall_score.toFixed(0)}{t('interview.points')}
                      </span>
                    )}
                    <Button asChild size="sm" variant={iv.status === 'completed' ? 'neutral' : 'default'}>
                      <Link to={linkTo}>
                        {iv.status === 'completed' ? (
                          <>
                            <FileText className="size-4" />
                            {t('interviewList.viewReport')}
                          </>
                        ) : (
                          <>
                            {t('interviewList.continue')}
                            <ArrowRight className="size-4" />
                          </>
                        )}
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
