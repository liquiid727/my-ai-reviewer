import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { listInterviews } from '@/api/interview'
import type { InterviewListItem } from '@/types/interview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ArrowRight, Calendar, Hash } from 'lucide-react'

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  pending: { label: '待开始', color: 'bg-gray-300 text-gray-800 border-gray-500' },
  generating: { label: '生成题目中', color: 'bg-blue-300 text-blue-900 border-blue-600' },
  in_progress: { label: '进行中', color: 'bg-yellow-300 text-yellow-900 border-yellow-600' },
  report_generating: { label: '报告生成中', color: 'bg-purple-300 text-purple-900 border-purple-600' },
  completed: { label: '已完成', color: 'bg-green-400 text-green-900 border-green-700' },
  failed: { label: '失败', color: 'bg-red-400 text-red-900 border-red-700' },
}

const RECOMMENDATION_LABELS: Record<string, string> = {
  strong_yes: '强烈推荐',
  yes: '推荐',
  maybe: '待定',
  no: '不推荐',
  strong_no: '强烈不推荐',
}

export function InterviewListPage() {
  const [interviews, setInterviews] = useState<InterviewListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setLoading(true)
    listInterviews()
      .then((res) => {
        if (res.code !== 0) {
          setError(res.message || '获取面试列表失败')
          return
        }
        setInterviews(res.data || [])
      })
      .catch((err: Error) => {
        setError(err.message || '获取面试列表失败')
      })
      .finally(() => {
        setLoading(false)
      })
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
        <Card>
          <CardContent className="pt-6">
            <p className="text-red-600 font-bold">错误：{error}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-3xl font-black">面试列表</h1>

      {interviews.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12">
            <p className="text-lg text-muted-foreground">暂无面试记录</p>
            <Button asChild>
              <Link to="/upload">上传简历开始面试</Link>
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {interviews.map((iv) => {
            const statusCfg = STATUS_CONFIG[iv.status] || {
              label: iv.status,
              color: 'bg-gray-300',
            }
            const linkTo =
              iv.status === 'completed'
                ? `/interview/${iv.interview_id}/report`
                : `/interview/${iv.interview_id}`

            return (
              <Card key={iv.interview_id} className="hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none transition-all">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      面试 #{iv.interview_id.slice(0, 8)}
                      <Badge className={statusCfg.color}>{statusCfg.label}</Badge>
                    </CardTitle>
                    {iv.overall_score != null && (
                      <span className="text-2xl font-black">
                        {iv.overall_score.toFixed(0)}分
                      </span>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1">
                        <Hash className="size-3" />
                        {iv.question_count} 题
                      </span>
                      <span className="flex items-center gap-1">
                        <Calendar className="size-3" />
                        {new Date(iv.created_at).toLocaleString('zh-CN')}
                      </span>
                      {iv.recommendation && (
                        <Badge variant="neutral">
                          {RECOMMENDATION_LABELS[iv.recommendation] || iv.recommendation}
                        </Badge>
                      )}
                    </div>
                    <Button asChild size="sm">
                      <Link to={linkTo}>
                        {iv.status === 'completed' ? '查看报告' : '继续面试'}
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
