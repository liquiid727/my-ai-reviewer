import { useEffect, useRef, useState, useCallback } from 'react'
import { useParams, Link } from 'react-router'
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
} from 'lucide-react'

const STAGE_LABELS: Record<string, string> = {
  basic: '基础知识',
  project: '项目经验',
  architecture: '系统设计',
  behavior: '行为面试',
}

const DIFFICULTY_COLORS: Record<string, string> = {
  easy: 'bg-green-400 text-green-900 border-green-700',
  medium: 'bg-yellow-300 text-yellow-900 border-yellow-700',
  hard: 'bg-red-400 text-red-900 border-red-700',
}

function ScoreBadge({ score }: { score: number }) {
  const color =
    score >= 70
      ? 'bg-green-400 text-green-900 border-green-700'
      : score >= 50
        ? 'bg-yellow-300 text-yellow-900 border-yellow-700'
        : 'bg-red-400 text-red-900 border-red-700'
  return <Badge className={color}>{score}分</Badge>
}

export function InterviewPage() {
  const { id } = useParams()
  const [loading, setLoading] = useState(true)
  const [answerText, setAnswerText] = useState('')
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

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

    startInterview(id)
      .then((res) => {
        if (res.code !== 0) {
          toast.error(res.message || '开始面试失败')
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
        toast.error(err.message || '面试启动失败')
      })
      .finally(() => {
        setLoading(false)
      })

    return () => {
      reset()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const handleSubmit = async () => {
    if (!id || !currentQuestion || !answerText.trim() || isSubmitting) return

    if (answerText.trim().length < 10) {
      toast.error('回答至少需要 10 个字符')
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
        toast.error(res.message || '提交回答失败')
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
          content: '面试已完成！正在生成面试报告...',
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
      toast.error((err as Error).message || '提交失败')
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
          <h1 className="text-2xl font-black">AI 面试</h1>
          {currentQuestion && (
            <span className="text-sm font-heading">
              第 {currentQuestion.current_num} 题 / 共 {currentQuestion.total_count} 题
            </span>
          )}
        </div>
        <Progress value={progress} className="h-3" />
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
              placeholder="输入你的回答... (Shift+Enter 换行)"
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
              查看面试报告
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}

function MessageBubble({ message }: { message: ChatMessage }) {
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
                  <Badge>{STAGE_LABELS[q.stage] || q.stage}</Badge>
                  <Badge className={DIFFICULTY_COLORS[q.difficulty] || ''}>
                    {q.difficulty}
                  </Badge>
                </>
              )}
              {message.type === 'followup' && (
                <Badge className="bg-purple-400 text-purple-900 border-purple-700">
                  追问
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
                  <span className="text-sm font-heading">评分：</span>
                  <ScoreBadge score={result.score} />
                </div>
                <p className="text-sm">{result.feedback}</p>
                {result.key_points_hit.length > 0 && (
                  <div className="space-y-1">
                    <span className="text-xs font-heading text-green-700">命中要点：</span>
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
                    <span className="text-xs font-heading text-red-700">遗漏要点：</span>
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
