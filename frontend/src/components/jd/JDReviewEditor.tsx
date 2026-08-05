import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { JDDetail, JDReviewDraft } from '@/types/jd'

function lines(value: string): string[] {
  return value.split('\n').map((line) => line.trim()).filter(Boolean)
}

function nextKey(existing: Array<{ key: string }>, prefix: string): string {
  const used = new Set(existing.map((item) => item.key))
  let index = 1
  while (used.has(`${prefix}-${index}`)) index += 1
  return `${prefix}-${index}`
}

interface JDReviewEditorProps {
  jd: JDDetail
  onSave: (draft: JDReviewDraft) => Promise<boolean>
}

export function JDReviewEditor({ jd, onSave }: JDReviewEditorProps) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState<JDReviewDraft>(() => jd.review_draft ?? {})
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const draftKey = `${jd.id}:${jd.review_revision}`

  const setScalar = (field: keyof JDReviewDraft, value: string | null) => {
    setDraft((current) => ({ ...current, [field]: value }))
    setSaved(false)
  }

  const addItem = (field: 'responsibilities' | 'required_skills' | 'preferred_skills', value: string) => {
    setDraft((current) => {
      const items = current[field] ?? []
      return {
        ...current,
        [field]: [
          ...items,
          { key: nextKey(items, field), value, evidence: null, evidence_status: 'unavailable', confidence: 0, provenance: 'manual' },
        ],
      }
    })
    setSaved(false)
  }

  const removeItem = (field: 'responsibilities' | 'required_skills' | 'preferred_skills', key: string) => {
    setDraft((current) => ({ ...current, [field]: (current[field] ?? []).filter((item) => item.key !== key) }))
    setSaved(false)
  }

  const addHardCondition = (value: string) => {
    setDraft((current) => {
      const items = current.hard_conditions ?? []
      return {
        ...current,
        hard_conditions: [
          ...items,
          { key: nextKey(items, 'hc'), category: 'other', value, evidence: null, evidence_status: 'unavailable', confidence: 0, provenance: 'manual' },
        ],
      }
    })
    setSaved(false)
  }

  const removeHardCondition = (key: string) => {
    setDraft((current) => ({ ...current, hard_conditions: (current.hard_conditions ?? []).filter((item) => item.key !== key) }))
    setSaved(false)
  }

  const setList = (field: 'languages' | 'certificates' | 'interview_clues', value: string) => {
    setDraft((current) => ({ ...current, [field]: lines(value) }))
    setSaved(false)
  }

  const itemRows = (field: 'responsibilities' | 'required_skills' | 'preferred_skills') => (draft[field] ?? []).map((item) => (
    <li key={item.key} className="flex flex-col gap-1 rounded-base border-2 border-black bg-secondary-background p-2 sm:flex-row sm:items-center sm:justify-between">
      <span className="min-w-0 break-words text-sm">
        {item.value}
        {item.provenance === 'manual' && <span className="ml-2 text-xs text-muted-foreground">{t('jd.manualEdits')}</span>}
        {item.evidence && <span className="ml-2 block text-xs text-muted-foreground sm:inline">“{item.evidence}”</span>}
      </span>
      <Button type="button" size="sm" variant="neutral" onClick={() => removeItem(field, item.key)}>{t('common.remove')}</Button>
    </li>
  ))

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const ok = await onSave(draft)
      if (ok) setSaved(true)
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="space-y-5" onSubmit={submit}>
      {saved && <p className="text-sm text-muted-foreground">{t('jd.saved')}</p>}
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="jd-review-title">{t('jd.field.title')}</Label><Input id="jd-review-title" value={draft.title ?? ''} maxLength={200} onChange={(event) => setScalar('title', event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-review-company">{t('jd.field.company')}</Label><Input id="jd-review-company" value={draft.company ?? ''} maxLength={200} onChange={(event) => setScalar('company', event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-review-location">{t('jd.field.location')}</Label><Input id="jd-review-location" value={draft.location ?? ''} maxLength={200} onChange={(event) => setScalar('location', event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-review-education">{t('jd.field.education')}</Label><Input id="jd-review-education" value={draft.education ?? ''} maxLength={200} onChange={(event) => setScalar('education', event.target.value)} /></div>
      </div>

      {(['required_skills', 'preferred_skills', 'responsibilities'] as const).map((field) => (
        <div key={field} className="space-y-2">
          <Label>{t(`jd.field.${field}`)}</Label>
          <ul className="space-y-2">{itemRows(field)}</ul>
          <div className="flex gap-2">
            <Input
              placeholder={t('jd.addItemPlaceholder')}
              maxLength={500}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  event.preventDefault()
                  const value = event.currentTarget.value.trim()
                  if (value) addItem(field, value)
                  event.currentTarget.value = ''
                }
              }}
            />
            <Button
              type="button"
              variant="neutral"
              onClick={(event) => {
                const input = event.currentTarget.previousElementSibling as HTMLInputElement | null
                if (input?.value.trim()) {
                  addItem(field, input.value.trim())
                  input.value = ''
                }
              }}
            >
              {t('common.add')}
            </Button>
          </div>
        </div>
      ))}

      <div className="space-y-2">
        <Label>{t('jd.field.hardConditions')}</Label>
        <ul className="space-y-2">{draft.hard_conditions?.map((item) => (
          <li key={item.key} className="flex flex-col gap-1 rounded-base border-2 border-black bg-secondary-background p-2 sm:flex-row sm:items-center sm:justify-between">
            <span className="min-w-0 break-words text-sm">{item.value}{item.evidence && <span className="ml-2 block text-xs text-muted-foreground sm:inline">“{item.evidence}”</span>}</span>
            <Button type="button" size="sm" variant="neutral" onClick={() => removeHardCondition(item.key)}>{t('common.remove')}</Button>
          </li>
        ))}</ul>
        <div className="flex gap-2">
          <Input
            placeholder={t('jd.addHardConditionPlaceholder')}
            maxLength={500}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault()
                const value = event.currentTarget.value.trim()
                if (value) addHardCondition(value)
                event.currentTarget.value = ''
              }
            }}
          />
          <Button
            type="button"
            variant="neutral"
            onClick={(event) => {
              const input = event.currentTarget.previousElementSibling as HTMLInputElement | null
              if (input?.value.trim()) {
                addHardCondition(input.value.trim())
                input.value = ''
              }
            }}
          >
            {t('common.add')}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="jd-review-languages">{t('jd.field.languages')}</Label><textarea id="jd-review-languages" className="min-h-20 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={(draft.languages ?? []).join('\n')} onChange={(event) => setList('languages', event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-review-certificates">{t('jd.field.certificates')}</Label><textarea id="jd-review-certificates" className="min-h-20 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={(draft.certificates ?? []).join('\n')} onChange={(event) => setList('certificates', event.target.value)} /></div>
      </div>
      <div className="space-y-2"><Label htmlFor="jd-review-notes">{t('jd.field.notes')}</Label><textarea id="jd-review-notes" className="min-h-20 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={draft.notes ?? ''} maxLength={1000} onChange={(event) => setScalar('notes', event.target.value)} /></div>

      <div className="flex flex-wrap justify-end gap-2">
        <Button type="submit" disabled={saving || saved}><span key={draftKey}>{saving && <Loader2 className="size-4 animate-spin" />}{t('jd.saveDraft')}</span></Button>
      </div>
    </form>
  )
}
