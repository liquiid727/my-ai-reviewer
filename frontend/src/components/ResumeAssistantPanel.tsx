import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import {
  Bot,
  Check,
  CircleAlert,
  Loader2,
  RotateCcw,
  Send,
  Sparkles,
  X,
} from 'lucide-react'

import {
  applyAssistantProposal,
  AssistantApiError,
  createAssistantTurn,
  getAssistantConversation,
  rejectAssistantProposal,
  undoAssistantProposal,
} from '@/api/builder'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import type {
  AssistantConversation,
  AssistantEditOperation,
  AssistantProposal,
  ResumeDraftData,
} from '@/types/builder'

interface ResumeAssistantPanelProps {
  draftId: string
  revision: number
  llmReady: boolean
  modelLabel: string | null
  ensureLlmReady: () => boolean
  flushDraft: () => Promise<number>
  onDraftChanged: (draft: ResumeDraftData) => void
  onConflict: () => Promise<void>
}

type BusyAction = { proposalId: string; kind: 'apply' | 'reject' | 'undo' } | null

export function ResumeAssistantPanel({
  draftId,
  revision,
  llmReady,
  modelLabel,
  ensureLlmReady,
  flushDraft,
  onDraftChanged,
  onConflict,
}: ResumeAssistantPanelProps) {
  const { t } = useTranslation()
  const [conversation, setConversation] = useState<AssistantConversation | null>(null)
  const [selected, setSelected] = useState<Record<string, Set<string>>>({})
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(true)
  const [sending, setSending] = useState(false)
  const [busyAction, setBusyAction] = useState<BusyAction>(null)
  const [error, setError] = useState<string | null>(null)
  const messageListRef = useRef<HTMLDivElement | null>(null)

  const initializeSelection = useCallback((next: AssistantConversation | null) => {
    if (!next) return
    setSelected((current) => {
      const merged = { ...current }
      next.proposals.forEach((proposal) => {
        if (!merged[proposal.proposal_id] && proposal.status === 'proposed') {
          merged[proposal.proposal_id] = new Set(
            proposal.operations.map((operation) => operation.operation_id),
          )
        }
      })
      return merged
    })
  }, [])

  const loadConversation = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await getAssistantConversation(draftId)
      if (response.code !== 0) throw new Error(response.message)
      setConversation(response.data)
      initializeSelection(response.data)
    } catch {
      setError(t('builder.assistant.loadFailed'))
    } finally {
      setLoading(false)
    }
  }, [draftId, initializeSelection, t])

  useEffect(() => {
    void loadConversation()
  }, [loadConversation])

  useEffect(() => {
    const list = messageListRef.current
    if (list) list.scrollTop = list.scrollHeight
  }, [conversation, sending])

  const currentModel = useMemo(() => {
    const proposalModel = conversation?.proposals.at(-1)?.model
    return proposalModel ?? modelLabel
  }, [conversation, modelLabel])

  const sendMessage = useCallback(async () => {
    const instruction = message.trim()
    if (!instruction || sending || !ensureLlmReady()) return
    setSending(true)
    setError(null)
    try {
      const baseRevision = await flushDraft()
      const response = await createAssistantTurn(draftId, {
        message: instruction,
        base_revision: baseRevision,
        client_request_id: createRequestId(),
        conversation_id: conversation?.conversation_id,
      })
      if (response.code !== 0) throw new Error(response.message)
      setConversation(response.data)
      initializeSelection(response.data)
      setMessage('')
    } catch (cause) {
      if (isConflict(cause)) {
        setError(t('builder.assistant.conflict'))
        await onConflict()
      } else {
        setError(t('builder.assistant.sendFailed'))
      }
    } finally {
      setSending(false)
    }
  }, [
    conversation?.conversation_id,
    draftId,
    ensureLlmReady,
    flushDraft,
    initializeSelection,
    message,
    onConflict,
    sending,
    t,
  ])

  const applyProposal = useCallback(async (proposal: AssistantProposal) => {
    const chosen = [...(selected[proposal.proposal_id] ?? new Set<string>())]
    if (chosen.length === 0) return
    setBusyAction({ proposalId: proposal.proposal_id, kind: 'apply' })
    setError(null)
    try {
      const latestRevision = await flushDraft()
      if (latestRevision !== proposal.base_revision) {
        setError(t('builder.assistant.stale'))
        return
      }
      const response = await applyAssistantProposal(
        draftId,
        proposal.proposal_id,
        proposal.base_revision,
        chosen,
      )
      if (response.code !== 0) throw new Error(response.message)
      onDraftChanged(response.data)
      await loadConversation()
    } catch (cause) {
      if (isConflict(cause)) {
        setError(t('builder.assistant.conflict'))
        await onConflict()
      } else {
        setError(t('builder.assistant.sendFailed'))
      }
    } finally {
      setBusyAction(null)
    }
  }, [draftId, flushDraft, loadConversation, onConflict, onDraftChanged, selected, t])

  const rejectProposal = useCallback(async (proposal: AssistantProposal) => {
    setBusyAction({ proposalId: proposal.proposal_id, kind: 'reject' })
    try {
      await rejectAssistantProposal(draftId, proposal.proposal_id)
      await loadConversation()
    } catch {
      setError(t('builder.assistant.sendFailed'))
    } finally {
      setBusyAction(null)
    }
  }, [draftId, loadConversation, t])

  const undoProposal = useCallback(async (proposal: AssistantProposal) => {
    setBusyAction({ proposalId: proposal.proposal_id, kind: 'undo' })
    try {
      await flushDraft()
      const response = await undoAssistantProposal(draftId, proposal.proposal_id)
      if (response.code !== 0) throw new Error(response.message)
      onDraftChanged(response.data)
      await loadConversation()
    } catch (cause) {
      if (isConflict(cause)) {
        setError(t('builder.assistant.conflict'))
        await onConflict()
      } else {
        setError(t('builder.assistant.sendFailed'))
      }
    } finally {
      setBusyAction(null)
    }
  }, [draftId, flushDraft, loadConversation, onConflict, onDraftChanged, t])

  const toggleOperation = (proposalId: string, operationId: string) => {
    setSelected((current) => {
      const next = new Set(current[proposalId] ?? [])
      if (next.has(operationId)) next.delete(operationId)
      else next.add(operationId)
      return { ...current, [proposalId]: next }
    })
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={messageListRef} className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {loading ? (
          <div className="flex h-32 items-center justify-center">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : !conversation ? (
          <div className="flex min-h-48 flex-col items-center justify-center gap-3 text-center">
            <div className="flex h-11 w-11 items-center justify-center rounded-base border-2 border-border bg-main shadow-shadow">
              <Sparkles className="h-5 w-5" />
            </div>
            <p className="max-w-64 text-sm text-gray-600">{t('builder.assistant.empty')}</p>
          </div>
        ) : (
          <>
            {conversation.messages.map((item) => (
              <div
                key={item.message_id}
                className={item.role === 'user' ? 'ml-8 flex justify-end' : 'mr-6 flex gap-2'}
              >
                {item.role === 'assistant' && <Bot className="mt-1 h-4 w-4 shrink-0" />}
                <p
                  className={`whitespace-pre-wrap break-words text-sm ${
                    item.role === 'user'
                      ? 'rounded-base border-2 border-border bg-main px-3 py-2 shadow-shadow'
                      : 'py-1 text-gray-700'
                  }`}
                >
                  {item.content}
                </p>
              </div>
            ))}
            {conversation.proposals.map((proposal) => (
              <ProposalReview
                key={proposal.proposal_id}
                proposal={proposal}
                revision={revision}
                selected={selected[proposal.proposal_id] ?? new Set()}
                busyAction={busyAction}
                onToggle={toggleOperation}
                onApply={() => void applyProposal(proposal)}
                onReject={() => void rejectProposal(proposal)}
                onUndo={() => void undoProposal(proposal)}
              />
            ))}
          </>
        )}
        {sending && (
          <div className="flex items-center gap-2 py-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            {t('builder.assistant.generating')}
          </div>
        )}
        {error && (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
      </div>

      <div className="shrink-0 border-t-2 border-border bg-background p-3">
        {currentModel && (
          <p className="mb-2 truncate text-xs text-gray-500">
            {t('builder.assistant.model', { model: currentModel })}
          </p>
        )}
        <div className="flex items-end gap-2">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault()
                void sendMessage()
              }
            }}
            placeholder={t('builder.assistant.placeholder')}
            disabled={sending}
            rows={3}
            className="max-h-36 min-h-20 min-w-0 flex-1 resize-y rounded-base border-2 border-border bg-white p-2 text-sm shadow-shadow focus:outline-none"
          />
          <Button
            size="icon"
            onClick={() => void sendMessage()}
            disabled={!message.trim() || sending || !llmReady}
            title={t('builder.assistant.send')}
          >
            {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </Button>
        </div>
      </div>
    </div>
  )
}

interface ProposalReviewProps {
  proposal: AssistantProposal
  revision: number
  selected: Set<string>
  busyAction: BusyAction
  onToggle: (proposalId: string, operationId: string) => void
  onApply: () => void
  onReject: () => void
  onUndo: () => void
}

function ProposalReview({
  proposal,
  revision,
  selected,
  busyAction,
  onToggle,
  onApply,
  onReject,
  onUndo,
}: ProposalReviewProps) {
  const { t } = useTranslation()
  const busy = busyAction?.proposalId === proposal.proposal_id
  const stale = proposal.status === 'proposed' && proposal.base_revision !== revision

  return (
    <div className="rounded-base border-2 border-border bg-white shadow-shadow">
      <div className="flex items-center justify-between gap-2 border-b-2 border-border px-3 py-2">
        <p className="text-sm font-heading">
          {t('builder.assistant.changesTitle', { count: proposal.operations.length })}
        </p>
        {proposal.status !== 'proposed' && (
          <Badge variant="neutral">{t(`builder.assistant.${proposal.status}`)}</Badge>
        )}
      </div>

      {proposal.operations.length === 0 ? (
        <p className="p-3 text-sm text-gray-500">{t('builder.assistant.noChanges')}</p>
      ) : (
        <div className="divide-y-2 divide-border">
          {proposal.operations.map((operation) => (
            <OperationRow
              key={operation.operation_id}
              operation={operation}
              checked={selected.has(operation.operation_id)}
              disabled={proposal.status !== 'proposed' || stale || busy}
              onToggle={() => onToggle(proposal.proposal_id, operation.operation_id)}
            />
          ))}
        </div>
      )}

      {stale && <p className="border-t-2 border-border p-3 text-xs text-red-700">{t('builder.assistant.stale')}</p>}

      <div className="flex flex-wrap gap-2 border-t-2 border-border p-3">
        {proposal.status === 'proposed' && proposal.operations.length > 0 && (
          <>
            <Button size="sm" onClick={onApply} disabled={busy || stale || selected.size === 0}>
              {busyAction?.kind === 'apply' && busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Check className="h-3.5 w-3.5" />
              )}
              {t(busyAction?.kind === 'apply' && busy ? 'builder.assistant.applying' : 'builder.assistant.applySelected')}
            </Button>
            <Button variant="neutral" size="sm" onClick={onReject} disabled={busy}>
              {busyAction?.kind === 'reject' && busy ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <X className="h-3.5 w-3.5" />
              )}
              {t('builder.assistant.reject')}
            </Button>
          </>
        )}
        {proposal.status === 'applied' && proposal.applied_revision === revision && (
          <Button variant="neutral" size="sm" onClick={onUndo} disabled={busy}>
            {busyAction?.kind === 'undo' && busy ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RotateCcw className="h-3.5 w-3.5" />
            )}
            {t('builder.assistant.undo')}
          </Button>
        )}
      </div>
    </div>
  )
}

function OperationRow({
  operation,
  checked,
  disabled,
  onToggle,
}: {
  operation: AssistantEditOperation
  checked: boolean
  disabled: boolean
  onToggle: () => void
}) {
  const { t } = useTranslation()
  return (
    <label className={`block p-3 ${disabled ? 'opacity-60' : 'cursor-pointer'}`}>
      <div className="flex items-start gap-2">
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={onToggle}
          className="mt-0.5 h-4 w-4 accent-black"
        />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-heading">{t(`builder.assistant.operation.${operation.kind}`)}</p>
          {operation.reason && <p className="mt-0.5 text-xs text-gray-500">{operation.reason}</p>}
          <div className="mt-2 grid gap-2 text-xs sm:grid-cols-2">
            {operation.kind !== 'add_bullet' && (
              <div className="min-w-0 border-l-2 border-gray-300 pl-2">
                <span className="text-gray-500">{t('builder.assistant.before')}</span>
                <p className="mt-1 break-words whitespace-pre-wrap">{operation.before || '—'}</p>
              </div>
            )}
            {operation.kind !== 'remove_bullet' && (
              <div className="min-w-0 border-l-2 border-main pl-2">
                <span className="text-gray-500">{t('builder.assistant.after')}</span>
                <p className="mt-1 break-words whitespace-pre-wrap">{operation.after || '—'}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </label>
  )
}

function createRequestId(): string {
  return globalThis.crypto?.randomUUID?.() ?? `assistant-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

function isConflict(cause: unknown): boolean {
  return cause instanceof AssistantApiError && cause.status === 409
}
