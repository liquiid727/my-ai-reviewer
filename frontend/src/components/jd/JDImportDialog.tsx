import { useMemo, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2, Plus, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { importJDFile, importJDImage, importJDManual, importJDText, importJDUrl } from '@/api/jd'
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
import type { JDDetail, JDSkill } from '@/types/jd'

type ImportMode = 'text' | 'file' | 'image' | 'url' | 'manual'

function formatFileSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

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
  const [image, setImage] = useState<File | null>(null)
  const [manualTitle, setManualTitle] = useState('')
  const [manualCompany, setManualCompany] = useState('')
  const [manualLocation, setManualLocation] = useState('')
  const [manualDepartment, setManualDepartment] = useState('')
  const [manualResponsibilities, setManualResponsibilities] = useState('')
  const [manualSkills, setManualSkills] = useState<string[]>([])
  const [manualSkillInput, setManualSkillInput] = useState('')
  const [manualNotes, setManualNotes] = useState('')
  const [allowDuplicate, setAllowDuplicate] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const valid = useMemo(() => {
    if (mode === 'text') return rawText.trim().length > 0 && rawText.length <= 100_000
    if (mode === 'manual') {
      return manualTitle.trim().length > 0
        && manualTitle.length <= 200
        && manualSkills.every((skill) => skill.length <= 500)
    }
    if (mode === 'url') {
      try {
        const parsed = new URL(url)
        return ['http:', 'https:'].includes(parsed.protocol)
      } catch {
        return false
      }
    }
    return (file !== null || image !== null) && (file ?? image)!.size <= 10 * 1024 * 1024
  }, [file, image, manualSkills, manualTitle, mode, rawText, url])

  const reset = () => {
    setMode('text')
    setRawText('')
    setTitle('')
    setCompany('')
    setUrl('')
    setFile(null)
    setImage(null)
    setManualTitle('')
    setManualCompany('')
    setManualLocation('')
    setManualDepartment('')
    setManualResponsibilities('')
    setManualSkills([])
    setManualSkillInput('')
    setManualNotes('')
    setAllowDuplicate(false)
  }

  const handleOpenChange = (next: boolean) => {
    if (!next && !submitting) reset()
    onOpenChange(next)
  }

  const addSkill = () => {
    const name = manualSkillInput.trim()
    if (name && !manualSkills.includes(name)) setManualSkills([...manualSkills, name])
    setManualSkillInput('')
  }

  const submit = async () => {
    if (!valid || submitting) return
    setSubmitting(true)
    try {
      let response
      if (mode === 'text') {
        response = await importJDText({
          raw_text: rawText.trim(),
          title: title.trim() || undefined,
          company: company.trim() || undefined,
          allow_duplicate: allowDuplicate,
        })
      } else if (mode === 'url') {
        response = await importJDUrl({ url: url.trim(), allow_duplicate: allowDuplicate })
      } else if (mode === 'manual') {
        const skills: JDSkill[] = manualSkills.map((name) => ({ name }))
        response = await importJDManual({
          title: manualTitle.trim(),
          company: manualCompany.trim() || null,
          location: manualLocation.trim() || null,
          department: manualDepartment.trim() || null,
          responsibilities: manualResponsibilities
            .split('\n')
            .map((line) => line.trim())
            .filter(Boolean)
            .slice(0, 50),
          required_skills: skills,
          notes: manualNotes.trim() || null,
          allow_duplicate: allowDuplicate,
        })
      } else if (mode === 'file') {
        response = await importJDFile(file as File, allowDuplicate)
      } else {
        response = await importJDImage(image as File, allowDuplicate)
      }
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
          <TabsList className="grid h-auto w-full grid-cols-5">
            <TabsTrigger value="text">{t('jd.importMode.text')}</TabsTrigger>
            <TabsTrigger value="file">{t('jd.importMode.file')}</TabsTrigger>
            <TabsTrigger value="image">{t('jd.importMode.image')}</TabsTrigger>
            <TabsTrigger value="url">{t('jd.importMode.url')}</TabsTrigger>
            <TabsTrigger value="manual">{t('jd.importMode.manual')}</TabsTrigger>
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
              {file && (
                <p className="break-all text-sm">
                  {file.name} · {file.type || t('jd.unknownType')} · {formatFileSize(file.size)}
                </p>
              )}
            </div>
          </TabsContent>
          <TabsContent value="image" className="space-y-4 pt-3">
            <div className="space-y-2">
              <Label htmlFor="jd-image">{t('jd.image')}</Label>
              <Input
                id="jd-image"
                type="file"
                accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
                onChange={(event) => setImage(event.target.files?.[0] ?? null)}
              />
              <p className="text-xs text-muted-foreground">{t('jd.imageHelp')}</p>
              {image && (
                <p className="break-all text-sm">
                  {image.name} · {image.type || t('jd.unknownType')} · {formatFileSize(image.size)}
                </p>
              )}
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
          <TabsContent value="manual" className="space-y-4 pt-3">
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="jd-manual-title">{t('jd.manualTitle')} *</Label>
                <Input
                  id="jd-manual-title"
                  value={manualTitle}
                  maxLength={200}
                  placeholder={t('jd.manualTitlePlaceholder')}
                  onChange={(event) => setManualTitle(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jd-manual-company">{t('jd.manualCompany')}</Label>
                <Input
                  id="jd-manual-company"
                  value={manualCompany}
                  maxLength={200}
                  onChange={(event) => setManualCompany(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jd-manual-location">{t('jd.manualLocation')}</Label>
                <Input
                  id="jd-manual-location"
                  value={manualLocation}
                  maxLength={200}
                  onChange={(event) => setManualLocation(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="jd-manual-department">{t('jd.manualDepartment')}</Label>
                <Input
                  id="jd-manual-department"
                  value={manualDepartment}
                  maxLength={200}
                  onChange={(event) => setManualDepartment(event.target.value)}
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t('jd.manualSkills')}</Label>
              <div className="flex gap-2">
                <Input
                  value={manualSkillInput}
                  maxLength={500}
                  placeholder={t('jd.manualSkillsPlaceholder')}
                  onChange={(event) => setManualSkillInput(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') {
                      event.preventDefault()
                      addSkill()
                    }
                  }}
                />
                <Button type="button" variant="neutral" onClick={addSkill}><Plus className="size-4" /></Button>
              </div>
              {manualSkills.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {manualSkills.map((skill) => (
                    <span key={skill} className="flex items-center gap-1 rounded-base border-2 border-black bg-secondary-background px-2 py-0.5 text-xs">
                      {skill}
                      <button
                        type="button"
                        className="text-muted-foreground hover:text-foreground"
                        onClick={() => setManualSkills(manualSkills.filter((name) => name !== skill))}
                        aria-label={t('common.remove')}
                      >
                        <X className="size-3" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-manual-responsibilities">{t('jd.manualResponsibilities')}</Label>
              <textarea
                id="jd-manual-responsibilities"
                className="min-h-24 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-black"
                value={manualResponsibilities}
                placeholder={t('jd.manualResponsibilitiesPlaceholder')}
                onChange={(event) => setManualResponsibilities(event.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="jd-manual-notes">{t('jd.manualNotes')}</Label>
              <textarea
                id="jd-manual-notes"
                className="min-h-16 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm focus-visible:outline-hidden focus-visible:ring-2 focus-visible:ring-black"
                value={manualNotes}
                maxLength={1000}
                onChange={(event) => setManualNotes(event.target.value)}
              />
              <p className="text-xs text-muted-foreground">{t('jd.manualReviewNote')}</p>
            </div>
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
