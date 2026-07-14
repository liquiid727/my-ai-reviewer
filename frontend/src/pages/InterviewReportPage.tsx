import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router'
import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts'
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Loader2,
  RefreshCw,
} from 'lucide-react'

import { getInterviewReport } from '@/api/interview'
import type { InterviewReportData } from '@/types/interview'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

const RECOMMENDATION_LABELS: Record<string, { label: string; color: string }> = {
  strong_yes: { label: '强烈推荐录用', color: 'bg-green-400 text-green-900 border-green-700' },
  yes: { label: '推荐录用', color: 'bg-green-300 text-green-900 border-green-600' },
  maybe: { label: '待定', color: 'bg-yellow-300 text-yellow-900 border-yellow-600' },
  no: { label: '不推荐', color: 'bg-red-300 text-red-900 border-red-600' },
  strong_no: { label: '强烈不推荐', color: 'bg-red-400 text-red-900 border-red-700' },
}

export function InterviewReportPage() {
  const { id } = useParams()
  const [report, setReport] = useState<InterviewReportData | null>(null)
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchReport = () => {
    if (!id) return
    setLoading(true)
    setError(null)
    getInterviewReport(id)
      .then((res) => {
        if (res.code === 2001) {
          setGenerating(true)
          return
        }
        if (res.code !== 0) {
          setError(res.message || '获取报告失败')
          return
        }
        setGenerating(false)
        setReport(res.data)
      })
      .catch((err: Error) => {
        setError(err.message || '获取报告失败')
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    fetchReport()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  useEffect(() => {
    if (!generating) return
    const timer = setInterval(() => {
      fetchReport()
    }, 3000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [generating])

  if (loading && !generating) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-48 w-full" />
        <Skeleton className="h-64 w-full" />
      </div>
    )
  }

  if (generating) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-16">
            <Loader2 className="size-12 animate-spin text-main" />
            <p className="text-xl font-heading">面试报告生成中...</p>
            <p className="text-sm text-muted-foreground">AI 正在综合分析所有回答，请稍候</p>
            <Button variant="neutral" size="sm" onClick={fetchReport}>
              <RefreshCw className="size-4 mr-1" />
              刷新状态
            </Button>
          </CardContent>
        </Card>
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

  if (!report) return null

  const rec = RECOMMENDATION_LABELS[report.recommendation] || {
    label: report.recommendation,
    color: 'bg-gray-300',
  }

  const radarData = report.dimension_scores.map((d) => ({
    dimension: d.name,
    score: d.score,
    fullMark: 100,
  }))

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Button asChild variant="neutral" size="icon">
          <Link to={`/interview/${id}`}>
            <ArrowLeft className="size-4" />
          </Link>
        </Button>
        <h1 className="text-3xl font-black">面试报告</h1>
      </div>

      {/* Score + Recommendation */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardContent className="flex flex-col items-center gap-4 pt-6">
            <ScoreGauge score={report.overall_score / 10} size={200} />
            <div className="text-center">
              <p className="text-sm text-muted-foreground">综合评分</p>
              <p className="text-2xl font-black">{report.overall_score.toFixed(1)} / 100</p>
            </div>
            <Badge className={`text-base py-1 px-4 ${rec.color}`}>{rec.label}</Badge>
          </CardContent>
        </Card>

        {/* Radar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>维度评分</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={280}>
              <RadarChart data={radarData} cx="50%" cy="50%" outerRadius="75%">
                <PolarGrid stroke="#000" strokeWidth={1} />
                <PolarAngleAxis
                  dataKey="dimension"
                  tick={{ fontSize: 12, fontWeight: 700, fill: '#000' }}
                />
                <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fontSize: 10 }} />
                <Radar
                  dataKey="score"
                  stroke="#88aaee"
                  fill="#88aaee"
                  fillOpacity={0.4}
                  strokeWidth={2}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: '5px',
                    border: '2px solid #000',
                    boxShadow: '4px 4px 0px 0px #000',
                    background: '#fff',
                  }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Dimension Details */}
      <Card>
        <CardHeader>
          <CardTitle>维度详情</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {report.dimension_scores.map((d, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-base border-2 border-border">
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-heading">{d.name}</span>
                    <Badge className={d.score >= 70 ? 'bg-green-400 border-green-700' : d.score >= 50 ? 'bg-yellow-300 border-yellow-600' : 'bg-red-400 border-red-700'}>
                      {d.score}分
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{d.reason}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Strengths & Weaknesses */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-green-700">
              <CheckCircle className="size-5" />
              优势
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {report.strengths.map((s, i) => (
                <div
                  key={i}
                  className="p-3 rounded-base border-2 border-border bg-green-50 shadow-[2px_2px_0px_0px_#000]"
                >
                  <p className="font-heading text-sm">{s.point}</p>
                  <p className="text-xs text-muted-foreground mt-1">{s.evidence}</p>
                </div>
              ))}
              {report.strengths.length === 0 && (
                <p className="text-sm text-muted-foreground">暂无</p>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-700">
              <XCircle className="size-5" />
              不足
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {report.weaknesses.map((w, i) => (
                <div
                  key={i}
                  className="p-3 rounded-base border-2 border-border bg-red-50 shadow-[2px_2px_0px_0px_#000]"
                >
                  <p className="font-heading text-sm">{w.point}</p>
                  <p className="text-xs text-muted-foreground mt-1">{w.evidence}</p>
                </div>
              ))}
              {report.weaknesses.length === 0 && (
                <p className="text-sm text-muted-foreground">暂无</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Per-Question Summary */}
      <Card>
        <CardHeader>
          <CardTitle>逐题回顾</CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="space-y-2">
            {report.per_question_summary.map((q, i) => (
              <AccordionItem key={i} value={`q-${i}`}>
                <AccordionTrigger>
                  <div className="flex items-center gap-2 text-left">
                    <Badge variant="neutral">第{q.question_num}题</Badge>
                    <span className="text-sm font-heading truncate max-w-[400px]">
                      {q.question_text}
                    </span>
                    <Badge className={q.final_score >= 70 ? 'bg-green-400 border-green-700' : q.final_score >= 50 ? 'bg-yellow-300 border-yellow-600' : 'bg-red-400 border-red-700'}>
                      {q.final_score.toFixed(0)}分
                    </Badge>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  <p className="text-sm">{q.summary}</p>
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </CardContent>
      </Card>

      {/* AI Summary */}
      {report.summary && (
        <Alert>
          <AlertTitle className="font-heading">AI 综合评价</AlertTitle>
          <AlertDescription className="mt-2 whitespace-pre-wrap">
            {report.summary}
          </AlertDescription>
        </Alert>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground pt-4">
        {report.llm_model && <span>模型：{report.llm_model}</span>}
        {report.created_at && (
          <span>生成时间：{new Date(report.created_at).toLocaleString('zh-CN')}</span>
        )}
      </div>
    </div>
  )
}
