import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate } from 'react-router'
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
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  AlertTriangle,
  Info,
  XCircle,
  HelpCircle,
  Search,
  SkipForward,
} from 'lucide-react'

import { getEvaluation } from '@/api/evaluation'
import type { EvaluationData, DimensionScore } from '@/types/evaluation'
import { ScoreGauge } from '@/components/ScoreGauge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from '@/components/ui/accordion'

function severityColor(severity: string): string {
  switch (severity) {
    case 'high':
      return 'bg-red-500 text-white'
    case 'medium':
      return 'bg-yellow-400 text-black'
    case 'low':
      return 'bg-gray-300 text-black'
    default:
      return 'bg-gray-300 text-black'
  }
}

function severityLabel(severity: string): string {
  switch (severity) {
    case 'high':
      return '高风险'
    case 'medium':
      return '中风险'
    case 'low':
      return '低风险'
    default:
      return severity
  }
}

interface DimensionTooltipProps {
  active?: boolean
  payload?: Array<{ payload: DimensionScore }>
}

function DimensionTooltip({ active, payload }: DimensionTooltipProps) {
  if (!active || !payload?.[0]) return null
  const dim = payload[0].payload
  return (
    <div className="rounded-base border-2 border-border bg-white p-3 shadow-shadow max-w-xs">
      <p className="font-heading text-sm">
        {dim.name}: {dim.score}
      </p>
      <p className="mt-1 text-xs text-gray-700">{dim.reason}</p>
      {dim.evidence && (
        <p className="mt-1 text-xs text-gray-600 italic">
          &ldquo;{dim.evidence}&rdquo;
        </p>
      )}
    </div>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Progress />
      <div className="flex items-center gap-6">
        <Skeleton className="h-44 w-44 rounded-full" />
        <div className="flex-1 space-y-3">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-3/4" />
        </div>
      </div>
      <Skeleton className="h-72 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
      <Skeleton className="h-48" />
    </div>
  )
}

function SuggestionList({ items }: { items: string[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-gray-500">暂无内容</p>
  }
  return (
    <ul className="space-y-3">
      {items.map((item, i) => (
        <li
          key={i}
          className="rounded-base border-2 border-border bg-white p-3"
        >
          <p className="text-sm">{item}</p>
        </li>
      ))}
    </ul>
  )
}

export function EvaluationPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [data, setData] = useState<EvaluationData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!id) return
    setLoading(true)
    setError(null)
    getEvaluation(id)
      .then((res) => {
        if (res.code !== 0) {
          setError(res.message || '获取评估报告失败')
        } else {
          setData(res.data)
        }
      })
      .catch((err: unknown) => {
        const message =
          err instanceof Error ? err.message : '网络错误，请稍后重试'
        setError(message)
      })
      .finally(() => setLoading(false))
  }, [id])

  const radarData = useMemo(() => {
    if (!data) return []
    return data.dimension_scores.map((d) => ({
      ...d,
      fullMark: 100,
    }))
  }, [data])

  if (loading) {
    return (
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-3xl font-black">评估报告</h1>
        <LoadingSkeleton />
      </div>
    )
  }

  if (error || !data) {
    return (
      <div className="mx-auto max-w-4xl">
        <h1 className="mb-6 text-3xl font-black">评估报告</h1>
        <Alert variant="destructive">
          <XCircle className="h-4 w-4" />
          <AlertTitle>加载失败</AlertTitle>
          <AlertDescription>{error ?? '未找到评估数据'}</AlertDescription>
        </Alert>
        <Button
          className="mt-4"
          variant="neutral"
          onClick={() => navigate(-1)}
        >
          <ArrowLeft className="h-4 w-4" />
          返回
        </Button>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-4xl space-y-8">
      {/* Header with back button */}
      <div className="flex items-center gap-4">
        <Button variant="neutral" size="icon" onClick={() => navigate(-1)}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <h1 className="text-3xl font-black">评估报告</h1>
      </div>

      {/* Overall Score Section */}
      <Card>
        <CardContent className="flex flex-col items-center gap-6 py-6 sm:flex-row sm:items-start">
          <ScoreGauge score={data.overall_score} />
          <div className="flex-1 text-center sm:text-left">
            <h2 className="text-2xl font-black">综合评分</h2>
            <p className="mt-2 text-gray-600">
              基于 {data.dimension_scores.length} 个维度的综合评估
            </p>
            <div className="mt-4 flex flex-wrap gap-2">
              {data.dimension_scores.map((d) => (
                <Badge
                  key={d.name}
                  variant="neutral"
                  className="text-xs"
                >
                  {d.name}: {d.score}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Radar Chart */}
      <Card>
        <CardHeader>
          <CardTitle>维度评分雷达图</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-80 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart
                data={radarData}
                cx="50%"
                cy="50%"
                outerRadius="75%"
              >
                <PolarGrid stroke="#000" strokeWidth={1} />
                <PolarAngleAxis
                  dataKey="name"
                  tick={{ fontSize: 12, fontWeight: 700, fill: '#000' }}
                />
                <PolarRadiusAxis
                  angle={90}
                  domain={[0, 100]}
                  tick={{ fontSize: 10, fill: '#666' }}
                />
                <Radar
                  name="评分"
                  dataKey="score"
                  stroke="#88aaee"
                  fill="#88aaee"
                  fillOpacity={0.4}
                  strokeWidth={2}
                />
                <Tooltip content={<DimensionTooltip />} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>

      {/* Strengths & Risks Side by Side */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Strengths */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-green-600" />
              优势亮点
              <Badge className="ml-auto bg-green-500 text-white">
                {data.strengths.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.strengths.map((s, i) => (
              <div
                key={i}
                className="rounded-base border-2 border-border bg-green-50 p-3 shadow-[2px_2px_0px_0px_#000]"
              >
                <p className="font-heading text-sm">{s.point}</p>
                <p className="mt-1 text-xs text-gray-600">{s.evidence}</p>
              </div>
            ))}
            {data.strengths.length === 0 && (
              <p className="text-sm text-gray-500">暂无优势亮点</p>
            )}
          </CardContent>
        </Card>

        {/* Risks */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              风险提示
              <Badge className="ml-auto bg-red-500 text-white">
                {data.risks.length}
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {data.risks.map((r, i) => (
              <div
                key={i}
                className="rounded-base border-2 border-border bg-white p-3 shadow-[2px_2px_0px_0px_#000]"
              >
                <div className="flex items-center gap-2">
                  <Badge className={severityColor(r.severity)}>
                    {severityLabel(r.severity)}
                  </Badge>
                  <p className="font-heading text-sm">{r.point}</p>
                </div>
                <p className="mt-1 text-xs text-gray-600">{r.evidence}</p>
              </div>
            ))}
            {data.risks.length === 0 && (
              <p className="text-sm text-gray-500">暂无风险提示</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Interview Suggestions */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Info className="h-5 w-5" />
            面试建议
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Accordion type="multiple" className="space-y-3">
            <AccordionItem value="worth_asking">
              <AccordionTrigger>
                <span className="flex items-center gap-2">
                  <HelpCircle className="h-4 w-4" />
                  值得追问
                  <Badge variant="neutral">
                    {data.interview_suggestions.worth_asking.length}
                  </Badge>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <SuggestionList
                  items={data.interview_suggestions.worth_asking}
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="suspicious">
              <AccordionTrigger>
                <span className="flex items-center gap-2">
                  <AlertCircle className="h-4 w-4" />
                  疑似夸大
                  <Badge variant="neutral">
                    {data.interview_suggestions.suspicious.length}
                  </Badge>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <SuggestionList
                  items={data.interview_suggestions.suspicious}
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="verify_direction">
              <AccordionTrigger>
                <span className="flex items-center gap-2">
                  <Search className="h-4 w-4" />
                  验证方向
                  <Badge variant="neutral">
                    {data.interview_suggestions.verify_direction.length}
                  </Badge>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <SuggestionList
                  items={data.interview_suggestions.verify_direction}
                />
              </AccordionContent>
            </AccordionItem>

            <AccordionItem value="skip">
              <AccordionTrigger>
                <span className="flex items-center gap-2">
                  <SkipForward className="h-4 w-4" />
                  建议跳过
                  <Badge variant="neutral">
                    {data.interview_suggestions.skip.length}
                  </Badge>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <SuggestionList
                  items={data.interview_suggestions.skip}
                />
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </CardContent>
      </Card>

      {/* Summary */}
      {data.summary && (
        <Alert>
          <Info className="h-4 w-4" />
          <AlertTitle>AI 综合评价</AlertTitle>
          <AlertDescription className="whitespace-pre-wrap">
            {data.summary}
          </AlertDescription>
        </Alert>
      )}

      {/* Footer */}
      <div className="flex flex-wrap items-center justify-between gap-2 border-t-2 border-border pt-4 text-sm text-gray-500">
        <span>
          模型:{' '}
          <span className="font-heading">{data.llm_model ?? '未知'}</span>
        </span>
        <span>
          评估时间:{' '}
          <span className="font-heading">
            {new Date(data.created_at).toLocaleString('zh-CN')}
          </span>
        </span>
      </div>
    </div>
  )
}
