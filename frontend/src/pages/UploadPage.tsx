import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router'
import { toast } from 'sonner'
import { FileUploader } from '@/components/FileUploader'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { Alert, AlertTitle, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { useResumeStore } from '@/stores/resumeStore'
import { uploadResume, getResumeStatus, retryResume } from '@/api/resume'

const STEP_LABELS: Record<string, string> = {
  text_extract: 'Extracting text',
  llm_parse: 'Parsing with AI',
  classify: 'Classifying',
  evaluate: 'Evaluating',
  done: 'Complete',
  failed: 'Failed',
}

const MAX_POLL_DURATION = 10 * 60 * 1000

export function UploadPage() {
  const navigate = useNavigate()
  const {
    resumeId, status, currentStep, completedSteps, error,
    setResumeId, setStatus, setPolling, reset,
  } = useResumeStore()
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState(0)
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const startTimeRef = useRef<number>(0)
  const mountedRef = useRef(true)

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
        toast.error(res.message || 'Failed to check status')
        return
      }

      const { status: s, current_step, completed_steps, error: err } = res.data
      setStatus(s, current_step, completed_steps, err)

      if (s === 'evaluated') {
        stopPolling()
        toast.success('Resume evaluation complete!')
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
        toast.error('Processing timed out. Please try again later.')
        return
      }

      const interval = elapsed > 3 * 60 * 1000 ? 5000 : 2000
      pollTimerRef.current = setTimeout(() => pollStatus(id), interval)
    } catch {
      if (!mountedRef.current) return

      const elapsed = Date.now() - startTimeRef.current
      if (elapsed > MAX_POLL_DURATION) {
        stopPolling()
        toast.error('Processing timed out. Please try again later.')
        return
      }

      const interval = elapsed > 3 * 60 * 1000 ? 5000 : 2000
      pollTimerRef.current = setTimeout(() => pollStatus(id), interval)
    }
  }, [setStatus, stopPolling, navigate])

  const handleUpload = useCallback(async (file: File) => {
    setUploading(true)
    setUploadProgress(30)
    try {
      const res = await uploadResume(file)
      setUploadProgress(100)

      if (res.code !== 0) {
        toast.error(res.message)
        return
      }

      const id = res.data.resume_id
      setResumeId(id)
      setStatus('uploaded', 'text_extract', [], null)
      setPolling(true)
      startTimeRef.current = Date.now()
      pollStatus(id)
      toast.success('Resume uploaded, processing started')
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [setResumeId, setStatus, setPolling, pollStatus])

  const handleRetry = useCallback(async () => {
    if (!resumeId) return
    try {
      const res = await retryResume(resumeId)
      if (res.code !== 0) {
        toast.error(res.message || 'Retry failed')
        return
      }
      setStatus('uploaded', 'text_extract', [], null)
      setPolling(true)
      startTimeRef.current = Date.now()
      pollStatus(resumeId)
      toast.success('Retrying processing...')
    } catch {
      toast.error('Retry failed')
    }
  }, [resumeId, setStatus, setPolling, pollStatus])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current)
    }
  }, [])

  const progress = completedSteps.length * 25

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-black">Upload Resume</h1>

      {!resumeId && (
        <FileUploader onFileSelect={handleUpload} disabled={uploading} />
      )}

      {uploading && (
        <div className="space-y-2">
          <p className="font-bold">Uploading...</p>
          <Progress value={uploadProgress} />
        </div>
      )}

      {resumeId && status && status !== 'evaluated' && (
        <div className="rounded-lg border-4 border-black bg-white p-6 shadow-[4px_4px_0_0_#000]">
          <div className="mb-4 flex items-center gap-3">
            <h2 className="text-xl font-black">Processing</h2>
            <Badge variant={status === 'failed' ? 'neutral' : 'default'} className={status === 'failed' ? 'bg-red-500 text-white' : ''}>
              {status}
            </Badge>
          </div>

          {status !== 'failed' && (
            <>
              <Progress value={progress} className="mb-3" />
              <p className="text-sm font-medium">
                {STEP_LABELS[currentStep || ''] || currentStep || 'Starting...'}
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
                <AlertTitle>Processing Failed</AlertTitle>
                <AlertDescription>{error || 'Unknown error'}</AlertDescription>
              </Alert>
              <div className="flex gap-2">
                <Button onClick={handleRetry}>Retry</Button>
                <Button variant="neutral" onClick={reset}>Upload Another</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {!resumeId && !uploading && (
        <Alert>
          <AlertTitle>Tip</AlertTitle>
          <AlertDescription>
            Make sure you've configured your AI model in{' '}
            <a href="/settings" className="font-bold underline">Settings</a>
            {' '}before uploading.
          </AlertDescription>
        </Alert>
      )}
    </div>
  )
}
