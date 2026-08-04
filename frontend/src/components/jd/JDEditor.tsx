import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { JDDetail, JDPatchInput, JDSeniority, JDSkill } from '@/types/jd'

function skillsToText(skills: JDSkill[]) {
  return skills.map((skill) => `${skill.name}${skill.critical ? ' | critical' : ''}`).join('\n')
}

function textToSkills(value: string): JDSkill[] {
  return value.split('\n').map((line) => line.trim()).filter(Boolean).map((line) => {
    const [name, flag] = line.split('|').map((part) => part.trim())
    return { name, critical: flag?.toLowerCase() === 'critical' }
  })
}

interface JDEditorProps {
  jd: JDDetail
  onSave: (input: JDPatchInput) => Promise<boolean>
  onCancel: () => void
}

export function JDEditor({ jd, onSave, onCancel }: JDEditorProps) {
  const { t } = useTranslation()
  const [title, setTitle] = useState(jd.title || '')
  const [company, setCompany] = useState(jd.company || '')
  const [location, setLocation] = useState(jd.location || '')
  const [seniority, setSeniority] = useState<JDSeniority>(jd.seniority || 'mid')
  const [responsibilities, setResponsibilities] = useState(jd.responsibilities.join('\n'))
  const [requiredSkills, setRequiredSkills] = useState(skillsToText(jd.required_skills))
  const [preferredSkills, setPreferredSkills] = useState(skillsToText(jd.preferred_skills))
  const [saving, setSaving] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (saving) return
    setSaving(true)
    try {
      const saved = await onSave({
        expected_updated_at: jd.updated_at || '',
        title: title.trim() || null,
        company: company.trim() || null,
        location: location.trim() || null,
        seniority,
        responsibilities: responsibilities.split('\n').map((line) => line.trim()).filter(Boolean),
        required_skills: textToSkills(requiredSkills),
        preferred_skills: textToSkills(preferredSkills),
      })
      if (saved) onCancel()
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="space-y-4" onSubmit={submit}>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="jd-edit-title">{t('jd.field.title')}</Label><Input id="jd-edit-title" value={title} maxLength={200} onChange={(event) => setTitle(event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-edit-company">{t('jd.field.company')}</Label><Input id="jd-edit-company" value={company} maxLength={200} onChange={(event) => setCompany(event.target.value)} /></div>
        <div className="space-y-2"><Label htmlFor="jd-edit-location">{t('jd.field.location')}</Label><Input id="jd-edit-location" value={location} maxLength={200} onChange={(event) => setLocation(event.target.value)} /></div>
        <div className="space-y-2"><Label>{t('jd.field.seniority')}</Label><Select value={seniority} onValueChange={(value) => setSeniority(value as JDSeniority)}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent>{(['junior', 'mid', 'senior', 'expert'] as JDSeniority[]).map((value) => <SelectItem key={value} value={value}>{t(`jd.seniority.${value}`)}</SelectItem>)}</SelectContent></Select></div>
      </div>
      <div className="space-y-2"><Label htmlFor="jd-edit-responsibilities">{t('jd.field.responsibilities')}</Label><textarea id="jd-edit-responsibilities" className="min-h-28 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={responsibilities} onChange={(event) => setResponsibilities(event.target.value)} /><p className="text-xs text-muted-foreground">{t('jd.onePerLine')}</p></div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-2"><Label htmlFor="jd-edit-required">{t('jd.field.requiredSkills')}</Label><textarea id="jd-edit-required" className="min-h-28 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={requiredSkills} onChange={(event) => setRequiredSkills(event.target.value)} /><p className="text-xs text-muted-foreground">{t('jd.skillHelp')}</p></div>
        <div className="space-y-2"><Label htmlFor="jd-edit-preferred">{t('jd.field.preferredSkills')}</Label><textarea id="jd-edit-preferred" className="min-h-28 w-full rounded-base border-2 border-black bg-secondary-background p-3 text-sm" value={preferredSkills} onChange={(event) => setPreferredSkills(event.target.value)} /><p className="text-xs text-muted-foreground">{t('jd.skillHelp')}</p></div>
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="neutral" onClick={onCancel} disabled={saving}>{t('common.cancel')}</Button>
        <Button type="submit" disabled={saving}>{saving && <Loader2 className="size-4 animate-spin" />}{t('common.save')}</Button>
      </div>
    </form>
  )
}
