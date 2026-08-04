import { useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ArrowDown, ArrowUp, Loader2, RotateCcw, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { PlanTask, PlanTaskCategory, PlanTaskPriority, PlanTaskStatus } from '@/types/plans'

interface PlanTaskEditorProps {
  task: PlanTask
  disabled: boolean
  reconciliationVersion: number
  canMoveUp: boolean
  canMoveDown: boolean
  onPatch: (input: {
    title?: string
    category?: PlanTaskCategory
    description?: string
    priority?: PlanTaskPriority
    status?: PlanTaskStatus
    due_date?: string | null
  }) => Promise<boolean>
  onDelete: () => Promise<boolean>
  onMove: (direction: -1 | 1) => Promise<boolean>
}

interface TaskDraft {
  title: string
  category: PlanTaskCategory
  description: string
  priority: PlanTaskPriority
  dueDate: string
  status: PlanTaskStatus
}

function draftFromTask(task: PlanTask): TaskDraft {
  return {
    title: task.title,
    category: task.category,
    description: task.description,
    priority: task.priority,
    dueDate: task.due_date || '',
    status: task.status,
  }
}

function mutationFromDraft(draft: TaskDraft) {
  return {
    title: draft.title.trim(),
    category: draft.category,
    description: draft.description,
    priority: draft.priority,
    due_date: draft.dueDate || null,
  }
}

export function PlanTaskEditor({
  task,
  disabled,
  reconciliationVersion,
  canMoveUp,
  canMoveDown,
  onPatch,
  onDelete,
  onMove,
}: PlanTaskEditorProps) {
  const { t } = useTranslation()
  const [draft, setDraft] = useState(() => draftFromTask(task))
  const [saveError, setSaveError] = useState(false)
  const [saving, setSaving] = useState(false)
  const savedDraft = useRef(JSON.stringify(mutationFromDraft(draftFromTask(task))))
  const latestTask = useRef(task)
  latestTask.current = task

  useEffect(() => {
    const next = draftFromTask(latestTask.current)
    setDraft(next)
    savedDraft.current = JSON.stringify(mutationFromDraft(next))
    setSaveError(false)
  }, [reconciliationVersion, task.id])

  const mutation = useMemo(() => mutationFromDraft(draft), [draft])

  useEffect(() => {
    if (disabled || JSON.stringify(mutation) === savedDraft.current || !mutation.title) return undefined
    const timer = window.setTimeout(async () => {
      setSaving(true)
      const saved = await onPatch(mutation)
      if (saved) {
        savedDraft.current = JSON.stringify(mutation)
        setSaveError(false)
      } else {
        setSaveError(true)
      }
      setSaving(false)
    }, 500)
    return () => window.clearTimeout(timer)
  }, [disabled, mutation, onPatch])

  const update = <K extends keyof TaskDraft>(key: K, value: TaskDraft[K]) => {
    setDraft((current) => ({ ...current, [key]: value }))
  }

  const updateStatus = async (status: PlanTaskStatus) => {
    if (disabled || saving) return
    update('status', status)
    setSaving(true)
    const saved = await onPatch({ status })
    if (saved) {
      setSaveError(false)
    } else {
      setSaveError(true)
    }
    setSaving(false)
  }

  const retry = async () => {
    if (disabled || saving || !mutation.title) return
    setSaving(true)
    const saved = await onPatch({ ...mutation, status: draft.status })
    if (saved) {
      savedDraft.current = JSON.stringify(mutation)
      setSaveError(false)
    }
    setSaving(false)
  }

  return (
    <div className="border-2 border-black bg-white p-3 shadow-shadow">
      <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_9rem_8rem_8rem] lg:items-start">
        <div className="min-w-0 space-y-2">
          <Input
            aria-label={t('plans.taskTitle')}
            value={draft.title}
            maxLength={300}
            disabled={disabled}
            onChange={(event) => update('title', event.target.value)}
          />
          <textarea
            aria-label={t('plans.taskDescription')}
            className="min-h-20 w-full rounded-base border-2 border-black bg-secondary-background p-2 text-sm disabled:cursor-not-allowed disabled:opacity-50"
            value={draft.description}
            maxLength={3000}
            disabled={disabled}
            onChange={(event) => update('description', event.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Select value={draft.category} disabled={disabled} onValueChange={(value) => update('category', value as PlanTaskCategory)}>
            <SelectTrigger aria-label={t('plans.taskCategory')}><SelectValue /></SelectTrigger>
            <SelectContent>{(['gap_priority', 'resume', 'skill', 'evidence_project', 'interview', 'application_review'] as PlanTaskCategory[]).map((value) => <SelectItem key={value} value={value}>{t(`plans.category.${value}`)}</SelectItem>)}</SelectContent>
          </Select>
          <Select value={draft.priority} disabled={disabled} onValueChange={(value) => update('priority', value as PlanTaskPriority)}>
            <SelectTrigger aria-label={t('plans.taskPriority')}><SelectValue /></SelectTrigger>
            <SelectContent>{(['high', 'medium', 'low'] as PlanTaskPriority[]).map((value) => <SelectItem key={value} value={value}>{t(`plans.priority.${value}`)}</SelectItem>)}</SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Select value={draft.status} disabled={disabled} onValueChange={(value) => void updateStatus(value as PlanTaskStatus)}>
            <SelectTrigger aria-label={t('plans.taskStatus')}><SelectValue /></SelectTrigger>
            <SelectContent>{(['todo', 'in_progress', 'done'] as PlanTaskStatus[]).map((value) => <SelectItem key={value} value={value}>{t(`plans.taskStatusValue.${value}`)}</SelectItem>)}</SelectContent>
          </Select>
          <Input aria-label={t('plans.dueDate')} type="date" value={draft.dueDate} disabled={disabled} onChange={(event) => update('dueDate', event.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2 lg:justify-end">
          <Button size="icon" variant="neutral" title={t('plans.moveUp')} disabled={disabled || !canMoveUp} onClick={() => void onMove(-1)}><ArrowUp className="size-4" /></Button>
          <Button size="icon" variant="neutral" title={t('plans.moveDown')} disabled={disabled || !canMoveDown} onClick={() => void onMove(1)}><ArrowDown className="size-4" /></Button>
          <Button size="icon" variant="neutral" title={t('plans.deleteTask')} disabled={disabled || task.status === 'done'} onClick={() => void onDelete()}><Trash2 className="size-4" /></Button>
          {saving && <Loader2 className="size-4 animate-spin self-center" aria-label={t('plans.saving')} />}
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-xs text-muted-foreground">
        <span>{task.source === 'manual' ? t('plans.manual') : t('plans.aiGenerated')}</span>
        {task.basis.length > 0 && <span className="truncate">{t('plans.basisCount', { count: task.basis.length })}</span>}
        {saveError && <Button size="sm" variant="neutral" onClick={() => void retry()} disabled={disabled || saving}><RotateCcw className="size-3" />{t('plans.retrySave')}</Button>}
      </div>
    </div>
  )
}
