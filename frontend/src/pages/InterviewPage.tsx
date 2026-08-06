import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router'
import { useTranslation } from 'react-i18next'
import { toast } from 'sonner'
import { startInterview, submitAnswer } from '@/api/interview'
import { useInterviewStore } from '@/stores/interviewStore'
import type { ChatMessage, QuestionPresentData } from '@/types/interview'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Loader2,
  Send,
  CheckCircle,
  XCircle,
  MessageSquare,
  ArrowRight,
  Timer,
} from 'lucide-react'

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-400 text-green-900 border-green-700',
  medium: 'bg-yellow-300 text-yellow-900 border-yellow-700',
  hard: 'bg-red-400 text-red-900 border-red-700',
}

// 计时器显示格式：mm:ss
function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function ScoreBadge({ score }: { score: number }) {
  const { t } = useTranslation()
  const color =
    score >= 70
      ? 'bg-green-400 text-green-900 border-green-700'
      : score >= 50
        ? 'bg-yellow-300 text-yellow-900 border-yellow-700'
        : 'bg-red-400 text-red-900 border-red-700'
  return <Badge className={color}>{score}{t('interview.points')}</Badge>
}

export function InterviewPage() {
  const { id } = useParams()
  const { t } = useTranslation()
  const [loading, setLoading] = useState(true)
  const [answerText, setAnswerText] = useState('')
  // 面试房间计时：总时长 + 当前题目用时（新题/追问时重置本题计时）
  const [totalSeconds, setTotalSeconds] = useState(0)
  const [questionSeconds, setQuestionSeconds] = useState(0)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const startRequestRef = useRef<{
    id: string
    promise: ReturnType<typeof startInterview>
  } | null>(null)

  const {
    currentQuestion,
    messages,
    isSubmitting,
    isFinished,
    setCurrentQuestion,
    addMessage,
    setSubmitting,
    setFinished,
    reset,
  } = useInterviewStore()

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  useEffect(() => {
    if (!id) return
    reset()
    setLoading(true)
    setTotalSeconds(0)
    setQuestionSeconds(0)

    const existingRequest = startRequestRef.current?.id === id ? startRequestRef.current.promise : null
    const request = existingRequest ?? startInterview(id)
    if (!existingRequest) {
      startRequestRef.current = { id, promise: request }
    }

    let active = true
    request
      .then((res) => {
        if (!active) return
        if (res.code !== 0) {
          toast.error(res.message || t('interview.startFailed'))
          return
        }
        const q = res.data
        setCurrentQuestion(q)
        addMessage({
          id: `q-${q.question_id}-0`,
          type: 'question',
          content: q.question_text,
          data: q,
          timestamp: Date.now(),
        })
      })
      .catch((err: Error) => {
        if (!active) return
        toast.error(err.message || t('interview.startFailed'))
      })
      .finally(() => {
        if (active) setLoading(false)
        if (startRequestRef.current?.promise === request) {
          startRequestRef.current = null
        }
      })

    return () => {
      active = false
      reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const currentQuestionId = currentQuestion?.question_id ?? null

  // 总计时：从首题展示开始，面试结束后停止
  useEffect(() => {
    if (!currentQuestionId || isFinished) return
    const timer = window.setInterval(() => setTotalSeconds((s) => s + 1), 1000)
    return () => window.clearInterval(timer)
  }, [currentQuestionId, isFinished])

  // 本题计时：切换到新题/追问时归零
  useEffect(() => {
    setQuestionSeconds(0)
    if (!currentQuestionId || isFinished) return
    const timer = window.setInterval(() => setQuestionSeconds((s) => s + 1), 1000)
    return () => window.clearInterval(timer)
  }, [currentQuestionId, isFinished])

  const handleSubmit = async () => {
    if (!id || !currentQuestion || !answerText.trim() || isSubmitting) return

    if (answerText.trim().length < 10) {
      toast.error(t('interview.answerTooShort'))
      return
    }

    const answer = answerText.trim()
    setAnswerText('')
    setSubmitting(true)

    addMessage({
      id: `a-${currentQuestion.question_id}-${Date.now()}`,
      type: 'answer',
      content: answer,
      timestamp: Date.now(),
    })

    try {
      const res = await submitAnswer(id, currentQuestion.question_id, answer)
      if (res.code !== 0) {
        toast.error(res.message || t('interview.submitFailed'))
        setSubmitting(false)
        return
      }

      const result = res.data
      addMessage({
        id: `e-${currentQuestion.question_id}-${Date.now()}`,
        type: 'evaluation',
        content: result.feedback,
        data: result,
        timestamp: Date.now(),
      })

      if (result.is_finished) {
        setFinished(true)
        setCurrentQuestion(null)
        addMessage({
          id: `sys-finished-${Date.now()}`,
          type: 'system',
          content: t('interview.completed'),
          timestamp: Date.now(),
        })
      } else if (result.next) {
        setCurrentQuestion(result.next)
        const nextQ = result.next
        addMessage({
          id: `q-${nextQ.question_id}-${nextQ.followup_round}`,
          type: nextQ.is_followup ? 'followup' : 'question',
          content: nextQ.question_text,
          data: nextQ,
          timestamp: Date.now(),
        })
      }
    } catch (err) {
      toast.error((err as Error).message || t('interview.submitError'))
    } finally {
      setSubmitting(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  if (loading) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  const progress = currentQuestion
    ? ((currentQuestion.current_num - 1) / currentQuestion.total_count) * 100
    : 100

  return (
    <div className="max-w-3xl mx-auto py-6 px-4 flex flex-col" style={{ height: 'calc(100vh - 80px)' }}>
      {/* Header */}
      <div className="mb-4 space-y-2">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-black">{t('interview.title')}</h1>
          {currentQuestion && (
            <span className="text-sm font-heading">
              {t('interview.questionXofY', {
                current: currentQuestion.current_num,
                total: currentQuestion.total_count,
              })}
            </span>
          )}
        </div>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span className="inline-flex items-center gap-1 font-heading">
              <Timer className="size-3.5" />
              {t('interview.timerTotal')} {formatElapsed(totalSeconds)}
            </span>
            {currentQuestion && !isFinished && (
              <span className="font-heading">
                {t('interview.timerQuestion')} {formatElapsed(questionSeconds)}
              </span>
            )}
          </div>
        </div>
        <Progress value={progress} className="h-3" />
        <p className="text-xs text-muted-foreground">{t('interview.roomHint')}</p>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      {!isFinished ? (
        <div className="border-t-2 border-border pt-4">
          <div className="flex gap-2">
            <textarea
              ref={textareaRef}
              value={answerText}
              onChange={(e) => setAnswerText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('interview.placeholder')}
              disabled={isSubmitting || !currentQuestion}
              rows={3}
              className="flex-1 rounded-base border-2 border-border bg-secondary-background px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-black focus:ring-offset-2 resize-none disabled:opacity-50"
            />
            <Button
              onClick={handleSubmit}
              disabled={isSubmitting || !answerText.trim() || !currentQuestion}
              className="self-end"
            >
              {isSubmitting ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <Send className="size-4" />
              )}
            </Button>
          </div>
        </div>
      ) : (
        <div className="border-t-2 border-border pt-4 flex justify-center">
          <Button asChild size="lg">
            <Link to={`/interview/${id}/report`}>
              {t('interview.viewReport')}
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
  const { t } = useTranslation()
  if (message.type === 'question' || message.type === 'followup') {
    const q = message.data as QuestionPresentData | undefined
    return (
      <div className="flex justify-start">
        <Card className="max-w-[85%]">
          <CardContent className="pt-4 space-y-2">
            <div className="flex items-center gap-2 flex-wrap">
              <MessageSquare className="size-4" />
              {q && (
                <>
                  <Badge>{t(`interview.stage.${q.stage}`) || q.stage}</Badge>
                  <Badge className={DIFFICULTY_COLORS[q.difficulty] || ''}>
                    {t(`interview.difficulty.${q.difficulty}`)}
                  </Badge>
                </>
              )}
              {message.type === 'followup' && (
                <Badge className="bg-purple-400 text-purple-900 border-purple-700">
                  {t('interview.followup')}
                </Badge>
              )}
            </div>
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (message.type === 'answer') {
    return (
      <div className="flex justify-end">
        <Card className="max-w-[85%] bg-main">
          <CardContent className="pt-4">
            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  if (message.type === 'evaluation') {
    const result = message.data as {
      score: number
      feedback: string
      key_points_hit: string[]
      key_points_missed: string[]
    } | undefined
    return (
      <div className="flex justify-start">
        <Card className="max-w-[85%] bg-secondary-background">
          <CardContent className="pt-4 space-y-3">
            {result && (
              <>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-heading">{t('interview.score')}</span>
                  <ScoreBadge score={result.score} />
                </div>
                <p className="text-sm">{result.feedback}</p>
                {result.key_points_hit.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs font-heading text-green-700">{t('interview.hitPoints')}</span>
                    <div className="flex flex-wrap gap-1">
                      {result.key_points_hit.map((p, i) => (
                        <span key={i} className="inline-flex items-center gap-1 text-xs bg-green-100 border border-green-300 rounded-base px-2 py-0.5">
                          <CheckCircle className="size-3 text-green-600" />
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {result.key_points_missed.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs font-heading text-red-700">{t('interview.missedPoints')}</span>
                    <div className="flex flex-wrap gap-1">
                      {result.key_points_missed.map((p, i) => (
                        <span key={i} className="inline-flex items-center gap-1 text-xs bg-red-100 border border-red-300 rounded-base px-2 py-0.5">
                          <XCircle className="size-3 text-red-600" />
                          {p}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </CardContent>
        </Card>
      </div>
    )
  }

  if (message.type === 'system') {
    return (
      <div className="flex justify-center">
        <Badge variant="neutral" className="text-sm py-1 px-3">
          {message.content}
        </Badge>
      </div>
    )
  }

  return null
}
