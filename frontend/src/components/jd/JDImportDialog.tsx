import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { importJDFile, importJDImages, importJDText, importJDUrl } from '@/api/jd'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import type { JDDetail } from '@/types/jd'

type ImportMode = 'text' | 'file' | 'url' | 'image'

interface JDImportDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: (jd: JDDetail) => void
  onLLMGate: () => void
}

export function JDImportDialog({ open, onOpenChange, onCreated, onLLMGate }: JDImportDialogProps) {
  const { t } = useTranslation()
  const [mode, setMode] = useState<ImportMode>('text')
  const [rawText, setRawText] = useState('')
  const [title, setTitle] = useState('')
  const [company, setCompany] = useState('')
  const [url, setUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [images, setImages] = useState<File[]>([])
  const [ackVision, setAckVision] = useState(false)
  const [allowDuplicate, setAllowDuplicate] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const valid = useMemo(() => {
    if (mode === 'text') return rawText.trim().length > 0 && rawText.length <= 100_000
    if (mode === 'url') {
      try {
        const parsed = new URL(url)
        return ['http:', 'https:'].includes(parsed.protocol)
      } catch {
        return false
      }
    }
    if (mode === 'image') {
      const total = images.reduce((sum, image) => sum + image.size, 0)
      return images.length >= 1 && images.length <= 8 && images.every((image) => image.size <= 10 * 1024 * 1024) && total <= 30 * 1024 * 1024 && ackVision
    }
    return file !== null && file.size <= 10 * 1024 * 1024
  }, [ackVision, file, images, mode, rawText, url])

  const reset = () => {
    setMode('text')
    setRawText('')
    setTitle('')
    setCompany('')
    setUrl('')
    setFile(null)
    setImages([])
    setAckVision(false)
    setAllowDuplicate(false)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next && !submitting) reset()
    onOpenChange(next)
  }

  const submit = async () => {
    if (!valid || submitting) return
    setSubmitting(true)
    try {
      const response = mode === 'text'
        ? await importJDText({
          raw_text: rawText.trim(),
          title: title.trim() || undefined,
          company: company.trim() || undefined,
          allow_duplicate: allowDuplicate,
        })
        : mode === 'url'
          ? await importJDUrl({ url: url.trim(), allow_duplicate: allowDuplicate })
          : mode === 'image'
            ? await importJDImages({
              images,
              title: title.trim() || undefined,
              company: company.trim() || undefined,
              allowDuplicate,
              acknowledgeExternalVision: ackVision,
            })
            : await importJDFile(file as File, allowDuplicate)
      if (response.code === 428) {
        onLLMGate()
        return
      }
      if (response.code !== 0) {
        toast.error(response.message || t('jd.importFailed'))
        return
      }
      onCreated(response.data)
      toast.success(t('jd.importStarted'))
      handleOpenChange(false)
    } catch (error) {
      toast.error((error as Error).message || t('jd.importFailed'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>{t('jd.importTitle')}</DialogTitle>
          <DialogDescription>{t('jd.importDescription')}</DialogDescription>
        </DialogHeader>
        <Tabs value={mode} onValueChange={(value) => setMode(value as ImportMode)}>
          <TabsList className="grid h-auto w-full grid-cols-4">
            <TabsTrigger value="text">{t('jd.importMode.text')}</TabsTrigger>
            <TabsTrigger value="file">{t('jd.importMode.file')}</TabsTrigger>
            <TabsTrigger value="url">{t('jd.importMode.url')}</TabsTrigger>
            <TabsTrigger value="image">{t('jd.importMode.image')}</TabsTrigger>
          </TabsList>
          <TabsContent value="text" className="space-y-4 pt-3">
            <div className="space-y-2">
              <Label htmlFor="jd-title">{t('jd.titleOptional')}</Label>
              <Input id="jd-title" value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-company">{t('jd.companyOptional')}</Label>
              <Input id="jd-company" value={company} maxLength={200} onChange={(event) => setCompany(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-text">{t('jd.rawText')}</Label>
              <textarea
                id="jd-text"
                className="min-h-44 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-black"
                value={rawText}
                maxLength={100_000}
                onChange={(event) => setRawText(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">{rawText.length.toLocaleString()} / 100,000</p>
            </div>
          </TabsContent>
          <TabsContent value="file" className="space-y-4 pt-3">
            <div className="space-y-2">
              <Label htmlFor="jd-file">{t('jd.file')}</Label>
              <Input
                id="jd-file"
                type="file"
                accept=".pdf,.docx,.txt,.md,text/plain,text/markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                onChange={(event) => setFile(event.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted-foreground">{t('jd.fileHelp')}</p>
              {file && <p className="break-all text-sm">{file.name}</p>}
            </div>
          </TabsContent>
          <TabsContent value="url" className="space-y-4 pt-3">
            <div className="space-y-2">
              <Label htmlFor="jd-url">{t('jd.url')}</Label>
              <Input
                id="jd-url"
                type="url"
                value={url}
                placeholder="https://example.com/jobs/123"
                onChange={(event) => setUrl(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">{t('jd.urlHelp')}</p>
            </div>
          </TabsContent>
          <TabsContent value="image" className="space-y-4 pt-3">
            <div className="space-y-2">
              <Label htmlFor="jd-images">{t('jd.image')}</Label>
              <Input
                id="jd-images"
                type="file"
                multiple
                accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                onChange={(event) => setImages(Array.from(event.target.files ?? []))}
              />
              <p className="text-xs text-muted-foreground">{t('jd.imageHelp')}</p>
              {images.length > 0 && (
                <ol className="list-decimal space-y-1 pl-5 text-sm">
                  {images.map((image, index) => <li key={`${image.name}-${index}`} className="break-all">{image.name}</li>)}
                </ol>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-image-title">{t('jd.titleOptional')}</Label>
              <Input id="jd-image-title" value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-image-company">{t('jd.companyOptional')}</Label>
              <Input id="jd-image-company" value={company} maxLength={200} onChange={(event) => setCompany(event.target.value)} />
            </div>
            <label className="flex items-start gap-2 rounded-base border-2 border-black bg-secondary-background p-3 text-sm">
              <input
                type="checkbox"
                className="mt-1 size-4 accent-black"
                checked={ackVision}
                onChange={(event) => setAckVision(event.target.checked)}
              />
              <span>{t('jd.visionDisclosure')}</span>
            </label>
          </TabsContent>
        </Tabs>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            className="mt-1 size-4 accent-black"
            checked={allowDuplicate}
            onChange={(event) => setAllowDuplicate(event.target.checked)}
          />
          <span>{t('jd.allowDuplicate')}</span>
        </label>
        <DialogFooter>
          <Button variant="neutral" type="button" onClick={() => handleOpenChange(false)} disabled={submitting}>
            {t('common.cancel')}
          </Button>
          <Button type="button" onClick={submit} disabled={!valid || submitting}>
            {submitting ? <Loader2 className="size-4 animate-spin" /> : <Upload className="size-4" />}
            {submitting ? t('jd.importing') : t('jd.import')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
