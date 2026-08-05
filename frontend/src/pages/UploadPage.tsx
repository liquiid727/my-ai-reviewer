import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { ArrowRight, Loader2, TriangleAlert } from 'lucide-react'
import { FileUploader } from '@/components/FileUploader'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { UploadWorkflowPanel } from '@/components/upload/UploadWorkflowPanel'
import { Progress } from '@/components/ui/progress'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { useResumeStore } from '@/stores/resumeStore'
import { useResumeHistoryStore } from '@/stores/resumeHistoryStore'
import { useSettingsStore } from '@/stores/settingsStore'
import {
  addPrivacyMasks,
  approvePrivacy,
  getPrivacyReview,
  uploadResume,
  getResumeStatus,
  retryResume,
} from '@/api/resume'
import {
  RESUME_POLL_FAST_MS,
  RESUME_POLL_MAX_MS,
  RESUME_POLL_SLOW_AFTER_MS,
  RESUME_POLL_SLOW_MS,
  isPollTimedOut,
  isResumeTerminalStatus,
  nextPollIntervalMs,
  shouldContinuePolling,
} from '@/lib/polling'
import type { PrivacyReviewData } from '@/types/resume'

// 后端 LLM 未就绪（无已激活且已验证配置）时的门禁错误码
const LLM_NOT_READY_CODE = 428

export function UploadPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const {
    resumeId, runId, status, currentStep, completedSteps, error, diagnostic,
    setResumeId, setStatus, setPolling, reset,
  } = useResumeStore()
  const { llmReady, loaded: settingsLoaded, refresh: refreshSettings } = useSettingsStore()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [gateOpen, setGateOpen] = useState(false)
  const [privacyReview, setPrivacyReview] = useState<PrivacyReviewData | null>(null)
  const [privacyBusy, setPrivacyBusy] = useState(false)
  const [pollTimedOut, setPollTimedOut] = useState(false)
  const [pollError, setPollError] = useState<string | null>(null)
  const [privacyEntityType, setPrivacyEntityType] = useState('person')
  const privacyTextRef = useRef<HTMLTextAreaElement | null>(null)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pollAbortRef = useRef<AbortController | null>(null)
  const pollEpochRef = useRef(0)
  const uploadAbortRef = useRef<AbortController | null>(null)
  const startTimeRef = useRef<number>(0)
  const pollFailureCountRef = useRef(0)
  const mountedRef = useRef(true)

  // 硬门禁：配置列表已加载且不存在"已激活+已验证"的 LLM 配置时拦截上传
  const llmBlocked = settingsLoaded && !llmReady

  const stopPolling = useCallback(() => {
    pollEpochRef.current += 1
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    pollAbortRef.current?.abort()
    pollAbortRef.current = null
    setPolling(false)
  }, [setPolling])

  const pollStatus = useCallback(async (id: string, epoch = pollEpochRef.current) => {
    if (!mountedRef.current || epoch !== pollEpochRef.current) return
    pollTimerRef.current = null
    const controller = new AbortController()
    pollAbortRef.current = controller

    try {
      const res = await getResumeStatus(id, controller.signal)
      if (!mountedRef.current || epoch !== pollEpochRef.current || controller.signal.aborted) return

      if (res.code !== 0) {
        stopPolling()
        setPollError(t('upload.statusQueryFailed'))
        toast.error(res.message || t('upload.statusQueryFailed'))
        return
      }

      const {
        status: s,
        current_step,
        completed_steps,
        error: err,
        run_id: responseRunId,
        diagnostic: responseDiagnostic,
      } = res.data
      pollFailureCountRef.current = 0
      setPollError(null)
      setStatus(s, current_step, completed_steps, err, responseRunId, responseDiagnostic)
      setPollTimedOut(false)
      // 同步刷新本地历史记录的状态（供「简历列表」页展示）
      useResumeHistoryStore.getState().updateStatus(id, s)

      if (s === 'privacy_review_required') {
        // The status request has completed; use a separate owned request for
        // the review payload so stopping the poller does not abort this fetch.
        const reviewController = new AbortController()
        pollAbortRef.current = reviewController
        try {
          const review = await getPrivacyReview(id, reviewController.signal)
          if (
            review.code === 0 &&
            mountedRef.current &&
            epoch === pollEpochRef.current &&
            !reviewController.signal.aborted
          ) {
            setPrivacyReview(review.data)
          } else if (
            review.code !== 0 &&
            mountedRef.current &&
            epoch === pollEpochRef.current &&
            !reviewController.signal.aborted
          ) {
            setPollError(review.message || t('upload.statusQueryFailed'))
          }
        } catch {
          if (
            mountedRef.current &&
            epoch === pollEpochRef.current &&
            !reviewController.signal.aborted
          ) {
            setPollError(t('upload.statusQueryFailed'))
          }
        } finally {
          if (pollAbortRef.current === reviewController) {
            pollAbortRef.current = null
            pollEpochRef.current += 1
            setPolling(false)
          }
        }
        return
      }

      if (s === 'evaluated') {
        stopPolling()
        toast.success(t('upload.evaluationComplete'))
        navigate(`/resume/${id}`)
        return
      }

      if (s === 'failed') {
        stopPolling()
        return
      }

      const elapsed = Date.now() - startTimeRef.current
      const timedOut = isPollTimedOut(elapsed, RESUME_POLL_MAX_MS)
      if (
        !shouldContinuePolling({
          mounted: mountedRef.current,
          timedOut,
          terminal: isResumeTerminalStatus(s),
        })
      ) {
        stopPolling()
        if (timedOut) {
          setPollTimedOut(true)
          toast.error(t('upload.timedOut'))
        }
        return
      }

      const interval = nextPollIntervalMs(
        elapsed,
        RESUME_POLL_SLOW_AFTER_MS,
        RESUME_POLL_FAST_MS,
        RESUME_POLL_SLOW_MS,
      )
      pollTimerRef.current = setTimeout(() => pollStatus(id, epoch), interval)
    } catch {
      if (!mountedRef.current || epoch !== pollEpochRef.current || controller.signal.aborted) return

      pollFailureCountRef.current += 1
      if (pollFailureCountRef.current >= 3) {
        stopPolling()
        setPollError(t('upload.statusQueryFailed'))
        return
      }

      const elapsed = Date.now() - startTimeRef.current
      const timedOut = isPollTimedOut(elapsed, RESUME_POLL_MAX_MS)
      if (
        !shouldContinuePolling({
          mounted: mountedRef.current,
          timedOut,
          terminal: false,
        })
      ) {
        stopPolling()
        if (timedOut) {
          setPollTimedOut(true)
          toast.error(t('upload.timedOut'))
        }
        return
      }

      const interval = nextPollIntervalMs(
        elapsed,
        RESUME_POLL_SLOW_AFTER_MS,
        RESUME_POLL_FAST_MS,
        RESUME_POLL_SLOW_MS,
      )
      pollTimerRef.current = setTimeout(() => pollStatus(id, epoch), interval)
    } finally {
      if (pollAbortRef.current === controller) pollAbortRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setStatus, stopPolling, navigate])

  const beginPolling = useCallback((id: string) => {
    stopPolling()
    const epoch = pollEpochRef.current
    setPollTimedOut(false)
    setPollError(null)
    pollFailureCountRef.current = 0
    setPolling(true)
    startTimeRef.current = Date.now()
    void pollStatus(id, epoch)
  }, [pollStatus, setPolling, stopPolling])

  const handleUpload = useCallback(async (file: File) => {
    // 双保险：即使绕过了上传区拦截，未就绪时也弹窗引导而不发请求
    if (!useSettingsStore.getState().llmReady) {
      setGateOpen(true)
      return
    }
    stopPolling()
    uploadAbortRef.current?.abort()
    const controller = new AbortController()
    uploadAbortRef.current = controller
    setUploading(true)
    setUploadProgress(30)
    try {
      const res = await uploadResume(file, controller.signal)
      setUploadProgress(100)

      if (res.code === LLM_NOT_READY_CODE) {
        // 后端门禁拦截（前端状态过期等场景），刷新就绪状态并引导配置
        refreshSettings()
        setGateOpen(true)
        return
      }

      if (res.code !== 0) {
        toast.error(res.message)
        return
      }

      const id = res.data.resume_id
      setResumeId(id)
      setPrivacyReview(null)
      setStatus('uploaded', 'text_extract', [], null, res.data.run_id ?? null, null)
      setPollTimedOut(false)
      setPollError(null)
      // 写入本地历史（localStorage，按 resume_id 去重，最多保留 10 条）
      useResumeHistoryStore.getState().addEntry({
        resume_id: id,
        // The client history must not retain the user-controlled filename.
        file_name: 'resume',
        uploaded_at: new Date().toISOString(),
        status: 'uploaded',
      })
      beginPolling(id)
      toast.success(t('upload.uploaded'))
    } catch (err) {
      if (controller.signal.aborted || !mountedRef.current) return
      toast.error(err instanceof Error ? err.message : t('upload.uploadFailed'))
    } finally {
      if (uploadAbortRef.current === controller) uploadAbortRef.current = null
      setUploading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beginPolling, setResumeId, setStatus, refreshSettings, stopPolling, t])

  const maskSelectedPrivacyText = useCallback(async () => {
    if (!resumeId || !privacyReview || !privacyTextRef.current) return
    const { selectionStart, selectionEnd } = privacyTextRef.current
    if (selectionStart === selectionEnd) return
    uploadAbortRef.current?.abort()
    const controller = new AbortController()
    uploadAbortRef.current = controller
    setPrivacyBusy(true)
    try {
      const response = await addPrivacyMasks(resumeId, privacyReview.revision, [{
        start: selectionStart,
        end: selectionEnd,
        entity_type: privacyEntityType,
      }], controller.signal)
      if (response.code !== 0) {
        toast.error(response.message || t('upload.privacyMaskFailed'))
        return
      }
      setPrivacyReview((current) => current ? { ...current, ...response.data } : response.data)
    } catch {
      if (mountedRef.current && !controller.signal.aborted) {
        toast.error(t('upload.privacyMaskFailed'))
      }
    } finally {
      if (uploadAbortRef.current === controller) uploadAbortRef.current = null
      setPrivacyBusy(false)
    }
  }, [privacyEntityType, privacyReview, resumeId, t])

  const approvePrivacyReview = useCallback(async () => {
    if (!resumeId || !privacyReview) return
    uploadAbortRef.current?.abort()
    const controller = new AbortController()
    uploadAbortRef.current = controller
    setPrivacyBusy(true)
    try {
      const response = await approvePrivacy(resumeId, privacyReview.revision, controller.signal)
      if (response.code !== 0) {
        toast.error(response.message || t('upload.privacyApproveFailed'))
        return
      }
      setPrivacyReview(null)
      setStatus(
        'text_masked',
        'llm_parse',
        ['text_extract', 'privacy_scan'],
        null,
        response.data.run_id ?? runId,
        null,
      )
      beginPolling(resumeId)
      toast.success(t('upload.privacyApproved'))
    } catch {
      if (mountedRef.current && !controller.signal.aborted) {
        toast.error(t('upload.privacyApproveFailed'))
      }
    } finally {
      if (uploadAbortRef.current === controller) uploadAbortRef.current = null
      setPrivacyBusy(false)
    }
  }, [beginPolling, privacyReview, resumeId, runId, setStatus, t])

  const handleRetry = useCallback(async () => {
    if (!resumeId) return
    stopPolling()
    uploadAbortRef.current?.abort()
    const controller = new AbortController()
    uploadAbortRef.current = controller
    try {
      const res = await retryResume(resumeId, controller.signal)
      if (res.code === LLM_NOT_READY_CODE) {
        // 重跑同样受门禁保护，引导用户先完成配置
        refreshSettings()
        setGateOpen(true)
        return
      }
      if (res.code !== 0) {
        toast.error(res.message || t('upload.retryFailed'))
        return
      }
      setStatus(
        res.data.status,
        res.data.current_step,
        res.data.completed_steps,
        res.data.error,
        res.data.run_id,
        res.data.diagnostic,
      )
      setPrivacyReview(null)
      beginPolling(resumeId)
      toast.success(t('upload.retrying'))
    } catch {
      if (mountedRef.current && !controller.signal.aborted) toast.error(t('upload.retryFailed'))
    } finally {
      if (uploadAbortRef.current === controller) uploadAbortRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [beginPolling, resumeId, setStatus, refreshSettings, stopPolling, t])

  const handleRecheck = useCallback(() => {
    if (resumeId) beginPolling(resumeId)
  }, [beginPolling, resumeId])

  const handleReset = useCallback(() => {
    stopPolling()
    uploadAbortRef.current?.abort()
    uploadAbortRef.current = null
    setPrivacyReview(null)
    setPollTimedOut(false)
    setPollError(null)
    reset()
  }, [reset, stopPolling])

  useEffect(() => {
    mountedRef.current = true
    // 进入上传页时拉取 LLM 配置就绪状态，供门禁判定
    refreshSettings()
    if (resumeId && status && !isResumeTerminalStatus(status)) {
      beginPolling(resumeId)
    }
    return () => {
      mountedRef.current = false
      pollEpochRef.current += 1
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
      pollAbortRef.current?.abort()
      uploadAbortRef.current?.abort()
      pollTimerRef.current = null
      pollAbortRef.current = null
      uploadAbortRef.current = null
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-black">{t('upload.title')}</h1>

      {!resumeId && (
        <div
          onClickCapture={(e) => {
            if (llmBlocked) {
              e.stopPropagation()
              setGateOpen(true)
            }
          }}
          onDropCapture={(e) => {
            if (llmBlocked) {
              e.preventDefault()
              e.stopPropagation()
              setGateOpen(true)
            }
          }}
        >
          <FileUploader onFileSelect={handleUpload} disabled={uploading || llmBlocked} />
        </div>
      )}

      {uploading && (
        <div className="flex items-center gap-3 rounded-base border-2 border-border bg-secondary-background p-3">
          <Loader2 className="size-5 shrink-0 animate-spin" />
          <div className="flex-1 space-y-2">
            <p className="text-sm font-bold">{t('upload.uploading')}</p>
            <Progress value={uploadProgress} />
          </div>
        </div>
      )}

      <UploadWorkflowPanel
        resumeId={resumeId}
        status={status}
        currentStep={currentStep}
        completedSteps={completedSteps}
        error={error}
        runId={runId}
        diagnostic={diagnostic}
        privacyReview={privacyReview}
        privacyBusy={privacyBusy}
        pollTimedOut={pollTimedOut}
        pollError={pollError}
        privacyEntityType={privacyEntityType}
        privacyTextRef={privacyTextRef}
        onPrivacyEntityTypeChange={setPrivacyEntityType}
        onMaskSelection={() => void maskSelectedPrivacyText()}
        onApprovePrivacy={() => void approvePrivacyReview()}
        onRetry={() => void handleRetry()}
        onRecheck={handleRecheck}
        onReset={handleReset}
      />

      {!resumeId && !uploading && llmBlocked && (
        <Alert variant="destructive">
          <TriangleAlert />
          <AlertTitle>{t('llmGate.title')}</AlertTitle>
          <AlertDescription>
            <p>
              {t('llmGate.description')}{' '}
              <button
                type="button"
                onClick={() => setGateOpen(true)}
                className="inline-flex items-center gap-1 font-bold underline underline-offset-2 hover:opacity-80"
              >
                {t('llmGate.configureNow')}
                <ArrowRight className="size-3.5" />
              </button>
            </p>
          </AlertDescription>
        </Alert>
      )}

      <LLMGateDialog open={gateOpen} onOpenChange={setGateOpen} />
    </div>
  )
}
