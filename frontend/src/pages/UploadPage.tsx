import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { useTranslation } from 'react-i18next'
import { FileUploader } from '@/components/FileUploader'
import { LLMGateDialog } from '@/components/LLMGateDialog'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { useResumeStore } from '@/stores/resumeStore'
import { useResumeHistoryStore } from '@/stores/resumeHistoryStore'
import { useSettingsStore } from '@/stores/settingsStore'
import { uploadResume, getResumeStatus, retryResume } from '@/api/resume'

const MAX_POLL_DURATION = 10 * 60 * 1000

// 后端 LLM 未就绪（无已激活且已验证配置）时的门禁错误码
const LLM_NOT_READY_CODE = 428

export function UploadPage() {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const {
    resumeId, status, currentStep, completedSteps, error,
    setResumeId, setStatus, setPolling, reset,
  } = useResumeStore()
  const { llmReady, loaded: settingsLoaded, refresh: refreshSettings } = useSettingsStore()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [gateOpen, setGateOpen] = useState(false)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const startTimeRef = useRef<number>(0)
  const mountedRef = useRef(true)

  // 硬门禁：配置列表已加载且不存在"已激活+已验证"的 LLM 配置时拦截上传
  const llmBlocked = settingsLoaded && !llmReady

  const stopPolling = useCallback(() => {
    if (pollTimerRef.current) {
      clearTimeout(pollTimerRef.current)
      pollTimerRef.current = null
    }
    setPolling(false)
  }, [setPolling])

  const pollStatus = useCallback(async (id: string) => {
    if (!mountedRef.current) return

    try {
      const res = await getResumeStatus(id)
      if (!mountedRef.current) return

      if (res.code !== 0) {
        stopPolling()
        toast.error(res.message || t('upload.timedOut'))
        return
      }

      const { status: s, current_step, completed_steps, error: err } = res.data
      setStatus(s, current_step, completed_steps, err)
      // 同步刷新本地历史记录的状态（供「简历列表」页展示）
      useResumeHistoryStore.getState().updateStatus(id, s)

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
      if (elapsed > MAX_POLL_DURATION) {
        stopPolling()
        toast.error(t('upload.timedOut'))
        return
      }

      const interval = elapsed > 3 * 60 * 1000 ? 5000 : 2000
      pollTimerRef.current = setTimeout(() => pollStatus(id), interval)
    } catch {
      if (!mountedRef.current) return

      const elapsed = Date.now() - startTimeRef.current
      if (elapsed > MAX_POLL_DURATION) {
        stopPolling()
        toast.error(t('upload.timedOut'))
        return
      }

      const interval = elapsed > 3 * 60 * 1000 ? 5000 : 2000
      pollTimerRef.current = setTimeout(() => pollStatus(id), interval)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setStatus, stopPolling, navigate])

  const handleUpload = useCallback(async (file: File) => {
    // 双保险：即使绕过了上传区拦截，未就绪时也弹窗引导而不发请求
    if (!useSettingsStore.getState().llmReady) {
      setGateOpen(true)
      return
    }
    setUploading(true)
    setUploadProgress(30)
    try {
      const res = await uploadResume(file)
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
      setStatus('uploaded', 'text_extract', [], null)
      // 写入本地历史（localStorage，按 resume_id 去重，最多保留 10 条）
      useResumeHistoryStore.getState().addEntry({
        resume_id: id,
        file_name: file.name,
        uploaded_at: new Date().toISOString(),
        status: 'uploaded',
      })
      setPolling(true)
      startTimeRef.current = Date.now()
      pollStatus(id)
      toast.success(t('upload.uploaded'))
    } catch (err) {
      toast.error(err instanceof Error ? err.message : t('upload.uploadFailed'))
    } finally {
      setUploading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [setResumeId, setStatus, setPolling, pollStatus, refreshSettings])

  const handleRetry = useCallback(async () => {
    if (!resumeId) return
    try {
      const res = await retryResume(resumeId)
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
      setStatus('uploaded', 'text_extract', [], null)
      setPolling(true)
      startTimeRef.current = Date.now()
      pollStatus(resumeId)
      toast.success(t('upload.retrying'))
    } catch {
      toast.error(t('upload.retryFailed'))
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId, setStatus, setPolling, pollStatus, refreshSettings])

  useEffect(() => {
    mountedRef.current = true
    // 进入上传页时拉取 LLM 配置就绪状态，供门禁判定
    refreshSettings()
    return () => {
      mountedRef.current = false
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const progress = completedSteps.length * 25

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
        <div className="space-y-2">
          <p className="font-bold">{t('upload.uploading')}</p>
          <Progress value={uploadProgress} />
        </div>
      )}

      {resumeId && status && status !== 'evaluated' && (
        <div className="rounded-lg border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_#000]">
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-xl font-black">{t('upload.processing')}</h2>
            <Badge variant={status === 'failed' ? 'neutral' : 'default'} className={status === 'failed' ? 'bg-red-500 text-white' : ''}>
              {status}
            </Badge>
          </div>

          {status !== 'failed' && (
            <>
              <Progress value={progress} className="mb-3" />
              <p className="text-sm font-medium">
                {t(`upload.step.${currentStep || 'starting'}`)}
              </p>
              <div className="mt-2 flex flex-wrap gap-1">
                {completedSteps.map((step) => (
                  <Badge key={step} variant="default">{step}</Badge>
                ))}
              </div>
            </>
          )}

          {status === 'failed' && (
            <div className="space-y-3">
              <Alert variant="destructive">
                <AlertTitle>{t('upload.processingFailed')}</AlertTitle>
                <AlertDescription>{error || t('common.loading')}</AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button onClick={handleRetry}>{t('upload.retry')}</Button>
                <Button variant="neutral" onClick={reset}>{t('upload.uploadAnother')}</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {!resumeId && !uploading && (
        llmBlocked ? (
          <Alert variant="destructive">
            <AlertTitle>{t('llmGate.title')}</AlertTitle>
            <AlertDescription>
              {t('llmGate.description')}{' '}
              <button
                type="button"
                onClick={() => setGateOpen(true)}
                className="font-bold underline"
              >
                {t('llmGate.configureNow')}
              </button>
            </AlertDescription>
          </Alert>
        ) : (
          <Alert>
            <AlertTitle>{t('upload.tipTitle')}</AlertTitle>
            <AlertDescription>
              {t('upload.tip')}{' '}
              <a href="/settings" className="font-bold underline">{t('nav.settings')}</a>
            </AlertDescription>
          </Alert>
        )
      )}

      <LLMGateDialog open={gateOpen} onOpenChange={setGateOpen} />
    </div>
  )
}
